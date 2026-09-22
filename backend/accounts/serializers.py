from rest_framework import serializers
from .models import User, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone', 'address', 'role', 'password', 'designation', 'department']
        extra_kwargs = {'password': {'write_only': True}, 'username': {'required': False}}

    def create(self, validated_data):
        role = validated_data.get('role', 'user')
        is_approved = validated_data.pop('is_approved', True) if 'is_approved' in validated_data else True

        if role == 'officer':
            is_approved = False  # Officers need admin approval

        # Generate username from email if not provided
        username = validated_data.get('username')
        if not username:
            email = validated_data.get('email', '')
            username = email.split('@')[0] if email else f"user_{User.objects.count() + 1}"

        user = User.objects.create_user(
            username=username,
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            role=role,
            designation=validated_data.get('designation', ''),
            department=validated_data.get('department', ''),
            is_approved=is_approved,
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'address', 'designation', 'department']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                  'role', 'is_active', 'designation', 'department']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone', 'address', 'role', 'is_active', 'is_approved', 'designation', 'department',
                  'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_superuser:
            data['role'] = 'admin'
        return data


class OfficerApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone', 'role', 'is_approved', 'designation', 'department', 'created_at']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name',
                           'phone', 'role', 'designation', 'department', 'created_at']


class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'action', 'details', 'ip_address', 'created_at']
