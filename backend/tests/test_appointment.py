"""Appointment booking, collision prevention, and isolation tests.

Bookings are only possible after a lawyer accepts the case, so each test
submits a case, accepts the invitation, then exercises the slot workflow.
"""
from __future__ import annotations

from app.database import get_db

from .conftest import accept_invitation, headers, submit_case, token_for

RENTAL_DESC = (
    "My landlord refuses to return my rental deposit even though I vacated "
    "the apartment and completed the agreement."
)


def _submit_and_accept(client, user_token, tracker):
    """Submit a PRO02 case and accept its invitation; return (case_id, lawyer_id, lawyer_tok)."""
    resp = submit_case(client, user_token, "Tenancy issue", RENTAL_DESC)
    body = resp.json()
    case_id = body["case"]["case_id"]
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]
    tracker(case_id)

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    acc = accept_invitation(client, lawyer_tok, invitation_id)
    assert acc.status_code == 200
    return case_id, lawyer_id, lawyer_tok


def _get_slots(client, user_token, case_id):
    return client.get(f"/cases/{case_id}/slots", headers=headers(user_token))


def test_available_slots_retrievable(client, user_token, tracker):
    case_id, _, _ = _submit_and_accept(client, user_token, tracker)
    resp = _get_slots(client, user_token, case_id)
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) >= 1
    assert resp.json()["slots"][0]["status"] == "available"


def test_cannot_book_before_acceptance(client, user_token, tracker):
    resp = submit_case(client, user_token, "Tenancy issue", RENTAL_DESC)
    case_id = resp.json()["case"]["case_id"]
    tracker(case_id)
    assert _get_slots(client, user_token, case_id).status_code == 409


def test_book_appointment_persists(client, user_token, tracker):
    case_id, lawyer_id, _ = _submit_and_accept(client, user_token, tracker)
    slot_id = _get_slots(client, user_token, case_id).json()["slots"][0]["slot_id"]

    resp = client.post(
        "/appointments",
        json={"case_id": case_id, "slot_id": slot_id},
        headers=headers(user_token),
    )
    assert resp.status_code == 200, resp.text
    appt = resp.json()["appointment"]
    assert appt["appointment_id"].startswith("APPT-")
    assert appt["status"] == "booked"
    assert appt["slot_id"] == slot_id
    assert appt["lawyer_id"] == lawyer_id

    stored = get_db()["appointment_temp"].find_one({"appointment_id": appt["appointment_id"]})
    assert stored is not None

    mine = client.get("/appointments/mine", headers=headers(user_token))
    assert any(a["appointment_id"] == appt["appointment_id"] for a in mine.json()["appointments"])


def test_double_booking_same_slot_rejected(client, user_token, tracker):
    case_id, _, _ = _submit_and_accept(client, user_token, tracker)
    slot_id = _get_slots(client, user_token, case_id).json()["slots"][0]["slot_id"]

    first = client.post(
        "/appointments", json={"case_id": case_id, "slot_id": slot_id}, headers=headers(user_token)
    )
    assert first.status_code == 200

    second = client.post(
        "/appointments", json={"case_id": case_id, "slot_id": slot_id}, headers=headers(user_token)
    )
    assert second.status_code == 409


def test_other_user_cannot_book_someone_elses_case(client, user_token, tracker):
    case_id, _, _ = _submit_and_accept(client, user_token, tracker)
    slot_id = _get_slots(client, user_token, case_id).json()["slots"][0]["slot_id"]

    other_tok = token_for("user", user_id="someone-else")
    resp = client.post(
        "/appointments",
        json={"case_id": case_id, "slot_id": slot_id},
        headers=headers(other_tok),
    )
    assert resp.status_code == 404


def test_lawyer_sees_appointment(client, user_token, tracker):
    case_id, lawyer_id, lawyer_tok = _submit_and_accept(client, user_token, tracker)
    slot_id = _get_slots(client, user_token, case_id).json()["slots"][0]["slot_id"]
    appt = client.post(
        "/appointments", json={"case_id": case_id, "slot_id": slot_id}, headers=headers(user_token)
    ).json()["appointment"]

    resp = client.get("/appointments/for-me", headers=headers(lawyer_tok))
    assert resp.status_code == 200
    assert any(a["appointment_id"] == appt["appointment_id"] for a in resp.json()["appointments"])


def test_cancel_frees_slot(client, user_token, tracker):
    case_id, _, _ = _submit_and_accept(client, user_token, tracker)
    slot_id = _get_slots(client, user_token, case_id).json()["slots"][0]["slot_id"]
    appt = client.post(
        "/appointments", json={"case_id": case_id, "slot_id": slot_id}, headers=headers(user_token)
    ).json()["appointment"]

    cancel = client.patch(
        f"/appointments/{appt['appointment_id']}/status",
        json={"status": "cancelled"},
        headers=headers(user_token),
    )
    assert cancel.status_code == 200

    slots_after = _get_slots(client, user_token, case_id).json()["slots"]
    assert any(s["slot_id"] == slot_id and s["status"] == "available" for s in slots_after)
