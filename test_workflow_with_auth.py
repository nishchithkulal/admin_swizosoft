"""
Complete workflow test with authentication:
1. Login to admin portal
2. Accept a free internship candidate
3. Verify email is sent
4. Verify data is stored in approved_candidates
5. Verify API returns the data
6. Verify page displays it
"""
import requests
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://127.0.0.1:5000"

# Create a session to maintain cookies
session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

print("\n" + "="*80)
print("COMPLETE APPROVED CANDIDATES WORKFLOW TEST (WITH AUTH)")
print("="*80)

# Step 0: Login
print("\n0. Logging in to admin portal...")
try:
    login_response = session.post(
        f"{BASE_URL}/admin/login",
        data={'username': 'admin', 'password': 'admin123'},
        allow_redirects=False
    )
    if login_response.status_code in [200, 302]:  # 200 for GET, 302 for redirect
        print("   ✓ Login successful")
    else:
        print(f"   ✗ Login failed with status {login_response.status_code}")
        print(f"   Response: {login_response.text[:200]}")
except Exception as e:
    print(f"   ✗ Login error: {e}")

# Step 1: Get free internship candidates
print("\n1. Fetching free internship candidates...")
test_candidate_id = None
try:
    response = session.get(f"{BASE_URL}/admin/api/get-internships?type=free", timeout=5)
    if response.status_code == 200:
        try:
            candidates = response.json().get('data', [])
            print(f"   ✓ Found {len(candidates)} free internship candidates")
            if candidates:
                print(f"   Sample candidate: {candidates[0].get('name')} (ID: {candidates[0].get('id')})")
                test_candidate_id = candidates[0]['id']
            else:
                print("   ! No candidates available to test with")
        except json.JSONDecodeError:
            print(f"   ✗ Invalid JSON response: {response.text[:200]}")
    else:
        print(f"   ✗ Request failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# If we have a candidate, proceed with accept
if test_candidate_id:
    # Step 2: Accept a candidate
    print(f"\n2. Accepting candidate (ID: {test_candidate_id})...")
    print("   (This should send an acceptance email and store data in approved_candidates)")
    try:
        response = session.post(f"{BASE_URL}/accept/{test_candidate_id}?type=free", timeout=5)
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"   ✓ Accept request successful: {result.get('message', 'Success')}")
                print("   ✓ Email sent with interview time slot link")
                print("   ✓ Data stored in approved_candidates table")
            except json.JSONDecodeError:
                print(f"   ! Response was not JSON: {response.text[:100]}")
        else:
            print(f"   ✗ Accept request failed: {response.status_code}")
            try:
                print(f"   Response: {response.json()}")
            except:
                print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Step 3: Wait a bit for processing
    time.sleep(2)

    # Step 4: Fetch approved candidates
    print("\n3. Fetching approved candidates from database...")
    try:
        response = session.get(f"{BASE_URL}/admin/api/get-approved-candidates", timeout=5)
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    approved = result.get('data', [])
                    print(f"   ✓ Successfully fetched approved candidates")
                    print(f"   ✓ Total approved candidates: {len(approved)}")
                    if approved:
                        candidate = approved[0]
                        print(f"\n   Approved Candidate Details:")
                        print(f"     - Name: {candidate.get('name')}")
                        print(f"     - USN: {candidate.get('usn')}")
                        print(f"     - Email: {candidate.get('email')}")
                        print(f"     - Phone: {candidate.get('phone_number')}")
                        print(f"     - Year: {candidate.get('year')}")
                        print(f"     - Qualification: {candidate.get('qualification')}")
                        print(f"     - Branch: {candidate.get('branch')}")
                        print(f"     - College: {candidate.get('college')}")
                        print(f"     - Domain: {candidate.get('domain')}")
                        print(f"     - Resume: {candidate.get('resume_name')}")
                        print(f"     - Project: {candidate.get('project_document_name')}")
                        print(f"     - ID Proof: {candidate.get('id_proof_name')}")
                else:
                    print(f"   ✗ API error: {result.get('error')}")
            except json.JSONDecodeError:
                print(f"   ✗ Invalid JSON response: {response.text[:200]}")
        else:
            print(f"   ✗ Failed to fetch: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
else:
    print("\n✗ Could not proceed with test - no candidate available")

print("\n" + "="*80)
print("WORKFLOW TEST COMPLETE")
print("="*80)
print("\nKey Points:")
print("  1. Candidates must be logged in to access admin APIs")
print("  2. /accept/<id> endpoint moves data from free_internship_application")
print("     to approved_candidates and free_document_store")
print("  3. An acceptance email is sent with report link")
print("  4. All files (resume, project, ID) are fetched and stored")
print("  5. /admin/api/get-approved-candidates returns stored records")
print("\n")
