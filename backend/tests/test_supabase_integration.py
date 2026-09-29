import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ==============================================================================
# TEST: Wrong Password is refused
# ==============================================================================
def test_supabase_wrong_password_refused():
    resp = client.post("/api/supabase/auth/login", json={
        "email": "coordinator@ayurctms.demo",
        "password": "IncorrectPassword123!",
        "role": "Research Coordinator"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Wrong email or password"

# ==============================================================================
# TEST: Wrong Role for Account is refused
# ==============================================================================
def test_supabase_wrong_role_for_account_refused():
    # User attempts to log into Admin role using Coordinator credentials
    resp = client.post("/api/supabase/auth/login", json={
        "email": "coordinator@ayurctms.demo",
        "password": "Coord@Demo#2026",
        "role": "Admin" # Mismatch
    })
    assert resp.status_code == 403
    assert "not approved for that role" in resp.json()["detail"]

# ==============================================================================
# TEST: 2FA OTP Step & Wrong OTP code is refused
# ==============================================================================
def test_supabase_otp_flow_and_wrong_otp():
    # Step 1: Valid Login triggers 2FA
    login_resp = client.post("/api/supabase/auth/login", json={
        "email": "doctor@ayurctms.demo",
        "password": "Doctor@Demo#2026",
        "role": "Doctor / Investigator"
    })
    assert login_resp.status_code == 200
    assert login_resp.json()["step"] == "VERIFICATION_REQUIRED"
    assert login_resp.json()["demo_code"] == "123456"

    # Step 2: Wrong OTP fails
    otp_fail = client.post("/api/supabase/auth/verify-otp", json={
        "email": "doctor@ayurctms.demo",
        "role": "Doctor / Investigator",
        "otp_code": "999999"
    })
    assert otp_fail.status_code == 400
    assert "Invalid verification code" in otp_fail.json()["detail"]

    # Step 3: Correct OTP succeeds and routes to dashboard
    otp_ok = client.post("/api/supabase/auth/verify-otp", json={
        "email": "doctor@ayurctms.demo",
        "role": "Doctor / Investigator",
        "otp_code": "123456"
    })
    assert otp_ok.status_code == 200
    assert otp_ok.json()["success"] is True
    assert otp_ok.json()["dashboard_route"] == "/dashboard/doctor"

# ==============================================================================
# TEST: Registration DPDP Consent Checkbox Enforced
# ==============================================================================
def test_registration_dpdp_consent_enforced():
    resp = client.post("/api/supabase/auth/register", json={
        "full_name": "Test Investigator",
        "email": "new.user@ayurctms.demo",
        "phone": "9876543210",
        "role": "Doctor / Investigator",
        "site": "SITE-01",
        "password": "Password@123456",
        "confirm_password": "Password@123456",
        "privacy_consent_ticked": False # Unticked!
    })
    assert resp.status_code == 400
    assert "DPDP Act Compliance" in resp.json()["detail"]

# ==============================================================================
# TEST: Submissions Versioning and Regulatory Verification
# ==============================================================================
def test_submissions_version_history_and_verify():
    # 1. Fetch submissions
    res_list = client.get("/api/supabase/submissions")
    assert res_list.status_code == 200
    subs = res_list.json()
    assert len(subs) > 0

    # 2. Assert that editing a 'Verified' submission is blocked (GCP-ASU Data Integrity)
    verified_sub = next(s for s in subs if s["status"] == "Verified")
    blocked_edit = client.put(f"/api/supabase/submissions/{verified_sub['id']}", json={
        "payload": {"notes": "Illegal edit attempt"},
        "reason": "Attempting edit on locked record",
        "changed_by": "Dr. Sunita Patel"
    })
    assert blocked_edit.status_code == 400
    assert "Cannot edit submission" in blocked_edit.json()["detail"]

    # 3. Update a 'Draft' submission with audit reason
    draft_sub = next(s for s in subs if s["status"] in ["Draft", "Needs correction"])
    update_res = client.put(f"/api/supabase/submissions/{draft_sub['id']}", json={
        "title": "Updated Clinical Submission Title",
        "payload": {"notes": "Corrected blood pressure reading"},
        "reason": "Corrected transcription error from hospital case sheet",
        "changed_by": "Dr. Sunita Patel"
    })
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Clinical Submission Title"

    # 4. Formally Verify submission by PI
    verify_res = client.post(f"/api/supabase/submissions/{draft_sub['id']}/verify", json={
        "verified_by": "Prof. Sharma",
        "verifier_role": "Principal Investigator",
        "verifier_email": "pi@ayurctms.demo",
        "note": "Source document verified against raw hospital records."
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "Verified"

# ==============================================================================
# TEST: Row Level Security (Coordinator sees own, PI sees all)
# ==============================================================================
def test_supabase_rls_submission_visibility():
    # 1. Coordinator querying with own ID sees only their submissions
    coord_res = client.get("/api/supabase/submissions?owner_id=usr-coord-01&role=Research%20Coordinator")
    assert coord_res.status_code == 200
    coord_data = coord_res.json()
    assert all(s["owner_id"] == "usr-coord-01" for s in coord_data)
    # Coordinator does NOT see doctor's submission (sub-103)
    assert not any(s["id"] == "sub-103" for s in coord_data)

    # 2. PI querying sees all submissions across researchers
    pi_res = client.get("/api/supabase/submissions?owner_id=usr-pi-01&role=Principal%20Investigator")
    assert pi_res.status_code == 200
    pi_data = pi_res.json()
    # PI sees doctor's submission as well
    assert any(s["id"] == "sub-103" for s in pi_data)

# ==============================================================================
# TEST: Account Lockout after 5 consecutive failed attempts
# ==============================================================================
def test_supabase_account_lockout_after_five_attempts():
    target_email = "pv@ayurctms.demo"
    
    # 4 failed attempts: returns 401
    for i in range(4):
        res = client.post("/api/supabase/auth/login", json={
            "email": target_email,
            "password": "WrongPasswordAttempt!",
            "role": "PV Officer"
        })
        assert res.status_code == 401

    # 5th attempt locks the account
    fifth_res = client.post("/api/supabase/auth/login", json={
        "email": target_email,
        "password": "WrongPasswordAttempt!",
        "role": "PV Officer"
    })
    assert fifth_res.status_code == 401

    # 6th attempt is blocked by 403 Forbidden with lockout notification
    locked_res = client.post("/api/supabase/auth/login", json={
        "email": target_email,
        "password": "Pharma@Demo#2026", # Even correct password is now blocked
        "role": "PV Officer"
    })
    assert locked_res.status_code == 403
    assert "temporarily locked" in locked_res.json()["detail"]

# ==============================================================================
# TEST: SUPABASE_SECRET_KEY is never leaked in status endpoint or UI
# ==============================================================================
def test_supabase_status_does_not_leak_secrets():
    res = client.get("/api/supabase/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_configured" in data
    assert "mode" in data
    # Ensure neither secret key nor publishable key is returned in clear text
    raw_text = res.text
    assert "sb_secret" not in raw_text
    assert "SUPABASE_SECRET_KEY" not in raw_text

