"""Appointment booking with atomic double-booking protection.

Slots live inside ``lawyer_temp.available_slots``. Booking is made safe by a
partial unique index on ``appointment_temp.slot_id`` for active statuses, so a
second booking of the same slot is rejected even under a race.
"""
from __future__ import annotations

import datetime as dt
import random
import string
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..database import get_db

ACTIVE_APPOINTMENT_STATUSES = ["requested", "booked"]
_ALLOWED_APPOINTMENT_STATUSES = ["requested", "booked", "completed", "cancelled"]


class AppointmentError(RuntimeError):
    """Raised for invalid or conflicting booking attempts."""


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _generate_id(prefix: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{rand}"


def available_slots(lawyer: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the lawyer's still-available, non-past slots."""
    today = dt.date.today().isoformat()
    slots = lawyer.get("available_slots") or []
    result = []
    for slot in slots:
        if slot.get("status") != "available":
            continue
        if (slot.get("date") or "") < today:
            continue
        result.append(dict(slot))
    return result


def find_slot(lawyer: Dict[str, Any], slot_id: str) -> Optional[Dict[str, Any]]:
    for slot in lawyer.get("available_slots") or []:
        if slot.get("slot_id") == slot_id:
            return slot
    return None


def book_appointment(
    case: Dict[str, Any],
    lawyer: Dict[str, Any],
    slot_id: str,
    notes: Optional[str],
    user_id: str,
) -> Dict[str, Any]:
    """Persist a new appointment and mark the lawyer's slot as booked."""
    db = get_db()

    slot = find_slot(lawyer, slot_id)
    if slot is None:
        raise AppointmentError("That time slot does not exist for this lawyer.")

    if slot.get("status") != "available":
        raise AppointmentError("That time slot is no longer available.")

    slot_date = slot.get("date") or ""
    if slot_date and slot_date < dt.date.today().isoformat():
        raise AppointmentError("That time slot is in the past.")

    doc_id = ObjectId()
    appointment_id = _generate_id("APPT")
    doc: Dict[str, Any] = {
        "_id": doc_id,
        "appointment_id": appointment_id,
        "case_id": case.get("case_id"),
        "user_id": user_id,
        "lawyer_id": lawyer.get("lawyer_id"),
        "slot_id": slot_id,
        "date": slot.get("date"),
        "start_time": slot.get("start_time"),
        "end_time": slot.get("end_time"),
        "status": "booked",
        "notes": (notes or "").strip() or None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    try:
        # The partial unique index on slot_id (active statuses) is the atomic
        # guard against double-booking.
        db["appointment_temp"].insert_one(doc)
    except DuplicateKeyError as exc:
        raise AppointmentError(
            "That time slot has already been booked. Please choose another slot."
        ) from exc

    # Mark the embedded slot as booked so subsequent slot listings reflect it.
    db["lawyer_temp"].update_one(
        {"_id": lawyer["_id"], "available_slots.slot_id": slot_id},
        {"$set": {"available_slots.$.status": "booked"}},
    )
    return doc


def get_appointment_for_user(appointment_id: str, auth) -> Optional[Dict[str, Any]]:
    """Fetch an appointment if ``auth`` owns it (user) or it belongs to them (lawyer)."""
    db = get_db()
    doc = db["appointment_temp"].find_one({"appointment_id": appointment_id})
    if doc is None:
        return None
    if auth.role == "user":
        if doc.get("user_id") != auth.user_id:
            return None
    elif auth.role == "lawyer":
        if doc.get("lawyer_id") != auth.lawyer_id:
            return None
    else:
        return None
    return doc


def update_appointment_status(
    appointment_id: str, new_status: str, auth
) -> Optional[Dict[str, Any]]:
    """Apply a permitted status transition; frees the slot on cancellation."""
    new_status = (new_status or "").strip().lower()
    if new_status not in _ALLOWED_APPOINTMENT_STATUSES:
        raise ValueError(f"Invalid appointment status '{new_status}'.")

    db = get_db()
    doc = db["appointment_temp"].find_one({"appointment_id": appointment_id})
    if doc is None:
        return None

    # Authorization: the client user owns it, or the assigned lawyer manages it.
    if auth.role == "user":
        if doc.get("user_id") != auth.user_id:
            raise PermissionError("This appointment does not belong to you.")
        # Clients may cancel their own appointments, not mark them completed.
        if new_status not in ("cancelled",):
            raise PermissionError("You can only cancel your own appointment.")
    elif auth.role == "lawyer":
        if doc.get("lawyer_id") != auth.lawyer_id:
            raise PermissionError("This appointment is not with you.")
        # Lawyers may confirm, complete, or cancel their own appointments.
        if new_status not in ("booked", "completed", "cancelled"):
            raise PermissionError("Invalid status for a lawyer to set.")
    else:
        raise PermissionError("Forbidden.")

    db["appointment_temp"].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": new_status, "updated_at": _now_iso()}},
    )

    # Keep lawyer slot state consistent: cancel frees the slot for reuse.
    if new_status == "cancelled":
        db["lawyer_temp"].update_one(
            {"lawyer_id": doc.get("lawyer_id"), "available_slots.slot_id": doc.get("slot_id")},
            {"$set": {"available_slots.$.status": "available"}},
        )

    doc["status"] = new_status
    doc["updated_at"] = _now_iso()
    return doc
