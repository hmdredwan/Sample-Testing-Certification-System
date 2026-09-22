from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer, PaymentUpdateSerializer
from tests.models import TestRequest
from utils.helpers import log_activity
import random
import string


def generate_receipt_number():
    prefix = 'RRI'
    random_str = ''.join(random.choices(string.digits, k=6))
    return f'{prefix}-{random_str}'


# ============ User Payment Views ============
class UserPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related('test_request')


class CreatePaymentView(generics.CreateAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            test_request = serializer.validated_data['test_request']

            # Ensure the test request belongs to the user
            if test_request.user != request.user:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

            # Check for duplicate payment
            existing = Payment.objects.filter(
                test_request=test_request, status='paid'
            ).exists()
            if existing:
                return Response({'error': 'Payment already made for this test request.'},
                               status=status.HTTP_400_BAD_REQUEST)

            payment = serializer.save(
                user=request.user,
                receipt_number=generate_receipt_number(),
                status='paid',
                paid_at=request.data.get('paid_at'),
            )
            log_activity(request, 'Payment Made',
                        f'Payment of {payment.amount} for test request via {payment.payment_method}')

            return Response(PaymentSerializer(payment).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, user=request.user)
        return Response(PaymentSerializer(payment).data)


# ============ Admin Payment Views ============
class AdminPaymentListView(generics.ListAPIView):
    queryset = Payment.objects.select_related('user', 'test_request').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminPaymentDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        return Response(PaymentSerializer(payment).data)

    def put(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        serializer = PaymentUpdateSerializer(payment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_activity(request, 'Payment Updated', f'Updated payment {payment.receipt_number}')
            return Response(PaymentSerializer(payment).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
