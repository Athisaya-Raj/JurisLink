"""Case endpoints (submission, classification, retrieval, status updates)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..dependencies.auth import AuthUser, get_current_user, require_role
from ..models.case import CaseStatusUpdateRequest, CaseSubmitRequest
from ..services import appointment_service, case_service, invitation_service
from ..services.classification import ClassificationError
from ..utils.serialization import public_lawyer, serialize_doc, serialize_docs

router = APIRouter(tags=["cases"])


def _prediction_payload(doc: dict) -> dict:
    return {
        "category_id": doc.get("predicted_category_id"),
        "category_name": doc.get("predicted_category_name"),
        "confidence": doc.get("prediction_confidence"),
        "review_recommended": doc.get("prediction_review_recommended"),
        "explanation": doc.get("prediction_explanation"),
    }


@router.post("/demo/submit-and-classify")
def submit_and_classify(
    payload: CaseSubmitRequest,
    user: AuthUser = Depends(require_role("user")),
):
    """Validate, classify, and persist a new case, then send an invitation."""
    try:
        doc, disposition = case_service.submit_case(payload.model_dump(), user.user_id)
    except ClassificationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db = get_db()
    invitation = invitation_service.get_latest_invitation(doc.get("case_id"))
    invited_lawyer = None
    if invitation and invitation.get("lawyer_id"):
        invited_lawyer = db["lawyer_temp"].find_one({"lawyer_id": invitation["lawyer_id"]})

    if invited_lawyer:
        message = (
            f"Your case was submitted and sent to {invited_lawyer.get('name')} for review."
        )
    else:
        message = (
            "Your case was submitted but no eligible lawyer is currently available; "
            "it is pending assignment for manual review."
        )

    return {
        "disposition": disposition,
        "case": serialize_doc(doc),
        "prediction": _prediction_payload(doc),
        "invitation": serialize_doc(invitation),
        "lawyer": public_lawyer(invited_lawyer),
        "message": message,
    }


@router.get("/mine")
def my_cases(user: AuthUser = Depends(require_role("user"))):
    docs = list(
        get_db()["case_temp"].find({"user_id": user.user_id}).sort("created_at", -1)
    )
    return {"cases": serialize_docs(docs)}


@router.get("/assigned-to-me")
def assigned_cases(user: AuthUser = Depends(require_role("lawyer"))):
    """Cases the lawyer has accepted (assigned to them)."""
    docs = list(
        get_db()["case_temp"]
        .find({"assigned_lawyer_id": user.lawyer_id})
        .sort("created_at", -1)
    )
    return {"cases": serialize_docs(docs)}


@router.get("/{case_id}")
def case_detail(case_id: str, user: AuthUser = Depends(get_current_user)):
    doc = case_service.get_case_for_user(case_id, user)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    lawyer = case_service.get_case_lawyer(doc)
    invitation = invitation_service.get_latest_invitation(doc.get("case_id"))
    appointments = list(
        get_db()["appointment_temp"].find({"case_id": doc.get("case_id")}).sort("created_at", -1)
    )
    return {
        "case": serialize_doc(doc),
        "prediction": _prediction_payload(doc),
        "lawyer": public_lawyer(lawyer),
        "invitation": serialize_doc(invitation),
        "appointments": serialize_docs(appointments),
    }


@router.patch("/{case_id}/status")
def update_case_status(
    case_id: str,
    payload: CaseStatusUpdateRequest,
    user: AuthUser = Depends(require_role("lawyer")),
):
    try:
        doc = case_service.update_case_status(case_id, payload.status, user.lawyer_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case": serialize_doc(doc)}


@router.get("/{case_id}/slots")
def case_slots(case_id: str, user: AuthUser = Depends(require_role("user"))):
    doc = case_service.get_case_for_user(case_id, user)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not doc.get("assigned_lawyer_id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This case has not been accepted by a lawyer yet, so no slots are available.",
        )
    lawyer = case_service.get_case_lawyer(doc)
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned lawyer not found")
    slots = appointment_service.available_slots(lawyer)
    return {"lawyer": public_lawyer(lawyer), "slots": slots}
