"""
===================================================================================
FILE: tests/test_api.py
ROLE: Automated Integration & API Route Testing Suite (With Auth & RBAC Verification)
===================================================================================
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app
import auth
import config


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def admin_headers(client):
    """Fixture returning Bearer token headers for Admin user."""
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client):
    """Fixture returning Bearer token headers for Manager user."""
    res = client.post("/api/auth/login", json={"username": "manager", "password": "manager123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def analyst_headers(client):
    """Fixture returning Bearer token headers for Analyst user."""
    res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_login_success(client):
    """Test login endpoint with valid credentials for admin, manager, and analyst."""
    for username, pwd, expected_role in [
        ("admin", "admin123", auth.ROLE_ADMIN),
        ("manager", "manager123", auth.ROLE_MANAGER),
        ("analyst", "analyst123", auth.ROLE_ANALYST)
    ]:
        res = client.post("/api/auth/login", json={"username": username, "password": pwd})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "access_token" in data
        assert data["user"]["role"] == expected_role


def test_auth_login_failure(client):
    """Test login endpoint rejects invalid passwords and non-existent users."""
    res1 = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res1.status_code == 401

    res2 = client.post("/api/auth/login", json={"username": "nonexistent_user", "password": "password"})
    assert res2.status_code == 401


def test_auth_me_profile(client, admin_headers):
    """Test /api/auth/me returns profile details for authenticated user."""
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == auth.ROLE_ADMIN


def test_system_status(client, admin_headers):
    """Test /api/status endpoint returns online status and correct model configs."""
    response = client.get("/api/status", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["company_id"] == config.DEFAULT_COMPANY_ID
    assert data["embedding_model"] == config.EMBEDDING_MODEL_NAME
    assert data["llm_model"] == config.LLM_MODEL
    assert "total_chunks" in data
    assert "user" in data


def test_list_companies(client, admin_headers):
    """Test /api/companies endpoint lists active workspaces for Admin."""
    response = client.get("/api/companies", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert len(data["companies"]) >= 1
    company_ids = [c["id"] for c in data["companies"]]
    assert config.DEFAULT_COMPANY_ID in company_ids


def test_rbac_workspace_creation_permissions(client, analyst_headers, admin_headers):
    """Test RBAC enforcement: Analyst role blocked from creating workspaces, Admin allowed."""
    test_company_name = "RBAC Test Bank"
    clean_id = config.sanitize_company_id(test_company_name)

    # 1. Analyst attempt to create workspace -> 403 Forbidden
    analyst_res = client.post("/api/companies", json={"name": test_company_name}, headers=analyst_headers)
    assert analyst_res.status_code == 403

    # 2. Admin create workspace -> 200 OK
    admin_create_res = client.post("/api/companies", json={"name": test_company_name}, headers=admin_headers)
    assert admin_create_res.status_code == 200
    assert admin_create_res.json()["company"]["id"] == clean_id

    # 3. Clean up: Admin delete workspace -> 200 OK
    admin_del_res = client.delete(f"/api/companies/{clean_id}", headers=admin_headers)
    assert admin_del_res.status_code == 200


def test_vector_search(client, analyst_headers):
    """Test raw vector Cosine similarity search endpoint with Analyst role."""
    response = client.post("/api/search", json={
        "query": "Commercial real estate loan-to-value limits",
        "company_id": config.DEFAULT_COMPANY_ID,
        "top_k": 4,
        "min_score": 0.0
    }, headers=analyst_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Commercial real estate loan-to-value limits"
    assert "results" in data
    assert isinstance(data["results"], list)


def test_chat_endpoint(client, analyst_headers):
    """Test standard RAG chat endpoint with multi-turn history support."""
    response = client.post("/api/chat", json={
        "query": "What are the debt service coverage ratio (DSCR) rules?",
        "company_id": config.DEFAULT_COMPANY_ID,
        "top_k": 3,
        "min_score": 0.15,
        "history": [
            {"role": "user", "content": "Hi, I need loan policy information."},
            {"role": "assistant", "content": "Hello! I am your FDIC loan policy assistant."}
        ]
    }, headers=analyst_headers)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "timing" in data


def test_chat_stream_endpoint(client, analyst_headers):
    """Test Server-Sent Events (SSE) chat streaming endpoint."""
    response = client.post("/api/chat/stream", json={
        "query": "What are the appraisal requirements for commercial loans over $500,000?",
        "company_id": config.DEFAULT_COMPANY_ID,
        "top_k": 2,
        "min_score": 0.10
    }, headers=analyst_headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    content = response.text
    assert "data: " in content
    assert '"type": "sources"' in content or '"type": "token"' in content
