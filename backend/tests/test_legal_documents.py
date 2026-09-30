from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def set_session(role, email):
    token = create_access_token({
        "sub": f"demo:{email}",
        "email": email,
        "role": role,
        "full_name": f"Test {role}",
        "site_id": "SITE-HQ",
        "principal_type": "demo",
    })
    client.cookies.set("ayur_access_token", token)


def test_leadership_legal_summary_is_read_only_and_role_protected():
    client.cookies.clear()
    assert client.get("/api/legal-documents").status_code == 401

    set_session("Institution Leadership", "leader@ayurctms.demo")
    response = client.get("/api/legal-documents")
    assert response.status_code == 200
    documents = response.json()["documents"]
    assert len(documents) == 8
    assert [doc["days_remaining"] for doc in documents] == sorted(doc["days_remaining"] for doc in documents)
    assert {"title", "type", "issuing_authority", "issue_date", "expiry_date", "status", "countdown"}.issubset(documents[0])
    assert documents[0]["status"] == "Expired"
    assert documents[0]["countdown"].startswith("Expired ")
    assert all("file_name" not in doc and "signed_download_url" not in doc for doc in documents)

    set_session("Research Coordinator", "coordinator@ayurctms.demo")
    assert client.get("/api/legal-documents").status_code == 403