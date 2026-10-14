"""Lawyer endpoints (profiles, availability, slot views)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..dependencies.auth import AuthUser, get_current_user, require_role
from ..services import appointment_service, lawyer_matching
from ..utils.serialization import public_lawyer, serialize_doc, serialize_docs

router = APIRouter(tags=["lawyers"])


@router.get("/available")
def available_lawyers(category_id: str, user: AuthUser = Depends(get_current_user)):
    lawyers = lawyer_matching.find_eligible_lawyers(category_id)
    return {"lawyers": [public_lawyer(l) for l in lawyers]}


@router.get("/me")
def my_profile(user: AuthUser = Depends(require_role("lawyer"))):
    lawyer = get_db()["lawyer_temp"].find_one({"lawyer_id": user.lawyer_id})
    if lawyer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo lawyer record not found for the configured DEMO_LAWYER_ID.",
        )
    return {"lawyer": public_lawyer(lawyer)}


@router.get("/me/slots")
def my_slots(user: AuthUser = Depends(require_role("lawyer"))):
    """The lawyer's own slots with their booking status and linked appointment."""
    db = get_db()
    lawyer = db["lawyer_temp"].find_one({"lawyer_id": user.lawyer_id})
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer not found")

    active = appointment_service.ACTIVE_APPOINTMENT_STATUSES
    appointments = list(db["appointment_temp"].find({"lawyer_id": user.lawyer_id, "status": {"$in": active}}))
    by_slot = {a.get("slot_id"): a for a in appointments}

    slots = lawyer.get("available_slots") or []
    slot_view = []
    for slot in slots:
        entry = dict(slot)
        appt = by_slot.get(slot.get("slot_id"))
        entry["appointment"] = serialize_doc(appt) if appt else None
        slot_view.append(entry)

    return {
        "lawyer": public_lawyer(lawyer),
        "slots": slot_view,
        "appointments": serialize_docs(appointments),
    }
