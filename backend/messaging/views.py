from django.db import models as django_models
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Message
from .serializers import MessageSerializer, MessageCreateSerializer
from tests.models import TestRequest
from utils.helpers import log_activity


class UserMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(
            receiver=self.request.user
        ).select_related('sender', 'receiver', 'test_request')


class UserSentMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(
            sender=self.request.user
        ).select_related('sender', 'receiver', 'test_request')


class ConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, test_request_id):
        """Get all messages for a specific test request (conversation thread)"""
        messages = Message.objects.filter(
            test_request_id=test_request_id
        ).filter(
            django_models.Q(sender=request.user) | django_models.Q(receiver=request.user)
        ).select_related('sender', 'receiver').order_by('created_at')

        # Mark unread messages as read
        Message.objects.filter(
            test_request_id=test_request_id,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)

        return Response(MessageSerializer(messages, many=True).data)


class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            test_request = serializer.validated_data['test_request']
            receiver = serializer.validated_data['receiver']

            # Ensure user is part of this test request
            is_participant = (
                test_request.user == request.user or
                test_request.officer == request.user
            )
            if not is_participant:
                return Response({'error': 'You are not part of this test request.'},
                               status=status.HTTP_403_FORBIDDEN)

            message = Message.objects.create(
                test_request=test_request,
                sender=request.user,
                receiver=receiver,
                subject=serializer.validated_data.get('subject', ''),
                content=serializer.validated_data['content'],
            )
            log_activity(request, 'Message Sent',
                        f'Sent message to {receiver.username} regarding test request')
            return Response(MessageSerializer(message).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkMessageReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            message = Message.objects.get(pk=pk, receiver=request.user)
            message.is_read = True
            message.save()
            return Response({'message': 'Marked as read'})
        except Message.DoesNotExist:
            return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)


class UnreadMessageCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            receiver=request.user, is_read=False
        ).count()
        return Response({'unread_count': count})
