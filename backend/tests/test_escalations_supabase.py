import copy
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api import escalations


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Minimal stand-in for the Supabase query builder, backed by a dict of lists."""
    def __init__(self, store, table):
        self.store, self.table = store, table
        self.filters, self.op, self.payload, self.columns = [], "select", None, "*"

    def select(self, columns="*"):
        self.columns = columns
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args):
        return self

    def execute(self):
        rows = self.store.setdefault(self.table, [])
        if self.op == "insert":
            new_rows = self.payload if isinstance(self.payload, list) else [self.payload]
            new_rows = [{"id": str(uuid.uuid4()), **row} for row in new_rows]
            rows.extend(new_rows)
            return _Result(copy.deepcopy(new_rows))
        matched = [r for r in rows if all(r.get(k) == v for k, v in self.filters)]
        if self.op == "update":
            for row in matched:
                row.update(self.payload)
        result = copy.deepcopy(matched)
        if "escalation_events(*)" in self.columns:
            for row in result:
                row["escalation_events"] = [
                    copy.deepcopy(e) for e in self.store.get("escalation_events", []) if e["escalation_id"] == row["id"]
                ]
        return _Result(result)


class FakeSupabase:
    def __init__(self):
        self.store = {"profiles": [{"id": str(uuid.uuid4()), "email": "coordinator@ayurctms.demo"}]}

    def from_(self, table):
        return _Query(self.store, table)


def _login(email, password, role):
    client = TestClient(app)
    login = client.post("/api/supabase/auth/login", json={"email": email, "password": password, "role": role})
    assert login.status_code == 200
    otp = client.post("/api/supabase/auth/verify-otp", json={
        "challenge_id": login.json()["challenge_id"], "email": email, "role": role, "otp_code": "123456"
    })
    assert otp.status_code == 200
    return client


@pytest.fixture
def supabase(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(escalations, "get_supabase_admin_client", lambda: fake)
    return fake


# ==============================================================================
# TEST: A new escalation is stored in Supabase, not in process memory
# ==============================================================================
def test_escalation_is_written_to_supabase_not_memory(supabase):
    in_memory_before = len(escalations._synthetic_escalations)
    notifications_before = len(escalations._notifications)
    coordinator = _login("coordinator@ayurctms.demo", "Coord@Demo#2026", "Research Coordinator")

    created = coordinator.post("/api/escalations", json={
        "from_name": "ignored", "from_role": "ignored",
        "category": "Safety", "urgency": "Critical",
        "summary": "Persisted escalation", "details": "Stored in Supabase"
    })
    assert created.status_code == 201
    esc_id = created.json()["id"]

    saved = supabase.store["escalations"]
    assert [row["id"] for row in saved] == [esc_id]
    assert saved[0]["from_user"] == supabase.store["profiles"][0]["id"]
    assert saved[0]["from_role"] == "Research Coordinator"
    # created + PV auto-copy + EC expedited notice
    assert len(supabase.store["escalation_events"]) == 3
    assert {n["target_role"] for n in supabase.store["notifications"]} == {
        "Principal Investigator", "Admin", "PV Officer", "EC Member"
    }
    assert all(n["ref_id"] == esc_id for n in supabase.store["notifications"])
    assert len(escalations._synthetic_escalations) == in_memory_before
    assert len(escalations._notifications) == notifications_before

    listed = next(e for e in coordinator.get("/api/escalations").json() if e["id"] == esc_id)
    assert listed["from_user"] == "coordinator@ayurctms.demo"
    assert len(listed["events"]) == 3


# ==============================================================================
# TEST: Acknowledge / resolve update the Supabase row and append to its thread
# ==============================================================================
def test_escalation_status_changes_are_written_to_supabase(supabase):
    coordinator = _login("coordinator@ayurctms.demo", "Coord@Demo#2026", "Research Coordinator")
    esc_id = coordinator.post("/api/escalations", json={
        "from_name": "x", "from_role": "x", "category": "Data issue",
        "summary": "Needs follow-up", "details": "Details"
    }).json()["id"]

    pi = _login("pi@ayurctms.demo", "Pi@Demo#2026", "Principal Investigator")
    acknowledged = pi.post(f"/api/escalations/{esc_id}/acknowledge", json={"actor_name": "x", "actor_role": "x"})
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "Acknowledged"

    resolved = pi.post(f"/api/escalations/{esc_id}/resolve", json={
        "actor_name": "x", "actor_role": "x", "resolution_notes": "Fixed at source"
    })
    assert resolved.status_code == 200
    assert supabase.store["escalations"][0]["status"] == "Resolved"
    assert supabase.store["escalations"][0]["resolution_notes"] == "Fixed at source"
    assert [e["event_type"] for e in resolved.json()["events"]] == ["created", "acknowledged", "resolved"]

    missing = pi.post(f"/api/escalations/{uuid.uuid4()}/acknowledge", json={"actor_name": "x", "actor_role": "x"})
    assert missing.status_code == 404
