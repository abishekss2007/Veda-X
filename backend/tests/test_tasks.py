from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.tasks import _tasks
from app.core.security import create_access_token
from app.db.models import AuditLogEntry
from app.main import app
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def set_session(role, email, site="SITE-01"):
    token = create_access_token({
        "sub": f"demo:{email}",
        "email": email,
        "role": role,
        "full_name": f"Test {role}",
        "site_id": site,
        "principal_type": "demo",
    })
    client.cookies.set("ayur_access_token", token)


@pytest.fixture(autouse=True)
def clear_tasks_and_cookie():
    _tasks.clear()
    client.cookies.clear()
    yield
    _tasks.clear()
    client.cookies.clear()


def test_tasks_enforce_admin_and_assignee_permissions_and_audit():
    task_data = {
        "assignee": "role:Research Coordinator",
        "title": "Review visit records",
        "description": "Check visit windows for completeness.",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "priority": "High",
        "due_date": (date.today() - timedelta(days=2)).isoformat(),
    }

    set_session("Research Coordinator", "coordinator@ayurctms.demo")
    coordinator_assignees = client.get("/api/tasks/assignees")
    assert coordinator_assignees.status_code == 200
    assert "Admin" not in coordinator_assignees.json()["roles"]
    assert "Principal Investigator" not in coordinator_assignees.json()["roles"]
    assert all(user["role"] not in {"Admin", "Principal Investigator"} for user in coordinator_assignees.json()["users"])

    coordinator_task = client.post("/api/tasks", json={**task_data, "assignee": "role:Monitor"})
    assert coordinator_task.status_code == 201
    assert coordinator_task.json()["created_by"] == "coordinator@ayurctms.demo"
    assert client.post("/api/tasks", json={**task_data, "assignee": "role:Admin"}).status_code == 403
    assert client.post("/api/tasks", json={**task_data, "assignee": "role:Principal Investigator"}).status_code == 403
    assert client.post("/api/tasks", json={**task_data, "assignee": "user:admin@ayurctms.in"}).status_code == 403
    assigned_by_coordinator = client.get("/api/tasks/assigned-by-me")
    assert assigned_by_coordinator.status_code == 200
    assert [task["id"] for task in assigned_by_coordinator.json()] == [coordinator_task.json()["id"]]
    assert client.get("/api/tasks/assigned-by-me").status_code == 200

    set_session("Admin", "admin@ayurctms.demo", "SITE-HQ")
    assignees = client.get("/api/tasks/assignees")
    assert assignees.status_code == 200
    assert "Research Coordinator" in assignees.json()["roles"]
    assert "Admin" in assignees.json()["roles"]
    assert "Principal Investigator" in assignees.json()["roles"]
    created = client.post("/api/tasks", json=task_data)
    assert created.status_code == 201
    role_task = created.json()
    assert role_task["status"] == "Assigned"
    assert role_task["overdue"] is True
    assert "2 day(s) ago" in role_task["overdue_reason"]

    user_task_payload = {**task_data, "assignee": "user:coordinator@ayurctms.in", "due_date": date.today().isoformat()}
    user_task = client.post("/api/tasks", json=user_task_payload)
    assert user_task.status_code == 201

    set_session("Research Coordinator", "coordinator@ayurctms.in")
    own_tasks = client.get("/api/tasks").json()
    assert {task["id"] for task in own_tasks} == {role_task["id"], user_task.json()["id"]}
    updated = client.patch(f"/api/tasks/{user_task.json()['id']}", json={"status": "In progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "In progress"
    forbidden_edit = client.patch(f"/api/tasks/{user_task.json()['id']}", json={"title": "Tamper"})
    assert forbidden_edit.status_code == 403

    set_session("Research Coordinator", "another.coordinator@ayurctms.in")
    other_tasks = client.get("/api/tasks").json()
    assert [task["id"] for task in other_tasks] == [role_task["id"]]
    assert client.patch(f"/api/tasks/{user_task.json()['id']}", json={"status": "Done"}).status_code == 403

    set_session("Admin", "admin@ayurctms.demo", "SITE-HQ")
    edited = client.patch(f"/api/tasks/{role_task['id']}", json={"title": "Updated review task"})
    assert edited.status_code == 200
    assert edited.json()["title"] == "Updated review task"

    db = TestingSessionLocal()
    try:
        actions = db.query(AuditLogEntry).filter(AuditLogEntry.action.in_(["TASK_ASSIGNED", "TASK_UPDATED"])).count()
        assert actions >= 3
    finally:
        db.close()