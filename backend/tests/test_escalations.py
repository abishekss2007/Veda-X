import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ============================================================================
# TEST 1: Role-based Escalation Visibility & RLS
# ============================================================================
def test_escalation_role_based_visibility():
    # Admin and PI see all reports
    resp_admin = client.get("/api/escalations", params={"role": "Admin"})
    assert resp_admin.status_code == 200
    admin_reports = resp_admin.json()
    assert len(admin_reports) >= 15

    resp_pi = client.get("/api/escalations", params={"role": "Principal Investigator"})
    assert resp_pi.status_code == 200
    assert len(resp_pi.json()) >= 15

    # Coordinator sees only their own reports
    resp_coord = client.get("/api/escalations", params={"role": "Research Coordinator"})
    assert resp_coord.status_code == 200
    coord_reports = resp_coord.json()
    assert len(coord_reports) < len(admin_reports)
    for r in coord_reports:
        assert r["from_role"] == "Research Coordinator"

    # Doctor sees only their own reports
    resp_doc = client.get("/api/escalations", params={"role": "Doctor / Investigator"})
    assert resp_doc.status_code == 200
    doc_reports = resp_doc.json()
    for r in doc_reports:
        assert r["from_role"] == "Doctor / Investigator"

    # PV Officer sees Safety/AE/SAE escalations
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

    resp = client.post("/api/escalations", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    esc_id = created["id"]
    assert created["status"] == "Sent"
    assert created["urgency"] == "Critical"
    assert created["subject_code"] == "SUB-AIIA-001-042"

    # Verify auto-routing events in thread
    events = created["events"]
    event_messages = [e["message"] for e in events]
    assert any("PV Officer" in m for m in event_messages), "Safety escalation must be auto-copied to PV Officer queue"
    assert any("Ethics Committee" in m for m in event_messages), "Critical SAE must be auto-sent to Ethics Committee"

    # Verify notification dispatches
    # 1. PI & Admin got notification
    resp_pi_notif = client.get("/api/escalations/notifications", params={"role": "Principal Investigator"})
    assert resp_pi_notif.status_code == 200
    pi_notifs = resp_pi_notif.json()
    assert any(n["ref_id"] == esc_id for n in pi_notifs)

    # 2. PV Officer got notification
    resp_pv_notif = client.get("/api/escalations/notifications", params={"role": "PV Officer"})
    assert resp_pv_notif.status_code == 200
    pv_notifs = resp_pv_notif.json()
    assert any(n["ref_id"] == esc_id for n in pv_notifs)

    # 3. EC Member got notification
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
    resp = client.post("/api/escalations", json=payload)
    assert resp.status_code == 201
    esc_id = resp.json()["id"]

    # 2. PI Acknowledges
    ack_payload = {
        "actor_name": "Prof. (Dr.) Rajeshwar Sharma",
        "actor_role": "Principal Investigator",
        "notes": "Acknowledged. Prioritize vernacular sheet before Visit 4."
    }
    resp_ack = client.post(f"/api/escalations/{esc_id}/acknowledge", json=ack_payload)
    assert resp_ack.status_code == 200
    ack_data = resp_ack.json()
    assert ack_data["status"] == "Acknowledged"
    assert "Prof. (Dr.) Rajeshwar Sharma" in ack_data["acknowledged_by"]
    assert ack_data["acknowledged_at"] is not None

    # 3. Coordinator or PI replies
    reply_payload = {
        "actor_name": "Dr. Sunita Patel",
        "actor_role": "Research Coordinator",
        "message": "Hindi consent sheet administered and signed with witness today at 11:30 AM."
    }
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
