"""Authentication and authorization tests."""
from __future__ import annotations

from .conftest import headers


def test_user_login_succeeds(client):
    resp = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "user"


def test_lawyer_login_succeeds(client):
    resp = client.post("/auth/login", json={"username": "lawyer", "password": "lawyer"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["role"] == "lawyer"
    assert body["user"]["lawyer_id"]
    # The demo lawyer maps to a single, persistent lawyer record (DEMO_LAWYER_ID).
    from app.config import settings

    assert body["user"]["lawyer_id"] == settings.DEMO_LAWYER_ID


def test_incorrect_password_rejected(client):
    resp = client.post("/auth/login", json={"username": "user", "password": "wrong"})
    assert resp.status_code == 401


def test_unknown_username_rejected(client):
    resp = client.post("/auth/login", json={"username": "nobody", "password": "user"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/cases/mine")
    assert resp.status_code == 401


def test_invalid_token_rejected(client):
    resp = client.get("/cases/mine", headers=headers("not-a-real-token"))
    assert resp.status_code == 401


def test_role_enforcement_user_vs_lawyer(client, user_token, lawyer_token):
    # A user cannot access lawyer-only endpoints.
    assert client.get("/cases/assigned-to-me", headers=headers(user_token)).status_code == 403
    assert client.get("/dashboard/lawyer", headers=headers(user_token)).status_code == 403
    # A lawyer cannot access user-only endpoints.
    assert client.get("/cases/mine", headers=headers(lawyer_token)).status_code == 403
    assert client.get("/dashboard/user", headers=headers(lawyer_token)).status_code == 403


def test_me_endpoint(client, user_token, lawyer_token):
    me = client.get("/auth/me", headers=headers(user_token))
    assert me.status_code == 200
    assert me.json()["role"] == "user"
    me_lawyer = client.get("/auth/me", headers=headers(lawyer_token))
    assert me_lawyer.status_code == 200
    assert me_lawyer.json()["role"] == "lawyer"
