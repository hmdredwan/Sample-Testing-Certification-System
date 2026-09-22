import uuid
import hashlib
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TestType, TestRequest, TestAssignment, SampleCustodyLog, TestCertificate
from accounts.models import User
from .serializers import (
    TestTypeSerializer, TestRequestSerializer, TestRequestCreateSerializer,
    TestStatusUpdateSerializer, TestAssignmentSerializer, TestAssignmentCreateSerializer,
    SampleCustodyLogSerializer, TestCertificateSerializer
)
from utils.helpers import log_activity
from utils.pdf_generator import generate_test_certificate_pdf
from utils.barcode_generator import generate_sample_tag_id, generate_qr_base64


# ============ Public Test Types ============
class PublicTestTypesView(generics.ListAPIView):
    queryset = TestType.objects.filter(is_active=True)
    serializer_class = TestTypeSerializer
    permission_classes = [permissions.AllowAny]


# ============ User Test Requests ============
class UserTestRequestListView(generics.ListAPIView):
    serializer_class = TestRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestRequest.objects.filter(user=self.request.user)


class CreateTestRequestView(generics.CreateAPIView):
    serializer_class = TestRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        test_type_id = request.data.get('test_type')
        test_type = get_object_or_404(TestType, id=test_type_id, is_active=True)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            existing = TestRequest.objects.filter(
                user=request.user, test_type=test_type, status='pending'
            ).exists()
            if existing:
                return Response({'error': 'You already have a pending request for this test.'},
                               status=status.HTTP_400_BAD_REQUEST)

            test_request = serializer.save(
                user=request.user,
                test_type=test_type
            )
            # Generate sample tag ID
            test_request.sample_tag_id = generate_sample_tag_id(test_request.id)
            test_request.save()

            # Create initial custody log entry
            SampleCustodyLog.objects.create(
                test_request=test_request,
                stage='received_reception',
                transferred_from=request.user,
                location='RRI Central Reception Counter',
                custody_notes='Sample testing request registered online.'
            )

            log_activity(request, 'Test Request Created',
                        f'User {request.user.username} requested test: {test_type.name} (Tag: {test_request.sample_tag_id})')

            return Response(TestRequestSerializer(test_request).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserTestRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        # Check permissions: owner, assigned officer, lab technician, field inspector, or admin
        if request.user.role not in ['admin', 'officer', 'lab_technician', 'field_inspector'] and test_request.user != request.user:
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(TestRequestSerializer(test_request).data)


# ============ Physical Sample Label View (Barcode & QR) ============
class SampleLabelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        if not test_request.sample_tag_id:
            test_request.sample_tag_id = generate_sample_tag_id(test_request.id)
            test_request.save()

        verification_url = f"http://localhost:3000/verify-certificate/sample/{test_request.sample_tag_id}"
        qr_base64 = generate_qr_base64(verification_url)

        return Response({
            'sample_tag_id': test_request.sample_tag_id,
            'test_request_id': test_request.id,
            'test_type_name': test_request.test_type.name,
            'sample_category': test_request.get_sample_category_display(),
            'sampling_location': test_request.sampling_location or 'N/A',
            'client_name': test_request.user.get_full_name() or test_request.user.username,
            'qr_code_base64': qr_base64,
            'verification_url': verification_url
        })


# ============ Chain of Custody Views ============
class CreateCustodyLogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        stage = request.data.get('stage', 'received_reception')
        location = request.data.get('location', '')
        custody_notes = request.data.get('custody_notes', '')

        custody_log = SampleCustodyLog.objects.create(
            test_request=test_request,
            stage=stage,
            transferred_from=request.user,
            location=location,
            custody_notes=custody_notes
        )
        
        # If stage is in_testing, update request status
        if stage == 'in_testing' and test_request.status in ['pending', 'approved']:
            test_request.status = 'testing'
            test_request.save()

        log_activity(request, 'Custody Log Created',
                    f'Sample {test_request.sample_tag_id} transferred: {stage}')
        return Response(SampleCustodyLogSerializer(custody_log).data, status=status.HTTP_201_CREATED)


class SampleCustodyHistoryView(generics.ListAPIView):
    serializer_class = SampleCustodyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return SampleCustodyLog.objects.filter(test_request_id=pk)


# ============ Digital Certificate & Verification Views ============
class GenerateCertificateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Admin or Officer can issue digital certificates
        if request.user.role not in ['admin', 'officer']:
            return Response({'error': 'Only officers or admins can issue digital certificates.'},
                           status=status.HTTP_403_FORBIDDEN)

        test_request = get_object_or_404(TestRequest, pk=pk)
        if test_request.status != 'completed':
            return Response({'error': 'Certificates can only be issued for completed tests.'},
                           status=status.HTTP_400_BAD_REQUEST)

        certificate, created = TestCertificate.objects.get_or_create(
            test_request=test_request,
            defaults={
                'certificate_number': f"RRI-CERT-2026-{str(uuid.uuid4())[:8].upper()}",
                'verification_code': str(uuid.uuid4()),
                'issued_by': request.user,
                'digital_signature_hash': hashlib.sha256(f"{test_request.id}-{request.user.id}".encode()).hexdigest()
            }
        )

        log_activity(request, 'Digital Certificate Issued',
                    f'Issued certificate {certificate.certificate_number} for test request {test_request.id}')
        return Response(TestCertificateSerializer(certificate).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DownloadCertificatePDFView(APIView):
    permission_classes = [permissions.AllowAny] # Publicly accessible with valid cert ID or code

    def get(self, request, code):
        try:
            # Try fetching by verification code or certificate_number or test_request_id
            certificate = TestCertificate.objects.select_related('test_request', 'test_request__user', 'test_request__test_type', 'test_request__officer', 'test_request__lab_technician').get(
                verification_code=code
            )
        except TestCertificate.DoesNotExist:
            try:
                certificate = TestCertificate.objects.select_related('test_request', 'test_request__user', 'test_request__test_type', 'test_request__officer', 'test_request__lab_technician').get(
                    certificate_number=code
                )
            except TestCertificate.DoesNotExist:
                return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        pdf_bytes = generate_test_certificate_pdf(certificate)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{certificate.certificate_number}.pdf"'
        return response


class PublicVerifyCertificateView(APIView):
    permission_classes = [permissions.AllowAny] # Public endpoint for QR code verification

    def get(self, request, code):
        try:
            certificate = TestCertificate.objects.select_related('test_request', 'test_request__user', 'test_request__test_type', 'test_request__officer', 'issued_by').get(
                verification_code=code
            )
        except TestCertificate.DoesNotExist:
            try:
                certificate = TestCertificate.objects.select_related('test_request', 'test_request__user', 'test_request__test_type', 'test_request__officer', 'issued_by').get(
                    certificate_number=code
                )
            except TestCertificate.DoesNotExist:
                return Response({
                    'is_valid': False,
                    'message': 'Invalid verification code. Certificate not found in RRI database.'
                }, status=status.HTTP_404_NOT_FOUND)

        serializer = TestCertificateSerializer(certificate)
        test_request = certificate.test_request

        return Response({
            'is_valid': certificate.is_valid,
            'certificate': serializer.data,
            'test_request': {
                'sample_tag_id': test_request.sample_tag_id,
                'test_type_name': test_request.test_type.name,
                'sample_category': test_request.get_sample_category_display(),
                'sampling_location': test_request.sampling_location,
                'collection_date': test_request.collection_date,
                'client_name': test_request.user.get_full_name() or test_request.user.username,
                'result_summary': test_request.result,
                'lab_measurements': test_request.lab_measurements,
                'issued_at': certificate.issued_at
            }
        })


# ============ Lab Technician Views ============
class LabTechnicianTestRequestsView(generics.ListAPIView):
    serializer_class = TestRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return tests assigned to technician or all in testing/approved stage
        user = self.request.user
        if user.role == 'lab_technician':
            return TestRequest.objects.filter(
                status__in=['approved', 'in_progress', 'testing', 'completed']
            ).select_related('user', 'test_type', 'officer', 'lab_technician')
        return TestRequest.objects.none()


class LabTechnicianUpdateResultsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        result_text = request.data.get('result', test_request.result)
        lab_measurements = request.data.get('lab_measurements', test_request.lab_measurements)
        new_status = request.data.get('status', test_request.status)

        test_request.result = result_text
        test_request.lab_measurements = lab_measurements
        test_request.status = new_status
        test_request.lab_technician = request.user
        test_request.save()

        # Log custody transfer if completed
        if new_status == 'completed':
            SampleCustodyLog.objects.create(
                test_request=test_request,
                stage='completed',
                transferred_from=request.user,
                location='RRI Specialized Laboratory Archive',
                custody_notes='Laboratory testing completed. Measurements recorded.'
            )

        log_activity(request, 'Lab Results Recorded',
                    f'Lab Technician {request.user.username} updated test {test_request.sample_tag_id or pk}')

        return Response(TestRequestSerializer(test_request).data)


# ============ Field Inspector Views ============
class FieldInspectorSampleCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        test_type_id = request.data.get('test_type')
        test_type = get_object_or_404(TestType, id=test_type_id)

        sample_category = request.data.get('sample_category', 'riverbed_soil')
        sampling_location = request.data.get('sampling_location', '')
        collection_date = request.data.get('collection_date')
        sample_description = request.data.get('sample_description', '')
        notes = request.data.get('notes', '')

        test_request = TestRequest.objects.create(
            user=request.user,
            test_type=test_type,
            field_inspector=request.user,
            sample_category=sample_category,
            sampling_location=sampling_location,
            collection_date=collection_date if collection_date else None,
            sample_description=sample_description,
            notes=notes,
            status='pending'
        )
        test_request.sample_tag_id = generate_sample_tag_id(test_request.id)
        test_request.save()

        # Initial custody log entry
        SampleCustodyLog.objects.create(
            test_request=test_request,
            stage='collected_field',
            transferred_from=request.user,
            location=sampling_location or 'Field Site',
            custody_notes=f'Field sample collected by Inspector {request.user.username}. Tag: {test_request.sample_tag_id}'
        )

        log_activity(request, 'Field Sample Registered',
                    f'Field Inspector {request.user.username} collected sample {test_request.sample_tag_id}')

        return Response(TestRequestSerializer(test_request).data, status=status.HTTP_201_CREATED)


class FieldInspectorSamplesView(generics.ListAPIView):
    serializer_class = TestRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestRequest.objects.filter(field_inspector=self.request.user)


# ============ Admin Test Type Management ============
class AdminTestTypeListView(generics.ListCreateAPIView):
    queryset = TestType.objects.all().order_by('-created_at')
    serializer_class = TestTypeSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        test_type = serializer.save()
        log_activity(self.request, 'Test Type Created',
                    f'Created test type: {test_type.name}')


class AdminTestTypeDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        test_type = get_object_or_404(TestType, pk=pk)
        return Response(TestTypeSerializer(test_type).data)

    def put(self, request, pk):
        test_type = get_object_or_404(TestType, pk=pk)
        serializer = TestTypeSerializer(test_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_activity(request, 'Test Type Updated', f'Updated test type: {test_type.name}')
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        test_type = get_object_or_404(TestType, pk=pk)
        name = test_type.name
        test_type.delete()
        log_activity(request, 'Test Type Deleted', f'Deleted test type: {name}')
        return Response({'message': f'Test type {name} deleted.'})


# ============ Admin Officer-Test Assignment ============
class AdminAssignmentListView(generics.ListAPIView):
    queryset = TestAssignment.objects.select_related('test_type', 'officer')
    serializer_class = TestAssignmentSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCreateAssignmentView(generics.CreateAPIView):
    serializer_class = TestAssignmentCreateSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            assignment, created = TestAssignment.objects.get_or_create(
                test_type=serializer.validated_data['test_type'],
                officer=serializer.validated_data['officer'],
                defaults={'is_active': True}
            )
            if not created and not assignment.is_active:
                assignment.is_active = True
                assignment.save()
            log_activity(request, 'Officer Assigned', 'Assigned officer to test type')
            return Response(TestAssignmentSerializer(assignment).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRemoveAssignmentView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, pk):
        try:
            assignment = TestAssignment.objects.get(pk=pk)
            assignment.delete()
            log_activity(request, 'Assignment Removed', 'Removed officer-test assignment')
            return Response({'message': 'Assignment removed.'})
        except TestAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)


# ============ Admin All Test Requests ============
class AdminTestRequestListView(generics.ListAPIView):
    queryset = TestRequest.objects.select_related('user', 'test_type', 'officer', 'lab_technician', 'field_inspector').all()
    serializer_class = TestRequestSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminAssignTestRequestView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        officer_id = request.data.get('officer')
        if not officer_id:
            test_request.officer = None
            test_request.save(update_fields=['officer', 'status_updated_at'])
        else:
            officer = get_object_or_404(User, pk=officer_id, role='officer', is_active=True)
            test_request.officer = officer
            test_request.save(update_fields=['officer', 'status_updated_at'])

        log_activity(
            request,
            'Test Request Assigned',
            f'Updated officer assignment for {test_request.sample_tag_id or test_request.id}',
        )
        return Response(TestRequestSerializer(test_request).data)


class AdminReviewTestRequestView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        test_request = get_object_or_404(TestRequest, pk=pk)
        review_status = request.data.get('status')
        if review_status not in ['approved', 'rejected']:
            return Response(
                {'error': 'Status must be approved or rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        test_request.status = review_status
        if 'notes' in request.data:
            test_request.notes = request.data.get('notes')
        test_request.save()
        log_activity(
            request,
            f'Test Request {review_status.title()}',
            f'Admin reviewed test request {test_request.sample_tag_id or test_request.id}',
        )
        return Response(TestRequestSerializer(test_request).data)


# ============ Officer Views ============
class OfficerAssignedTestsView(generics.ListAPIView):
    serializer_class = TestAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestAssignment.objects.filter(
            officer=self.request.user, is_active=True
        ).select_related('test_type')


class OfficerTestRequestsView(generics.ListAPIView):
    serializer_class = TestRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestRequest.objects.filter(
            officer=self.request.user
        ).select_related('user', 'test_type')


class OfficerUpdateTestStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            test_request = TestRequest.objects.get(pk=pk)
        except TestRequest.DoesNotExist:
            return Response({'error': 'Test request not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TestStatusUpdateSerializer(test_request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            old_status = test_request.status
            log_activity(request, 'Test Status Updated',
                        f'Updated test {pk} from {old_status} to {serializer.data.get("status")}')
            return Response(TestRequestSerializer(test_request).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
