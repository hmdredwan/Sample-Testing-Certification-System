from rest_framework import serializers
from .models import Message
from accounts.serializers import UserProfileSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)
    receiver = UserProfileSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'test_request', 'sender', 'receiver', 'subject',
                  'content', 'is_read', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['test_request', 'receiver', 'subject', 'content']
