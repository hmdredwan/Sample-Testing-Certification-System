#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rri_backend.settings')
django.setup()

from accounts.models import User

# Delete existing users to recreate them properly
User.objects.all().delete()
print("Cleared existing users")

# Create test users
admin = User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='Admin@123456',
    role='admin'
)
print("[OK] Admin user created")

officer = User.objects.create_user(
    username='officer',
    email='officer@example.com',
    password='Officer@123456',
    role='officer',
    is_approved=True,
    designation='Chief Scientific Officer',
    department='Hydraulics & Geotechnical Research'
)
print("[OK] Officer user created")

technician = User.objects.create_user(
    username='technician',
    email='technician@example.com',
    password='Technician@123456',
    role='lab_technician',
    is_approved=True,
    designation='Senior Lab Analyst',
    department='Soil & Sediment Testing Lab'
)
print("[OK] Lab Technician user created")

inspector = User.objects.create_user(
    username='inspector',
    email='inspector@example.com',
    password='Inspector@123456',
    role='field_inspector',
    is_approved=True,
    designation='Field Inspector',
    department='River Survey Unit'
)
print("[OK] Field Inspector user created")

user = User.objects.create_user(
    username='user',
    email='user@example.com',
    password='User@123456',
    role='user',
    is_approved=True
)
print("[OK] General Client User created")

print(f"\nAll users created successfully: {[u.username + ' (' + u.role + ')' for u in User.objects.all()]}")
