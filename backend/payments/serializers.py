from rest_framework import serializers
from .models import Payment
from accounts.serializers import UserProfileSerializer
from tests.serializers import TestRequestSerializer


class PaymentSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    test_request = TestRequestSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'user', 'test_request', 'amount', 'payment_method',
                  'transaction_id', 'status', 'receipt_number', 'paid_at', 'created_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['test_request', 'amount', 'payment_method', 'transaction_id']


class PaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['status', 'transaction_id', 'receipt_number', 'paid_at']
