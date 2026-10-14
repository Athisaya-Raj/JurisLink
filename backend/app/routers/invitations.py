"""Case-invitation endpoints (scoped to the authenticated lawyer)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..dependencies.auth import AuthUser, require_role
from ..models.invitation import InvitationDeclineRequest
from ..services import invitation_service
from ..services.invitation_service import InvitationNotFound, InvitationStateError
from ..utils.serialization import public_lawyer, serialize_doc, serialize_docs

router = APIRouter(tags=["invitations"])


@router.get("")
def list_invitations(user: AuthUser = Depends(require_role("lawyer"))):
    invitations = invitation_service.list_invitations(user.lawyer_id)
    return {
        "invitations": serialize_docs(invitations),
        "counts": invitation_service.invitation_counts(user.lawyer_id),
    }


@router.get("/{invitation_id}")
def invitation_detail(invitation_id: str, user: AuthUser = Depends(require_role("lawyer"))):
    invitation = invitation_service.get_invitation_for_lawyer(invitation_id, user.lawyer_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    db = get_db()
    case = db["case_temp"].find_one({"case_id": invitation.get("case_id")})
    lawyer = db["lawyer_temp"].find_one({"lawyer_id": invitation.get("lawyer_id")})
    return {
        "invitation": serialize_doc(invitation),
        "case": serialize_doc(case),
        "lawyer": public_lawyer(lawyer),
    }


@router.post("/{invitation_id}/accept")
def accept_invitation(invitation_id: str, user: AuthUser = Depends(require_role("lawyer"))):
    try:
        invitation, case = invitation_service.accept_invitation(invitation_id, user.lawyer_id)
    except InvitationNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    except InvitationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return {"invitation": serialize_doc(invitation), "case": serialize_doc(case)}


@router.post("/{invitation_id}/decline")
def decline_invitation(
    invitation_id: str,
    payload: Optional[InvitationDeclineRequest] = None,
    user: AuthUser = Depends(require_role("lawyer")),
):
    reason = payload.reason if payload else None
    try:
        invitation, next_lawyer = invitation_service.decline_invitation(
            invitation_id, user.lawyer_id, reason
        )
    except InvitationNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    except InvitationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return {
        "invitation": serialize_doc(invitation),
        "reassigned": next_lawyer is not None,
        "next_lawyer": public_lawyer(next_lawyer),
    }
