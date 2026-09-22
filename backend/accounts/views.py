from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import User, ActivityLog
from .serializers import (
    UserSerializer, UserProfileSerializer, UserUpdateSerializer,
    AdminUserUpdateSerializer, OfficerApprovalSerializer, ActivityLogSerializer
)
from utils.helpers import log_activity


class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            log_activity(request, 'User Signup', f'New user registered: {user.username} (role: {user.role})')
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Registration successful!' if user.is_approved
                           else 'Registration submitted! Waiting for admin approval.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SigninView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email_or_username = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')
        
        # Try to find user by email or username
        try:
            user_obj = User.objects.get(email=email_or_username)
            username = user_obj.username
        except User.DoesNotExist:
            username = email_or_username
        
        user = authenticate(request, username=username, password=password)

        if user:
            if not user.is_approved:
                return Response({
                    'error': 'Your account is pending admin approval.'
                }, status=status.HTTP_403_FORBIDDEN)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            log_activity(request, 'User Login', f'User logged in: {user.username}')
            return Response({
                'message': 'Login successful!',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class SignoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        log_activity(request, 'User Logout', f'User logged out: {request.user.username}')
        logout(request)
        return Response({'message': 'Logged out successfully'})


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Admin Views
class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'role']


class AdminCreateOfficerView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'officer'
        data['is_approved'] = True  # Admin-created officers are auto-approved
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            log_activity(request, 'Officer Created',
                        f'Admin created officer: {user.username}')
            return Response({
                'message': 'Officer created successfully!',
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_approved = True
            user.save(update_fields=['is_approved'])
            log_activity(request, 'User Created', f'Admin created user: {user.username}')
            return Response({
                'message': 'User created successfully',
                'user': UserProfileSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingOfficersView(generics.ListAPIView):
    queryset = User.objects.filter(role='officer', is_approved=False)
    serializer_class = OfficerApprovalSerializer
    permission_classes = [permissions.IsAdminUser]


class ApproveOfficerView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='officer')
            user.is_approved = True
            user.save()
            log_activity(request, 'Officer Approved', f'Approved officer: {user.username}')
            return Response({'message': f'Officer {user.username} approved!'})
        except User.DoesNotExist:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)


class RejectOfficerView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='officer')
            username = user.username
            user.delete()
            log_activity(request, 'Officer Rejected', f'Rejected officer: {username}')
            return Response({'message': f'Officer {username} rejected and removed.'})
        except User.DoesNotExist:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)


class DeleteUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user == request.user:
                return Response({'error': 'Cannot delete yourself'}, status=status.HTTP_400_BAD_REQUEST)
            username = user.username
            user.delete()
            log_activity(request, 'User Deleted', f'Deleted user: {username}')
            return Response({'message': f'User {username} deleted.'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class AllUsersListView(generics.ListAPIView):
    """List all users - accessible by admin"""
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminUserDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_activity(request, 'User Updated', f'Updated user: {user.username}')
            return Response(UserProfileSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivityLogListView(generics.ListAPIView):
    queryset = ActivityLog.objects.all().select_related('user')
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action', 'user__username', 'details']
    ordering_fields = ['created_at']
