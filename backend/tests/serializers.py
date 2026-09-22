from rest_framework import serializers
from .models import TestType, TestRequest, TestAssignment, SampleCustodyLog, TestCertificate
from accounts.serializers import UserProfileSerializer


class TestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestType
        fields = ['id', 'name', 'description', 'details', 'price',
                  'duration', 'sample_requirements', 'is_active', 'created_at']


class SampleCustodyLogSerializer(serializers.ModelSerializer):
    transferred_from = UserProfileSerializer(read_only=True)
    transferred_to = UserProfileSerializer(read_only=True)
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)

    class Meta:
        model = SampleCustodyLog
        fields = ['id', 'test_request', 'stage', 'stage_display', 'transferred_from',
                  'transferred_to', 'location', 'custody_notes', 'timestamp']


class TestCertificateSerializer(serializers.ModelSerializer):
    issued_by = UserProfileSerializer(read_only=True)

    class Meta:
        model = TestCertificate
        fields = ['id', 'test_request', 'certificate_number', 'verification_code',
                  'issued_by', 'issued_at', 'digital_signature_hash', 'is_valid']


class TestRequestSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    test_type = TestTypeSerializer(read_only=True)
    officer = UserProfileSerializer(read_only=True)
    lab_technician = UserProfileSerializer(read_only=True)
    field_inspector = UserProfileSerializer(read_only=True)
    category_display = serializers.CharField(source='get_sample_category_display', read_only=True)
    certificate = TestCertificateSerializer(read_only=True)
    custody_logs = SampleCustodyLogSerializer(many=True, read_only=True)

    class Meta:
        model = TestRequest
        fields = [
            'id', 'user', 'test_type', 'officer', 'lab_technician', 'field_inspector',
            'status', 'sample_tag_id', 'sample_category', 'category_display',
            'sampling_location', 'collection_date', 'sample_description', 'notes',
            'result', 'lab_measurements', 'certificate', 'custody_logs',
            'status_updated_at', 'created_at'
        ]


class TestRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRequest
        fields = ['test_type', 'sample_category', 'sampling_location',
                  'collection_date', 'sample_description', 'notes']

    def validate(self, attrs):
        if not attrs.get('test_type'):
            raise serializers.ValidationError("Test type is required")
        return attrs


class TestStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRequest
        fields = ['status', 'notes', 'result', 'lab_measurements', 'lab_technician', 'field_inspector']


class TestAssignmentSerializer(serializers.ModelSerializer):
    test_type = TestTypeSerializer(read_only=True)
    officer = UserProfileSerializer(read_only=True)

    class Meta:
        model = TestAssignment
        fields = ['id', 'test_type', 'officer', 'is_active', 'assigned_at']


class TestAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAssignment
        fields = ['test_type', 'officer']
