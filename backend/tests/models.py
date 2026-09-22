from django.db import models
from accounts.models import User
import uuid


class TestType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=100, blank=True, null=True)
    sample_requirements = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_types'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - ${self.price}"



class TestRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('testing', 'Testing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    SAMPLE_CATEGORY_CHOICES = (
        ('riverbed_soil', 'Riverbed Soil'),
        ('sediment', 'Sediment'),
        ('water', 'Water Quality'),
        ('concrete_block', 'Concrete / Construction Material'),
        ('geotextile', 'Geotextile'),
        ('other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_requests')
    test_type = models.ForeignKey(TestType, on_delete=models.CASCADE, related_name='requests')
    officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='assigned_tests')
    lab_technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='technician_samples')
    field_inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='inspected_samples')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sample_tag_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    sample_category = models.CharField(max_length=50, choices=SAMPLE_CATEGORY_CHOICES, default='riverbed_soil')
    sampling_location = models.CharField(max_length=255, blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)
    sample_description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    result = models.TextField(blank=True, null=True)
    lab_measurements = models.TextField(blank=True, null=True)
    status_updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'test_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.test_type.name} ({self.status})"


class TestAssignment(models.Model):
    """Tracks which officers are assigned to which test types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test_type = models.ForeignKey(TestType, on_delete=models.CASCADE, related_name='officer_assignments')
    officer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_assignments')
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'test_assignments'
        unique_together = ('test_type', 'officer')

    def __str__(self):
        return f"{self.officer.username} -> {self.test_type.name}"


class SampleCustodyLog(models.Model):
    """Tracks physical sample chain of custody transfers"""
    CUSTODY_STAGE_CHOICES = (
        ('collected_field', 'Collected in Field'),
        ('received_reception', 'Received at Lab Reception'),
        ('delivered_lab', 'Delivered to Specialized Lab'),
        ('in_testing', 'Testing in Progress'),
        ('storage', 'Moved to Sample Storage'),
        ('completed', 'Testing Completed & Archived'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test_request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='custody_logs')
    stage = models.CharField(max_length=50, choices=CUSTODY_STAGE_CHOICES, default='received_reception')
    transferred_from = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='custody_transfers_from')
    transferred_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='custody_transfers_to')
    location = models.CharField(max_length=255, blank=True, null=True)
    custody_notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sample_custody_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Custody Transfer for {self.test_request.sample_tag_id or self.test_request.id} - {self.stage}"


class TestCertificate(models.Model):
    """Digital Certificate issued upon test completion with dynamic QR code verification"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test_request = models.OneToOneField(TestRequest, on_delete=models.CASCADE, related_name='certificate')
    certificate_number = models.CharField(max_length=100, unique=True)
    verification_code = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    digital_signature_hash = models.CharField(max_length=255, blank=True, null=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        db_table = 'test_certificates'
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.test_request.test_type.name}"

