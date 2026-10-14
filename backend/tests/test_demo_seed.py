"""Idempotent demo-seeding tests (use a test-only seed id to avoid touching real seed)."""
from __future__ import annotations

from app.config import settings
from app.database import get_db
from app.services import demo_seed

from .conftest import headers, token_for


def test_seed_demo_is_idempotent(client, monkeypatch, tracker):
    seed_case_id = "TEST-SEED-001"
    monkeypatch.setattr(settings, "DEMO_SEED_CASE_ID", seed_case_id)

    first = demo_seed.seed_demo()
    assert first["case_created"] is True
    assert first["invitation_created"] is True
    assert first["lawyer_id"] == settings.DEMO_LAWYER_ID
    assert first["invitation_status"] == "pending"
    tracker(seed_case_id)

    second = demo_seed.seed_demo()
    assert second["case_created"] is False
    assert second["invitation_created"] is False

    # Exactly one case and one pending invitation persist in MongoDB.
    assert get_db()["case_temp"].count_documents({"case_id": seed_case_id}) == 1
    assert (
        get_db()["case_invitation_temp"].count_documents(
            {"case_id": seed_case_id, "lawyer_id": settings.DEMO_LAWYER_ID}
        )
        == 1
    )


def test_seed_demo_endpoint(client, monkeypatch, tracker):
    monkeypatch.setattr(settings, "DEMO_SEED_CASE_ID", "TEST-SEED-002")
    resp = client.post("/admin/seed-demo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == "TEST-SEED-002"
    assert body["lawyer_id"] == settings.DEMO_LAWYER_ID
    tracker("TEST-SEED-002")


def test_seed_demo_endpoint_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DEMO_ENDPOINTS", False)
    resp = client.post("/admin/seed-demo")
    assert resp.status_code == 403


def test_demo_lawyer_sees_seeded_invitation(client, monkeypatch, tracker):
    seed_case_id = "TEST-SEED-003"
    monkeypatch.setattr(settings, "DEMO_SEED_CASE_ID", seed_case_id)
    demo_seed.seed_demo()
    tracker(seed_case_id)

    lawyer_tok = token_for("lawyer", lawyer_id=settings.DEMO_LAWYER_ID)
    resp = client.get("/invitations", headers=headers(lawyer_tok))
    assert resp.status_code == 200
    assert any(i["case_id"] == seed_case_id for i in resp.json()["invitations"])
