"""Role-specific dashboard summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..database import get_db
from ..dependencies.auth import AuthUser, require_role
from ..utils.serialization import serialize_docs

router = APIRouter(tags=["dashboard"])


@router.get("/user")
def user_dashboard(user: AuthUser = Depends(require_role("user"))):
    db = get_db()
    cases = list(db["case_temp"].find({"user_id": user.user_id}))
    appointments = list(db["appointment_temp"].find({"user_id": user.user_id}))

    recent_cases = sorted(cases, key=lambda c: c.get("created_at") or "", reverse=True)[:5]
    recent_appointments = sorted(
        appointments, key=lambda a: a.get("created_at") or "", reverse=True
    )[:5]

    return {
        "total_cases": len(cases),
        "awaiting_assignment": sum(1 for c in cases if c.get("status") == "pending_assignment"),
        "assigned_cases": sum(1 for c in cases if c.get("assigned_lawyer_id")),
        "upcoming_appointments": sum(
            1 for a in appointments if a.get("status") in ("requested", "booked")
        ),
        "recent_cases": serialize_docs(recent_cases),
        "recent_appointments": serialize_docs(recent_appointments),
    }


@router.get("/lawyer")
def lawyer_dashboard(user: AuthUser = Depends(require_role("lawyer"))):
    db = get_db()
    cases = list(db["case_temp"].find({"assigned_lawyer_id": user.lawyer_id}))
    appointments = list(db["appointment_temp"].find({"lawyer_id": user.lawyer_id}))
    invitations = list(db["case_invitation_temp"].find({"lawyer_id": user.lawyer_id}))

    active_cases = [c for c in cases if c.get("status") in ("assigned", "in_review")]
    completed_cases = [c for c in cases if c.get("status") in ("resolved", "closed")]
    upcoming_appointments = [a for a in appointments if a.get("status") in ("requested", "booked")]

    recent_invitations = sorted(
        invitations, key=lambda i: i.get("created_at") or "", reverse=True
    )[:5]
    recent_cases = sorted(cases, key=lambda c: c.get("created_at") or "", reverse=True)[:5]
    recent_appointments = sorted(
        appointments, key=lambda a: a.get("created_at") or "", reverse=True
    )[:5]

    return {
        "pending_invitations": sum(1 for i in invitations if i.get("status") == "pending"),
        "accepted_cases": len(active_cases),
        "completed_cases": len(completed_cases),
        "upcoming_appointments": len(upcoming_appointments),
        "recent_invitations": serialize_docs(recent_invitations),
        "recent_cases": serialize_docs(recent_cases),
        "recent_appointments": serialize_docs(recent_appointments),
    }
