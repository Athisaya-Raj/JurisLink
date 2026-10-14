"""Case-invitation lifecycle: create, list, detail, accept, decline.

A case is offered to exactly one eligible lawyer at a time (a pending
invitation). On acceptance the case is assigned to that lawyer; on decline the
case is re-offered to the next eligible lawyer who has not already been invited.
Atomic ``find_one_and_update`` guards prevent simultaneous accept/decline from
corrupting invitation state.
"""
from __future__ import annotations

import datetime as dt
import random
import string
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..database import get_db
from .lawyer_matching import assign_lawyer

INVITATION_COLLECTION = "case_invitation_temp"

_ALLOWED_STATUSES = ("pending", "accepted", "declined", "cancelled")


class InvitationNotFound(RuntimeError):
    """The invitation does not exist or is not addressed to the caller."""


class InvitationStateError(RuntimeError):
    """The invitation is not in a state that allows the requested action."""


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _generate_id(prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{rand}"


def _build_invitation(case: Dict[str, Any], lawyer: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": ObjectId(),
        "invitation_id": _generate_id("INV"),
        "case_id": case.get("case_id"),
        "case_title": case.get("title"),
        "case_summary": (case.get("description") or "")[:240],
        "lawyer_id": lawyer.get("lawyer_id"),
        "lawyer_doc_id": str(lawyer.get("_id")),
        "lawyer_name": lawyer.get("name"),
        "user_id": case.get("user_id"),
        "predicted_category_id": case.get("predicted_category_id"),
        "predicted_category_name": case.get("predicted_category_name"),
        "status": "pending",
        "created_at": _now_iso(),
        "responded_at": None,
        "decline_reason": None,
    }


def _already_invited_lawyer_ids(case_id: str) -> set:
    db = get_db()
    return {
        inv.get("lawyer_id")
        for inv in db[INVITATION_COLLECTION].find({"case_id": case_id})
        if inv.get("lawyer_id")
    }


def create_invitation(
    case: Dict[str, Any], lawyer: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Create a pending invitation for a case.

    If ``lawyer`` is omitted, the best eligible lawyer (excluding any already
    invited) is selected deterministically. Returns ``None`` when no eligible
    lawyer remains.
    """
    db = get_db()
    if lawyer is None:
        category_id = case.get("predicted_category_id")
        if not category_id:
            return None
        exclude = _already_invited_lawyer_ids(case["case_id"])
        lawyer = assign_lawyer(category_id, exclude_lawyer_ids=exclude)
        if lawyer is None:
            return None

    doc = _build_invitation(case, lawyer)
    try:
        db[INVITATION_COLLECTION].insert_one(doc)
    except DuplicateKeyError:
        # Lost a race — return the existing pending invitation for this case.
        return db[INVITATION_COLLECTION].find_one(
            {"case_id": case["case_id"], "status": "pending"}
        )
    return doc


def list_invitations(lawyer_id: str) -> List[Dict[str, Any]]:
    return list(
        get_db()[INVITATION_COLLECTION]
        .find({"lawyer_id": lawyer_id})
        .sort("created_at", -1)
    )


def invitation_counts(lawyer_id: str) -> Dict[str, int]:
    db = get_db()
    counts = {"pending": 0, "accepted": 0, "declined": 0, "cancelled": 0, "total": 0}
    for inv in db[INVITATION_COLLECTION].find({"lawyer_id": lawyer_id}, {"status": 1}):
        counts["total"] += 1
        if inv.get("status") in counts:
            counts[inv["status"]] += 1
    return counts


def get_invitation_for_lawyer(invitation_id: str, lawyer_id: str) -> Optional[Dict[str, Any]]:
    """Return an invitation only if it is addressed to ``lawyer_id`` (else None)."""
    return get_db()[INVITATION_COLLECTION].find_one(
        {"invitation_id": invitation_id, "lawyer_id": lawyer_id}
    )


def get_latest_invitation(case_id: str) -> Optional[Dict[str, Any]]:
    return get_db()[INVITATION_COLLECTION].find_one(
        {"case_id": case_id}, sort=[("created_at", -1)]
    )


def _require_pending(invitation_id: str, lawyer_id: str) -> Dict[str, Any]:
    db = get_db()
    invitation = db[INVITATION_COLLECTION].find_one({"invitation_id": invitation_id})
    if invitation is None or invitation.get("lawyer_id") != lawyer_id:
        raise InvitationNotFound("Invitation not found.")
    if invitation.get("status") != "pending":
        raise InvitationStateError(
            f"This invitation has already been {invitation.get('status')}."
        )
    return invitation


def accept_invitation(invitation_id: str, lawyer_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Accept a pending invitation and assign the case to the lawyer (atomic)."""
    db = get_db()
    invitation = _require_pending(invitation_id, lawyer_id)

    now = _now_iso()
    updated = db[INVITATION_COLLECTION].find_one_and_update(
        {"_id": invitation["_id"], "status": "pending", "lawyer_id": lawyer_id},
        {"$set": {"status": "accepted", "responded_at": now}},
        return_document=True,
    )
    if updated is None:
        raise InvitationStateError("This invitation was already responded to.")

    db["case_temp"].update_one(
        {"case_id": invitation.get("case_id")},
        {
            "$set": {
                "status": "assigned",
                "assigned_lawyer_id": invitation.get("lawyer_id"),
                "assigned_lawyer_doc_id": invitation.get("lawyer_doc_id"),
                "assigned_lawyer_name": invitation.get("lawyer_name"),
                "accepted_at": now,
                "updated_at": now,
            }
        },
    )
    case = db["case_temp"].find_one({"case_id": invitation.get("case_id")})
    return updated, case


def decline_invitation(
    invitation_id: str, lawyer_id: str, reason: Optional[str] = None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Decline a pending invitation and re-offer the case if possible.

    Returns ``(updated_invitation, next_lawyer_or_None)``.
    """
    db = get_db()
    invitation = _require_pending(invitation_id, lawyer_id)

    now = _now_iso()
    updated = db[INVITATION_COLLECTION].find_one_and_update(
        {"_id": invitation["_id"], "status": "pending", "lawyer_id": lawyer_id},
        {
            "$set": {
                "status": "declined",
                "responded_at": now,
                "decline_reason": (reason or "").strip() or None,
            }
        },
        return_document=True,
    )
    if updated is None:
        raise InvitationStateError("This invitation was already responded to.")

    # Re-offer to the next eligible lawyer (skipping already-invited ones).
    next_lawyer = None
    case = db["case_temp"].find_one({"case_id": invitation.get("case_id")})
    if case is not None:
        new_inv = create_invitation(case)
        if new_inv:
            next_lawyer = db["lawyer_temp"].find_one({"lawyer_id": new_inv.get("lawyer_id")})

    return updated, next_lawyer
