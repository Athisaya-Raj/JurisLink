"""Case submission, classification-driven assignment, and persistence."""
from __future__ import annotations

import datetime as dt
import logging
import random
import string
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..database import get_db
from . import invitation_service
from .classification import ClassificationError, predict

logger = logging.getLogger("jurislink.case_service")

_ALLOWED_CASE_STATUSES = ["pending_assignment", "assigned", "in_review", "resolved", "closed"]


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _generate_id(prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{rand}"


def submit_case(payload: Dict[str, Any], user_id: str) -> Tuple[Dict[str, Any], str]:
    """Validate, classify, assign, and persist a new case.

    Returns ``(case_doc, disposition)`` where disposition is ``"created"`` or
    ``"duplicate"`` (an identical ``client_request_id`` was already processed).
    """
    db = get_db()

    # Idempotency: an explicit client_request_id lets a retry return the
    # already-persisted case instead of creating a duplicate.
    client_request_id = (payload.get("client_request_id") or "").strip() or None
    if client_request_id:
        existing = db["case_temp"].find_one({"client_request_id": client_request_id})
        if existing:
            return existing, "duplicate"

    description = (payload["description"] or "").strip()
    title = (payload["title"] or "").strip()
    if not title:
        raise ValueError("Case title is required.")
    if not description:
        raise ValueError("Case description is required.")

    prediction = predict(description)
    category_id = prediction["category_id"]

    doc_id = ObjectId()
    case_id = _generate_id("CASE")

    doc: Dict[str, Any] = {
        "_id": doc_id,
        "case_id": case_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "predicted_category_id": category_id,
        "predicted_category_name": prediction["category_name"],
        "prediction_confidence": prediction["confidence"],
        "prediction_explanation": prediction["explanation"],
        "prediction_review_recommended": prediction["review_recommended"],
        "review_flagged": prediction["review_recommended"],
        # A case is created unassigned; it becomes "assigned" only after an
        # eligible lawyer accepts the invitation.
        "status": "pending_assignment",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if payload.get("supporting_info"):
        doc["supporting_info"] = payload["supporting_info"].strip()
    if payload.get("preferred_date"):
        doc["preferred_date"] = payload["preferred_date"].strip()
    if client_request_id:
        doc["client_request_id"] = client_request_id

    try:
        db["case_temp"].insert_one(doc)
    except DuplicateKeyError:
        # Lost a race on the idempotency key — return the winner.
        if client_request_id:
            existing = db["case_temp"].find_one({"client_request_id": client_request_id})
            if existing:
                return existing, "duplicate"
        raise

    # Offer the case to the best eligible lawyer (creates a pending invitation).
    # Best-effort: when no lawyer is eligible the case simply stays pending.
    # When classification is uncertain, keep the case pending for manual review
    # rather than routing it to a lawyer who may not be relevant.
    if not prediction["review_recommended"]:
        try:
            invitation_service.create_invitation(doc)
        except Exception:  # noqa: BLE001 - never lose an already-persisted case
            logger.exception("Could not create invitation for case %s", case_id)

    return doc, "created"


def get_case_for_user(case_id: str, auth) -> Optional[Dict[str, Any]]:
    """Fetch a case if ``auth`` owns it (user) or is its assigned lawyer."""
    db = get_db()
    doc = db["case_temp"].find_one({"case_id": case_id})
    if doc is None:
        return None
    if auth.role == "user":
        if doc.get("user_id") != auth.user_id:
            return None
    elif auth.role == "lawyer":
        if doc.get("assigned_lawyer_id") != auth.lawyer_id:
            return None
    else:
        return None
    return doc


def update_case_status(case_id: str, new_status: str, lawyer_id: str) -> Optional[Dict[str, Any]]:
    """Lawyer updates the status of one of their own assigned cases."""
    new_status = (new_status or "").strip().lower()
    if new_status not in _ALLOWED_CASE_STATUSES:
        raise ValueError(f"Invalid case status '{new_status}'.")
    db = get_db()
    doc = db["case_temp"].find_one({"case_id": case_id})
    if doc is None:
        return None
    if doc.get("assigned_lawyer_id") != lawyer_id:
        raise PermissionError("You are not assigned to this case.")
    db["case_temp"].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": new_status, "updated_at": _now_iso()}},
    )
    doc["status"] = new_status
    doc["updated_at"] = _now_iso()
    return doc


def get_case_lawyer(case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the lawyer record referenced by a case (if any)."""
    lawyer_id = case.get("assigned_lawyer_id")
    if not lawyer_id:
        return None
    return get_db()["lawyer_temp"].find_one({"lawyer_id": lawyer_id})
