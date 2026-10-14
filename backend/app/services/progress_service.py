"""Case progress tracking and notes management.

Allows lawyers to add progress notes to cases with timestamps.
Each note is associated with a case_id and includes the lawyer_id and timestamp.
"""
from __future__ import annotations

import datetime as dt
import random
import string
from typing import Any, Dict, List, Optional

from bson import ObjectId

from ..database import get_db


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _generate_id(prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{rand}"


def add_progress_note(
    case_id: str, lawyer_id: str, note: str, note_type: str = "progress"
) -> Dict[str, Any]:
    """Add a progress note to a case.

    Args:
        case_id: The case ID.
        lawyer_id: The lawyer who is adding the note.
        note: The note content.
        note_type: Type of note (progress, consultation_scheduled, consultation_completed, etc.)

    Returns:
        The created progress note document.
    """
    db = get_db()

    # Verify the lawyer is assigned to this case
    case = db["case_temp"].find_one({"case_id": case_id})
    if case is None:
        raise ValueError("Case not found.")
    if case.get("assigned_lawyer_id") != lawyer_id:
        raise PermissionError("You are not assigned to this case.")

    progress_note_id = _generate_id("NOTE")
    now = _now_iso()

    doc = {
        "_id": ObjectId(),
        "progress_note_id": progress_note_id,
        "case_id": case_id,
        "lawyer_id": lawyer_id,
        "note_type": note_type,
        "content": note.strip(),
        "created_at": now,
        "updated_at": now,
    }

    db["progress_note_temp"].insert_one(doc)
    return doc


def get_case_progress_notes(case_id: str) -> List[Dict[str, Any]]:
    """Retrieve all progress notes for a case, sorted by created_at descending."""
    return list(
        get_db()["progress_note_temp"]
        .find({"case_id": case_id})
        .sort("created_at", -1)
    )


def update_progress_note(
    progress_note_id: str, lawyer_id: str, content: str
) -> Optional[Dict[str, Any]]:
    """Update a progress note (only by the original author)."""
    db = get_db()
    note = db["progress_note_temp"].find_one({"progress_note_id": progress_note_id})
    if note is None:
        raise ValueError("Progress note not found.")
    if note.get("lawyer_id") != lawyer_id:
        raise PermissionError("You can only edit your own notes.")

    db["progress_note_temp"].update_one(
        {"_id": note["_id"]},
        {"$set": {"content": content.strip(), "updated_at": _now_iso()}},
    )
    note["content"] = content.strip()
    note["updated_at"] = _now_iso()
    return note
