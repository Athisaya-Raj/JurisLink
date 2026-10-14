"""Case-invitation lifecycle tests (accept/decline, isolation, reassignment)."""
from __future__ import annotations

from app.database import get_db

from .conftest import accept_invitation, decline_invitation, headers, submit_case, token_for

FAMILY_DESC = (
    "My spouse and I have a serious disagreement about our marital rights and "
    "responsibilities, and I need legal guidance."
)


def _submit_family(client, user_token, tracker):
    resp = submit_case(client, user_token, "Marriage dispute", FAMILY_DESC)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    tracker(body["case"]["case_id"])
    return body


def test_submit_creates_pending_invitation_for_eligible_lawyer(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    assert body["case"]["status"] == "pending_assignment"
    assert body["invitation"]["status"] == "pending"
    assert body["lawyer"]["lawyer_id"].startswith("LAW-FAM01-")
    assert "FAM01" in body["lawyer"]["specializations"]


def test_lawyer_can_accept_and_case_becomes_assigned(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    case_id = body["case"]["case_id"]
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    acc = accept_invitation(client, lawyer_tok, invitation_id)
    assert acc.status_code == 200
    assert acc.json()["invitation"]["status"] == "accepted"
    assert acc.json()["case"]["status"] == "assigned"
    assert acc.json()["case"]["assigned_lawyer_id"] == lawyer_id

    # The user sees the updated status.
    detail = client.get(f"/cases/{case_id}", headers=headers(user_token))
    assert detail.json()["case"]["status"] == "assigned"
    assert detail.json()["case"]["assigned_lawyer_id"] == lawyer_id


def test_different_lawyer_cannot_accept(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    invitation_id = body["invitation"]["invitation_id"]
    other_tok = token_for("lawyer", lawyer_id="LAW-FAM02-01")
    resp = accept_invitation(client, other_tok, invitation_id)
    assert resp.status_code == 404


def test_accept_then_accept_again_conflicts(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]
    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)

    assert accept_invitation(client, lawyer_tok, invitation_id).status_code == 200
    second = accept_invitation(client, lawyer_tok, invitation_id)
    assert second.status_code == 409


def test_accept_then_decline_conflicts(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]
    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)

    assert accept_invitation(client, lawyer_tok, invitation_id).status_code == 200
    assert decline_invitation(client, lawyer_tok, invitation_id).status_code == 409


def test_decline_reassigns_to_next_eligible_lawyer(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    case_id = body["case"]["case_id"]
    invitation_id = body["invitation"]["invitation_id"]
    first_lawyer_id = body["lawyer"]["lawyer_id"]

    lawyer_tok = token_for("lawyer", lawyer_id=first_lawyer_id)
    resp = decline_invitation(client, lawyer_tok, invitation_id, reason="Conflict of interest")
    assert resp.status_code == 200
    assert resp.json()["invitation"]["status"] == "declined"
    assert resp.json()["invitation"]["decline_reason"] == "Conflict of interest"
    assert resp.json()["reassigned"] is True
    next_lawyer_id = resp.json()["next_lawyer"]["lawyer_id"]
    assert next_lawyer_id != first_lawyer_id

    # The case remains pending and a fresh invitation now targets the next lawyer.
    assert get_db()["case_temp"].find_one({"case_id": case_id})["status"] == "pending_assignment"
    active = get_db()["case_invitation_temp"].find_one({"case_id": case_id, "status": "pending"})
    assert active is not None
    assert active["lawyer_id"] == next_lawyer_id


def test_lawyer_can_list_own_invitations(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    lawyer_id = body["lawyer"]["lawyer_id"]
    invitation_id = body["invitation"]["invitation_id"]

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    resp = client.get("/invitations", headers=headers(lawyer_tok))
    assert resp.status_code == 200
    assert any(i["invitation_id"] == invitation_id for i in resp.json()["invitations"])
    assert resp.json()["counts"]["pending"] >= 1


def test_invitation_detail_includes_case(client, user_token, tracker):
    body = _submit_family(client, user_token, tracker)
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    resp = client.get(f"/invitations/{invitation_id}", headers=headers(lawyer_tok))
    assert resp.status_code == 200
    assert resp.json()["case"]["title"] == "Marriage dispute"
    assert resp.json()["case"]["predicted_category_id"] == "FAM01"
