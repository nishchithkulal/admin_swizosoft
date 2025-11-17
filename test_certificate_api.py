#!/usr/bin/env python
"""Test the certificate generation API directly"""

import os
import sys
import base64
import json
from datetime import datetime

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config
from models import db, ApprovedCandidate
from admin_app import app, generate_certificate_pdf, GENERATED_CERTS_PATH

# Setup Flask app context
app_config = get_config()
app.config.from_object(app_config)

print("=" * 70)
print("CERTIFICATE GENERATION TEST")
print("=" * 70)
print()

# Test 1: Check paths
print("[TEST 1] Checking paths...")
print(f"  SWIZ_CERTI exists: {os.path.exists(os.path.join(os.path.dirname(__file__), 'SWIZ CERTI'))}")
print(f"  Generated folder: {GENERATED_CERTS_PATH}")
print(f"  Generated exists: {os.path.exists(GENERATED_CERTS_PATH)}")
print()

# Test 2: Generate a test certificate directly
print("[TEST 2] Testing certificate generation function...")
try:
    candidate_name = "JOHN SMITH"
    cert_path, cert_id = generate_certificate_pdf(candidate_name)
    
    if os.path.exists(cert_path):
        size = os.path.getsize(cert_path)
        print(f"  SUCCESS! Certificate generated")
        print(f"    Certificate ID: {cert_id}")
        print(f"    Path: {cert_path}")
        print(f"    Size: {size} bytes")
    else:
        print(f"  FAILED! Certificate not found at {cert_path}")
except Exception as e:
    print(f"  ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Check database connection
print("[TEST 3] Checking database...")
try:
    with app.app_context():
        candidates_count = ApprovedCandidate.query.count()
        print(f"  Total approved candidates: {candidates_count}")
        
        if candidates_count > 0:
            candidate = ApprovedCandidate.query.first()
            print(f"  First candidate: ID={candidate.user_id}, Name={candidate.name}")
        else:
            print(f"  WARNING: No approved candidates found in database")
except Exception as e:
    print(f"  ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
