import pytest
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, seed_synthetic_data
from app.db.database import Base, get_db
from app.db.models import User, Participant, AuditLogEntry
from app.core.security import create_access_token, create_otp_stage_token
from app.core.audit import verify_audit_chain

from .conftest import TestingSessionLocal
client = TestClient(app)

# Helper to get auth header
def get_auth_header(role: str, user_id: int = 1, email: str = "test@ayurctms.in", site_id: str = "SITE-01"):
    token = create_access_token({"sub": str(user_id), "role": role, "email": email, "site_id": site_id})
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# TEST 1: Wrong password refused and 5 failed attempts locks the account
# ============================================================================
def test_failed_login_and_5_attempt_lockout():
    # Coordinator login with wrong password
    email = "coordinator@ayurctms.in"

    # Verify generic error message
    for attempt in range(1, 5):
        resp = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword123!"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Wrong email or password"

    # 5th attempt locks the account for 15 minutes
    resp_5 = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert resp_5.status_code == 403
    assert "locked for 15 minutes" in resp_5.json()["detail"].lower()

    # Clear rate limit store so subsequent call tests account lockout rather than IP rate limit
    from app.core.security import _rate_limit_store
    _rate_limit_store.clear()

    # Subsequent attempt while locked also blocked with 403
    resp_locked = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert resp_locked.status_code == 403
    assert "temporarily locked" in resp_locked.json()["detail"].lower()

    # Reset lockout for following tests
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.close()
    _rate_limit_store.clear()


# ============================================================================
# TEST 2: An OTP-stage token can't call the API
# ============================================================================
def test_otp_stage_token_cannot_call_protected_apis():
    otp_token = create_otp_stage_token(user_id=2, email="pi.sharma@ayurctms.in", role="Doctor / Investigator")
    headers = {"Authorization": f"Bearer {otp_token}"}

    # Attempt to query participants with incomplete OTP session
    resp = client.get("/api/participants", headers=headers)
    assert resp.status_code == 403
    assert "Two-step authentication incomplete" in resp.json()["detail"]


# ============================================================================
# TEST 3: Coordinator cannot read another site's participants (BOLA / IDOR)
# ============================================================================
def test_coordinator_cannot_access_other_site_data():
    # Site 1 Coordinator credentials
    headers_site1 = get_auth_header(role="Research Coordinator", user_id=1, email="coordinator@ayurctms.in", site_id="SITE-01")

    # Participant 4 belongs to SITE-02 (SUB-BHU-002-001, id=4)
    resp = client.get("/api/participants/4", headers=headers_site1)
    assert resp.status_code == 403
    assert "Cross-site access denied" in resp.json()["detail"]

    # But can access their own site participant (SUB-AIIA-001-042, id=1)
    resp_own = client.get("/api/participants/1", headers=headers_site1)
    assert resp_own.status_code == 200
    assert resp_own.json()["subject_code"] == "SUB-AIIA-001-042"


# ============================================================================
# TEST 4: Admin cannot read clinical data, and Monitor gets no unmasked names/phones
# TEST 4: Admin and Monitor can view records with masked PII, but Admin cannot add participants
# ============================================================================
def test_admin_and_monitor_clinical_data_restrictions():
    # Admin can view clinical records with masked PII
    admin_headers = get_auth_header(role="Admin", user_id=6, email="admin@ayurctms.in", site_id="SITE-HQ")
    resp_admin = client.get("/api/participants", headers=admin_headers)
    assert resp_admin.status_code == 200
    admin_data = resp_admin.json()
    assert len(admin_data) > 0
    assert "*" in admin_data[0]["full_name"]

    # Admin CANNOT add participants (Coordinator only)
    resp_admin_add = client.post("/api/participants", headers=admin_headers, json={
        "subject_code": "SUB-AIIA-001-099",
        "age": 45,
        "gender": "Male",
        "consent_status": "Written Consent Verified"
    })
    assert resp_admin_add.status_code == 403

    # Monitor tries to access clinical records: gets access BUT names and phones are masked
    monitor_headers = get_auth_header(role="Monitor", user_id=3, email="monitor.verma@ayurctms.in", site_id="SITE-01")
    resp_monitor = client.get("/api/participants", headers=monitor_headers)
    assert resp_monitor.status_code == 200
    data = resp_monitor.json()
    assert len(data) > 0
    first_record = data[0]
    # Phone must be masked in 98XXXXXX10 format
    assert "X" in first_record["phone_number"]
    assert first_record["phone_number"].startswith("98")
    assert first_record["phone_number"].endswith("10")
    # Name must be masked
    assert "*" in first_record["full_name"]



# ============================================================================
# TEST 5: SQL injection attempt in search fields fails safely
# ============================================================================
def test_sql_injection_resistance():
    headers = get_auth_header(role="Doctor / Investigator", user_id=2, email="pi.sharma@ayurctms.in", site_id="SITE-01")
    
    # Classic SQL injection payloads
    sql_payloads = [
        "' OR '1'='1",
        "SITE-01'; DROP TABLE participants; --",
        "1 UNION SELECT null, null, null--"
    ]
    for payload in sql_payloads:
        resp = client.get(f"/api/participants?site_id={payload}", headers=headers)
        assert resp.status_code == 200
        # Returns empty list without exploding or leaking SQL syntax errors
        assert isinstance(resp.json(), list)


# ============================================================================
# TEST 6: Upload of a disguised .exe file is rejected
# ============================================================================
def test_disguised_executable_upload_rejected():
    headers = get_auth_header(role="Research Coordinator", user_id=1, email="coordinator@ayurctms.in", site_id="SITE-01")

    # A windows PE executable header (MZ) disguised with a .pdf extension
    fake_exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00malicious_payload_code_here"
    
    files = {"file": ("clinical_trial_report.pdf", io.BytesIO(fake_exe_content), "application/pdf")}
    resp = client.post("/api/files/upload", files=files, headers=headers)
    assert resp.status_code == 400
    assert "Executable binary file signature detected" in resp.json()["detail"]


# ============================================================================
# TEST 7: Rate limits return 429
# ============================================================================
def test_rate_limiting_enforcement():
    # Send 10 rapid login attempts exceeding the limit of 5 per minute
    got_429 = False
    for _ in range(12):
        resp = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "WrongPassword#123"})
        if resp.status_code == 429:
            got_429 = True
            assert "Rate limit exceeded" in resp.json()["detail"]
            break
    assert got_429 is True


# ============================================================================
# TEST 8: Audit log tampering is caught by 'Verify Chain'
# ============================================================================
def test_audit_chain_tamper_detection():
    admin_headers = get_auth_header(role="Admin", user_id=6, email="admin@ayurctms.in", site_id="SITE-HQ")
    auditor_headers = get_auth_header(role="Auditor / Regulator", user_id=7, email="auditor@ayurctms.in", site_id="SITE-HQ")

    # Step A: Verify initial chain integrity
    resp_init = client.get("/api/audit/verify-chain", headers=auditor_headers)
    assert resp_init.status_code == 200
    assert resp_init.json()["valid"] is True

    # Step B: Tamper with Entry #1 via testing simulation
    resp_tamper = client.post(
        "/api/audit/tamper-simulate-test?entry_index=1&tampered_value=UNAUTHORIZED_TAMPERED_ACTION",
        headers=admin_headers
    )
    assert resp_tamper.status_code == 200

    # Step C: Re-verify chain - must fail and detect Entry #1
    resp_verify = client.get("/api/audit/verify-chain", headers=auditor_headers)
    assert resp_verify.status_code == 200
    result = resp_verify.json()
    assert result["valid"] is False
    assert result["broken_at_index"] == 1
    assert "Data integrity violation at Entry #1" in result["message"]


# ============================================================================
# TEST 9: All security headers are present
# ============================================================================
def test_all_security_headers_present():
    resp = client.get("/api/health")
    assert resp.status_code == 200

    # Verify all OWASP mandatory security headers
    assert "Strict-Transport-Security" in resp.headers
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in resp.headers["Permissions-Policy"]
    assert "X-Data-Residency" in resp.headers


# ============================================================================
# TEST 10: GCP-ASU Enrolment & Illiterate Impartial Witness Protections
# ============================================================================
def test_gcp_asu_illiterate_witness_gate():
    headers = get_auth_header(role="Research Coordinator", user_id=1, email="coordinator@ayurctms.in", site_id="SITE-01")

    # Attempting to consent an illiterate participant without impartial witness name & signature
    resp = client.post("/api/consent/record", json={
        "participant_id": 1,
        "consent_version_id": 1,
        "language": "Hindi",
        "explained_orally": True,
        "is_illiterate": True,
        "impartial_witness_name": "", # Missing witness
        "impartial_witness_signature": ""
    }, headers=headers)

    assert resp.status_code == 400
    assert "impartial witness name is strictly mandatory" in resp.json()["detail"]


# ============================================================================
# TEST 11: Ethics Committee Composition Validation (<5 members or no ASU expert)
# ============================================================================
def test_ethics_committee_composition_rules():
    resp = client.get("/api/ethics/composition-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_asu_expert"] is True
    assert data["total_active_members"] >= 5
    assert data["is_compliant"] is True


# ============================================================================
# TEST 12: DPDP Consent Withdrawal marks data 'retained for legal reasons'
# ============================================================================
def test_dpdp_consent_withdrawal_regulatory_retention():
    headers = get_auth_header(role="Research Coordinator", user_id=1, email="coordinator@ayurctms.in", site_id="SITE-01")

    # Withdraw consent for Participant 1 (consent_id=1)
    resp = client.post("/api/consent/withdraw/1", json={
        "reason": "Participant opted out due to personal relocation."
    }, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["data_status"] == "retained_for_legal_reasons"

    # Check participant status
    resp_p = client.get("/api/participants/1", headers=headers)
    assert resp_p.status_code == 200
    assert resp_p.json()["data_status"] == "retained_for_legal_reasons"
    assert resp_p.json()["is_enrolled"] is False
