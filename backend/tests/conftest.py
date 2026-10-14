"""Shared pytest fixtures, helpers, and data cleanup."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import connect, ensure_indexes, get_db
from app.main import app
from app.utils.security import create_access_token


@pytest.fixture(scope="session")
def client():
    """A TestClient whose lifespan connects to MongoDB and warms the model."""
    connect()
    ensure_indexes()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_token(client):
    resp = client.post("/auth/login", json={"username": "user", "password": "user"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def lawyer_token(client):
    resp = client.post("/auth/login", json={"username": "lawyer", "password": "lawyer"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def token_for(role: str, **claims) -> str:
    """Mint a token for an arbitrary principal (used for isolation tests)."""
    base = {"sub": claims.get("sub", f"{role}-test"), "role": role}
    base.update(claims)
    return create_access_token(base)


def submit_case(client, token, title, description, client_request_id=None):
    payload = {"title": title, "description": description}
    if client_request_id:
        payload["client_request_id"] = client_request_id
    return client.post("/cases/demo/submit-and-classify", json=payload, headers=headers(token))


def accept_invitation(client, token, invitation_id):
    return client.post(f"/invitations/{invitation_id}/accept", headers=headers(token))


def decline_invitation(client, token, invitation_id, reason=None):
    payload = {"reason": reason} if reason else {}
    return client.post(f"/invitations/{invitation_id}/decline", json=payload, headers=headers(token))


@pytest.fixture
def tracker():
    """Tracks created case_ids and cleans up their cases, invitations, appointments, and progress notes."""
    created: list = []

    def track(case_id):
        created.append(case_id)

    yield track

    db = get_db()
    for case_id in created:
        if not case_id:
            continue
        for appt in list(db["appointment_temp"].find({"case_id": case_id})):
            db["lawyer_temp"].update_one(
                {"lawyer_id": appt.get("lawyer_id"), "available_slots.slot_id": appt.get("slot_id")},
                {"$set": {"available_slots.$.status": "available"}},
            )
            db["appointment_temp"].delete_one({"_id": appt["_id"]})
        db["case_invitation_temp"].delete_many({"case_id": case_id})
        db["progress_note_temp"].delete_many({"case_id": case_id})
        db["case_temp"].delete_one({"case_id": case_id})
