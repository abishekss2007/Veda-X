import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def set_demo_session(role, email=None, site="SITE-01"):
    email = email or f"{role.split()[0].lower()}@ayurctms.demo"
    token = create_access_token({
        "sub": f"demo:{email}",
        "email": email,
        "role": role,
        "full_name": f"Test {role}",
        "site_id": site,
        "principal_type": "demo",
    })
    client.cookies.set("ayur_access_token", token)

# ============================================================================
# TEST 1: Role-based Escalation Visibility & RLS
# ============================================================================
def test_escalation_role_based_visibility():
    # Admin and PI see all reports
    set_demo_session("Admin")
    resp_admin = client.get("/api/escalations", params={"role": "Admin"})
    assert resp_admin.status_code == 200
    admin_reports = resp_admin.json()
    assert len(admin_reports) >= 15

    set_demo_session("Principal Investigator")
    resp_pi = client.get("/api/escalations", params={"role": "Principal Investigator"})
    assert resp_pi.status_code == 200
    assert len(resp_pi.json()) >= 15

    # Coordinator sees only their own reports
    set_demo_session("Research Coordinator")
    resp_coord = client.get("/api/escalations", params={"role": "Admin"})
    assert resp_coord.status_code == 200
    coord_reports = resp_coord.json()
    assert len(coord_reports) < len(admin_reports)
    for r in coord_reports:
        assert r["from_role"] == "Research Coordinator"

    # Doctor sees only their own reports
    set_demo_session("Doctor / Investigator")
    resp_doc = client.get("/api/escalations", params={"role": "Doctor / Investigator"})
    assert resp_doc.status_code == 200
    doc_reports = resp_doc.json()
    for r in doc_reports:
        assert r["from_role"] == "Doctor / Investigator"

    # PV Officer sees Safety/AE/SAE escalations
    set_demo_session("PV Officer")
    resp_pv = client.get("/api/escalations", params={"role": "PV Officer"})
    assert resp_pv.status_code == 200
    pv_reports = resp_pv.json()
    for r in pv_reports:
        is_safety = (
            r["category"] == "Safety"
            or "ae" in r["summary"].lower()
            or "sae" in r["summary"].lower()
            or r["from_role"] == "PV Officer"
        )
        assert is_safety

    # EC Member sees Ethics and Critical escalations
    set_demo_session("EC Member")
    resp_ec = client.get("/api/escalations", params={"role": "EC Member"})
    assert resp_ec.status_code == 200
    ec_reports = resp_ec.json()
    for r in ec_reports:
        is_ethics_or_critical = (
            r["category"] == "Ethics"
            or r["urgency"] == "Critical"
            or r["from_role"] == "EC Member"
        )
        assert is_ethics_or_critical


# ============================================================================
# TEST 2: Doctor Submits Critical SAE Escalation -> Auto-copy PV and EC
# ============================================================================
def test_create_critical_sae_escalation_workflow():
    payload = {
        "from_user": "usr-doc-01",
        "from_name": "Dr. Arvind Joshi",
        "from_role": "Doctor / Investigator",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-042",
        "category": "Safety",
        "urgency": "Critical",
        "summary": "Suspected Severe Pitta-Kopa Reaction with Jaundice",
        "details": "Subject presented with icterus, severe pruritus, and elevated bilirubin. Dosing discontinued immediately.",
        "attachment_name": "bilirubin_panel_042.pdf"
    }

    set_demo_session("Doctor / Investigator", email="doctor@ayurctms.demo")
    payload["from_name"] = "Client supplied name"
    payload["from_role"] = "Admin"
    payload["site_id"] = "SITE-99"
    resp = client.post("/api/escalations", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    esc_id = created["id"]
    assert created["status"] == "Sent"
    assert created["urgency"] == "Critical"
    assert created["subject_code"] == "SUB-AIIA-001-042"
    assert created["from_role"] == "Doctor / Investigator"
    assert created["from_user"] == "doctor@ayurctms.demo"
    assert created["site_id"] == "SITE-01"

    # Verify auto-routing events in thread
    events = created["events"]
    event_messages = [e["message"] for e in events]
    assert any("PV Officer" in m for m in event_messages), "Safety escalation must be auto-copied to PV Officer queue"
    assert any("Ethics Committee" in m for m in event_messages), "Critical SAE must be auto-sent to Ethics Committee"

    # Verify notification dispatches
    # 1. PI & Admin got notification
    set_demo_session("Principal Investigator", email="pi@ayurctms.demo", site="SITE-HQ")
    resp_pi_notif = client.get("/api/escalations/notifications", params={"role": "Principal Investigator"})
    assert resp_pi_notif.status_code == 200
    pi_notifs = resp_pi_notif.json()
    assert any(n["ref_id"] == esc_id for n in pi_notifs)

    # 2. PV Officer got notification
    set_demo_session("PV Officer", email="pv@ayurctms.demo")
    resp_pv_notif = client.get("/api/escalations/notifications", params={"role": "PV Officer"})
    assert resp_pv_notif.status_code == 200
    pv_notifs = resp_pv_notif.json()
    assert any(n["ref_id"] == esc_id for n in pv_notifs)

    # 3. EC Member got notification
    set_demo_session("EC Member", email="ec@ayurctms.demo")
    resp_ec_notif = client.get("/api/escalations/notifications", params={"role": "EC Member"})
    assert resp_ec_notif.status_code == 200
    ec_notifs = resp_ec_notif.json()
    assert any(n["ref_id"] == esc_id for n in ec_notifs)


# ============================================================================
# TEST 3: Escalation Action Lifecycle (Acknowledge -> Reply -> Assign -> Resolve)
# ============================================================================
def test_escalation_lifecycle_actions():
    # 1. Create a High urgency report
    payload = {
        "from_user": "usr-coord-01",
        "from_name": "Dr. Sunita Patel",
        "from_role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-002",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-019",
        "category": "Consent",
        "urgency": "High",
        "summary": "Vernacular Re-consent Form signature missing",
        "details": "Protocol amendment v2 signed in English but Hindi version requires witness re-verification.",
        "attachment_name": None
    }
    set_demo_session("Research Coordinator", email="coordinator@ayurctms.demo")
    resp = client.post("/api/escalations", json=payload)
    assert resp.status_code == 201
    esc_id = resp.json()["id"]

    # 2. PI Acknowledges
    ack_payload = {
        "actor_name": "Prof. (Dr.) Rajeshwar Sharma",
        "actor_role": "Principal Investigator",
        "notes": "Acknowledged. Prioritize vernacular sheet before Visit 4."
    }
    set_demo_session("Principal Investigator", email="pi@ayurctms.demo", site="SITE-HQ")
    resp_ack = client.post(f"/api/escalations/{esc_id}/acknowledge", json=ack_payload)
    assert resp_ack.status_code == 200
    ack_data = resp_ack.json()
    assert ack_data["status"] == "Acknowledged"
    assert "Test Principal Investigator" in ack_data["acknowledged_by"]
    assert ack_data["acknowledged_at"] is not None

    # 3. Coordinator or PI replies
    reply_payload = {
        "actor_name": "Dr. Sunita Patel",
        "actor_role": "Research Coordinator",
        "message": "Hindi consent sheet administered and signed with witness today at 11:30 AM."
    }
    set_demo_session("Research Coordinator", email="coordinator@ayurctms.demo")
    resp_reply = client.post(f"/api/escalations/{esc_id}/reply", json=reply_payload)
    assert resp_reply.status_code == 200
    reply_data = resp_reply.json()
    assert any("Hindi consent sheet administered" in e["message"] for e in reply_data["events"])

    # 4. PI Assigns to Quality Monitor
    assign_payload = {
        "actor_name": "Prof. (Dr.) Rajeshwar Sharma",
        "actor_role": "Principal Investigator",
        "assign_to": "Vikram Verma (Monitor)",
        "notes": "Verify during next routine SDV audit visit."
    }
    set_demo_session("Principal Investigator", email="pi@ayurctms.demo", site="SITE-HQ")
    resp_assign = client.post(f"/api/escalations/{esc_id}/assign", json=assign_payload)
    assert resp_assign.status_code == 200
    assign_data = resp_assign.json()
    assert assign_data["status"] == "In progress"
    assert assign_data["assigned_to"] == "Vikram Verma (Monitor)"

    # 5. Admin or PI Resolves
    resolve_payload = {
        "actor_name": "System Administrator",
        "actor_role": "Admin",
        "resolution_notes": "Monitor verified vernacular sheet and witness thumbprint match GCP-ASU criteria. Closed."
    }
    set_demo_session("Admin", email="admin@ayurctms.demo", site="SITE-HQ")
    resp_resolve = client.post(f"/api/escalations/{esc_id}/resolve", json=resolve_payload)
    assert resp_resolve.status_code == 200
    resolve_data = resp_resolve.json()
    assert resolve_data["status"] == "Resolved"
    assert resolve_data["resolved_at"] is not None
    assert "Monitor verified vernacular sheet" in resolve_data["resolution_notes"]


# ============================================================================
# TEST 4: Immutability - Reports Cannot be Deleted
# ============================================================================
def test_escalation_delete_not_allowed():
    # DELETE method is rejected per GCP-ASU immutable audit trial requirements
    resp_del = client.delete("/api/escalations/esc-101")
    assert resp_del.status_code in [404, 405], "Escalation deletion must be forbidden (append-only)"


# ============================================================================
# TEST 5: Comprehensive Synthetic Clinical Dataset & Zero PII Verification
# ============================================================================
def test_study_data_integrity_and_zero_pii():
    set_demo_session("Research Coordinator", email="coordinator@ayurctms.demo")
    resp = client.get("/api/escalations/study-data")
    assert resp.status_code == 200
    data = resp.json()

    # 6 studies
    assert len(data["studies"]) == 6
    # 4 sites
    assert len(data["sites"]) == 4
    # 150 participants
    assert data["total_participants"] == 150
    assert len(data["participants"]) == 150
    # 60 Adverse Events (8 SAEs)
    assert data["total_aes"] == 60
    assert data["total_saes"] == 8

    # Zero PII check: Every participant must have a subject_code, NO 'name' or personal identifiers
    for p in data["participants"]:
        assert "subject_code" in p
        assert p["subject_code"].startswith("SUB-AIIA-")
        assert "name" not in p
        assert "phone" not in p
        assert "email" not in p
        assert "aadhaar" not in p

    # Adverse events check
    sae_count = sum(1 for ae in data["adverse_events"] if ae["is_sae"])
    assert sae_count == 8


def test_private_report_attachment_upload_and_link(tmp_path, monkeypatch):
    from app.api import files as file_api

    monkeypatch.setattr(file_api, "UPLOAD_STORAGE_DIR", str(tmp_path))
    client.cookies.clear()
    file_data = ("report.pdf", b"%PDF-1.7\nsynthetic test document", "application/pdf")
    assert client.post("/api/files/upload", files={"file": file_data}).status_code == 401

    set_demo_session("Research Coordinator", email="coordinator@ayurctms.demo")
    upload = client.post("/api/files/upload", files={"file": file_data})
    assert upload.status_code == 200
    upload_result = upload.json()
    assert upload_result["original_filename"] == "report.pdf"
    assert (tmp_path / upload_result["safe_storage_name"]).exists()

    download = client.get(upload_result["signed_download_url"])
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")

    report = client.post("/api/escalations", json={
        "from_name": "Client-provided name",
        "from_role": "Admin",
        "category": "Other",
        "urgency": "Normal",
        "summary": "Attachment upload integration check",
        "details": "Synthetic test only.",
        "attachment_name": upload_result["original_filename"],
        "attachment_url": upload_result["signed_download_url"],
    })
    assert report.status_code == 201
    assert report.json()["attachment_name"] == "report.pdf"
    assert report.json()["attachment_url"] == upload_result["signed_download_url"]
