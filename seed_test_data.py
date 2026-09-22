#!/usr/bin/env python
import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rri_backend.settings')
django.setup()

from accounts.models import User
from tests.models import TestType, TestRequest, SampleCustodyLog, TestCertificate
from utils.pdf_generator import generate_test_certificate_pdf
from utils.barcode_generator import generate_sample_tag_id

print("Seeding test types...")
t1, _ = TestType.objects.get_or_create(
    name="Grain Size Analysis (Sieve & Hydrometer)",
    defaults={
        "description": "Particle size distribution analysis of riverbed sediment and soil samples according to ASTM D422.",
        "details": "Determines silt, clay, and sand fractions for river hydraulic model calibration.",
        "price": 4500.00,
        "duration": "3 Days",
        "sample_requirements": "Minimum 1.0 kg dried sediment/soil sample",
        "is_active": True
    }
)

t2, _ = TestType.objects.get_or_create(
    name="Direct Shear & Soil Cohesion Test",
    defaults={
        "description": "Consolidated drained direct shear test to determine shear strength parameters (c and phi).",
        "details": "Essential for embankment stability and riverbank erosion risk assessments.",
        "price": 8500.00,
        "duration": "5 Days",
        "sample_requirements": "3 undisturbed cylindrical soil core samples",
        "is_active": True
    }
)

t3, _ = TestType.objects.get_or_create(
    name="River Water Salinity & Hydro-Chemical Quality",
    defaults={
        "description": "Quantitative analysis of pH, Salinity (ppt), Electrical Conductivity (EC), and Total Dissolved Solids (TDS).",
        "details": "Monitors estuarine intrusion and coastal river water quality.",
        "price": 3200.00,
        "duration": "2 Days",
        "sample_requirements": "500ml water sample in airtight sterile bottle",
        "is_active": True
    }
)

print("[OK] Test types seeded.")

# Fetch users
client_user = User.objects.get(username='user')
officer_user = User.objects.get(username='officer')
tech_user = User.objects.get(username='technician')
inspector_user = User.objects.get(username='inspector')

# Seed a completed test request with digital certificate
req1, created = TestRequest.objects.get_or_create(
    user=client_user,
    test_type=t1,
    defaults={
        "status": "completed",
        "sample_category": "riverbed_soil",
        "sampling_location": "Padma River - Mawa Point (23.472 N, 90.261 E)",
        "collection_date": "2026-09-01",
        "sample_description": "Undisturbed riverbed soil core collected at 4.0m depth.",
        "result": "Grain Size Distribution: Sand 42.5%, Silt 48.0%, Clay 9.5%. Soil Classification: Silty Sand (SM). Complies with RRI Standard SOP-2026.",
        "lab_measurements": "- D10: 0.012 mm\n- D30: 0.045 mm\n- D60: 0.180 mm\n- Coefficient of Uniformity (Cu): 15.0\n- Coefficient of Curvature (Cc): 0.94",
        "officer": officer_user,
        "lab_technician": tech_user,
        "field_inspector": inspector_user
    }
)
req1.sample_tag_id = generate_sample_tag_id(req1.id)
req1.save()

# Custody Log for req1
SampleCustodyLog.objects.get_or_create(
    test_request=req1,
    stage="completed",
    defaults={
        "transferred_from": tech_user,
        "location": "RRI Geotechnical Lab Archive",
        "custody_notes": "Sample analysis completed and archived."
    }
)

# Certificate for req1
cert, cert_created = TestCertificate.objects.get_or_create(
    test_request=req1,
    defaults={
        "certificate_number": "RRI-CERT-2026-PADMA01",
        "verification_code": "VERIFY-RRI-2026-PADMA-001",
        "issued_by": officer_user,
        "digital_signature_hash": "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
        "is_valid": True
    }
)

print(f"[OK] Seeded completed TestRequest with Certificate: {cert.certificate_number} (Code: {cert.verification_code})")

# Test PDF Generation
pdf_bytes = generate_test_certificate_pdf(cert)
print(f"[OK] Test Certificate PDF generated successfully ({len(pdf_bytes)} bytes)")
