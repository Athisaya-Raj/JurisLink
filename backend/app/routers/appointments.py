"""Appointment endpoints (booking, listing, status updates)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..dependencies.auth import AuthUser, get_current_user, require_role
from ..models.appointment import AppointmentCreateRequest, AppointmentStatusUpdateRequest
from ..services import appointment_service, case_service
from ..services.appointment_service import AppointmentError
from ..utils.serialization import serialize_doc, serialize_docs

router = APIRouter(tags=["appointments"])


@router.post("")
def create_appointment(
    payload: AppointmentCreateRequest,
    user: AuthUser = Depends(require_role("user")),
):
    case_doc = case_service.get_case_for_user(payload.case_id, user)
    if case_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or does not belong to you.",
        )
    lawyer = case_service.get_case_lawyer(case_doc)
    if lawyer is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This case has no assigned lawyer yet.",
        )
    try:
        appointment = appointment_service.book_appointment(
            case_doc, lawyer, payload.slot_id, payload.notes, user.user_id
        )
    except AppointmentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return {"appointment": serialize_doc(appointment)}


@router.get("/mine")
def my_appointments(user: AuthUser = Depends(require_role("user"))):
    docs = list(
        get_db()["appointment_temp"].find({"user_id": user.user_id}).sort("created_at", -1)
    )
    return {"appointments": serialize_docs(docs)}


@router.get("/for-me")
def appointments_for_me(user: AuthUser = Depends(require_role("lawyer"))):
    docs = list(
        get_db()["appointment_temp"].find({"lawyer_id": user.lawyer_id}).sort("created_at", -1)
    )
    return {"appointments": serialize_docs(docs)}


@router.patch("/{appointment_id}/status")
def update_status(
    appointment_id: str,
    payload: AppointmentStatusUpdateRequest,
    user: AuthUser = Depends(get_current_user),
):
    try:
        doc = appointment_service.update_appointment_status(appointment_id, payload.status, user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return {"appointment": serialize_doc(doc)}
