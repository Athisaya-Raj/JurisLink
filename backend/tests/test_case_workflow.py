"""End-to-end case submission / classification / invitation / isolation tests."""
from __future__ import annotations

import uuid

from app.database import get_db

from .conftest import accept_invitation, headers, submit_case, token_for

FAMILY_DESC = (
    "My spouse and I have a serious disagreement about our marital rights and "
    "responsibilities, and I need legal guidance."
)
RENTAL_DESC = (
    "My landlord refuses to return my rental deposit even though I vacated "
    "the apartment and completed the agreement."
)


def test_submit_case_classifies_and_creates_invitation(client, user_token, tracker):
    rid = f"req-{uuid.uuid4()}"
    resp = submit_case(client, user_token, "Rental deposit dispute", RENTAL_DESC, client_request_id=rid)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    case = body["case"]
    assert case["case_id"].startswith("CASE-")
    assert case["predicted_category_id"] == "PRO02"
    assert case["status"] == "pending_assignment"
    assert case.get("assigned_lawyer_id") is None
    assert body["invitation"] is not None
    assert body["invitation"]["status"] == "pending"
    assert body["lawyer"] is not None
    assert body["lawyer"]["lawyer_id"].startswith("LAW-PRO02-")
    tracker(case["case_id"])

    stored = get_db()["case_temp"].find_one({"case_id": case["case_id"]})
    assert stored is not None
    inv = get_db()["case_invitation_temp"].find_one({"case_id": case["case_id"]})
    assert inv is not None and inv["status"] == "pending"


def test_duplicate_submission_is_idempotent(client, user_token, tracker):
    rid = f"req-{uuid.uuid4()}"
    first = submit_case(client, user_token, "Family dispute", FAMILY_DESC, client_request_id=rid)
    assert first.status_code == 200
    case_id = first.json()["case"]["case_id"]
    tracker(case_id)

    second = submit_case(client, user_token, "Family dispute", FAMILY_DESC, client_request_id=rid)
    assert second.status_code == 200
    assert second.json()["disposition"] == "duplicate"
    assert second.json()["case"]["case_id"] == case_id
    assert get_db()["case_temp"].count_documents({"client_request_id": rid}) == 1


def test_case_appears_on_user_dashboard(client, user_token, tracker):
    resp = submit_case(
        client, user_token, "Child custody question",
        "I need legal guidance about a child custody dispute and parenting arrangements.",
    )
    assert resp.status_code == 200
    case_id = resp.json()["case"]["case_id"]
    tracker(case_id)
    mine = client.get("/cases/mine", headers=headers(user_token))
    assert any(c["case_id"] == case_id for c in mine.json()["cases"])


def test_case_appears_on_lawyer_dashboard_after_accept(client, user_token, tracker):
    resp = submit_case(client, user_token, "Marriage dispute", FAMILY_DESC)
    body = resp.json()
    case_id = body["case"]["case_id"]
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]
    tracker(case_id)

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    acc = accept_invitation(client, lawyer_tok, invitation_id)
    assert acc.status_code == 200

    assigned = client.get("/cases/assigned-to-me", headers=headers(lawyer_tok))
    assert any(c["case_id"] == case_id for c in assigned.json()["cases"])


def test_other_user_cannot_retrieve_case(client, user_token, tracker):
    resp = submit_case(
        client, user_token, "Contract dispute",
        "The other party breached our written contract and I want to pursue recovery.",
    )
    case_id = resp.json()["case"]["case_id"]
    tracker(case_id)
    other_tok = token_for("user", user_id="someone-else")
    assert client.get(f"/cases/{case_id}", headers=headers(other_tok)).status_code == 404


def test_unrelated_lawyer_cannot_retrieve_case(client, user_token, tracker):
    resp = submit_case(
        client, user_token, "Property boundary dispute",
        "My neighbour and I disagree about the legal boundary of our land and ownership documents.",
    )
    case_id = resp.json()["case"]["case_id"]
    tracker(case_id)
    unrelated_tok = token_for("lawyer", lawyer_id="LAW-FAM01-01")
    assert client.get(f"/cases/{case_id}", headers=headers(unrelated_tok)).status_code == 404


def test_lawyer_can_update_own_case_status_after_accept(client, user_token, tracker):
    resp = submit_case(
        client, user_token, "Alimony question",
        "I need help understanding maintenance and alimony obligations after separation.",
    )
    body = resp.json()
    case_id = body["case"]["case_id"]
    invitation_id = body["invitation"]["invitation_id"]
    lawyer_id = body["lawyer"]["lawyer_id"]
    tracker(case_id)

    lawyer_tok = token_for("lawyer", lawyer_id=lawyer_id)
    accept_invitation(client, lawyer_tok, invitation_id)

    patch = client.patch(
        f"/cases/{case_id}/status", json={"status": "in_review"}, headers=headers(lawyer_tok)
    )
    assert patch.status_code == 200
    assert patch.json()["case"]["status"] == "in_review"


def test_lawyer_cannot_update_unrelated_case(client, user_token, tracker):
    resp = submit_case(
        client, user_token, "Tax query",
        "I have a dispute with the tax department about my assessment and want advice.",
    )
    case_id = resp.json()["case"]["case_id"]
    tracker(case_id)
    unrelated_tok = token_for("lawyer", lawyer_id="LAW-FAM01-01")
    patch = client.patch(
        f"/cases/{case_id}/status", json={"status": "in_review"}, headers=headers(unrelated_tok)
    )
    assert patch.status_code == 403


def test_short_description_rejected(client, user_token):
    resp = submit_case(client, user_token, "Tiny case", "help")
    assert resp.status_code == 422
