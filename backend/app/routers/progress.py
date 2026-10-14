"""Progress note endpoints for case tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies.auth import AuthUser, require_role
from ..services import progress_service
from ..utils.serialization import serialize_docs

router = APIRouter(tags=["progress"])


class ProgressNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)
    note_type: str = Field(default="progress", max_length=50)


@router.post("/cases/{case_id}/progress")
def add_progress_note(
    case_id: str,
    payload: ProgressNoteRequest,
    user: AuthUser = Depends(require_role("lawyer")),
):
    """Add a progress note to a case."""
    try:
        doc = progress_service.add_progress_note(
            case_id, user.lawyer_id, payload.note, payload.note_type
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {"progress_note": doc}


@router.get("/cases/{case_id}/progress")
def get_progress_notes(case_id: str, user: AuthUser = Depends(require_role("lawyer"))):
    """Retrieve all progress notes for a case (lawyer can see notes for their cases)."""
    # Verify the lawyer is assigned to this case
    db = get_db()
    case = db["case_temp"].find_one({"case_id": case_id})
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if case.get("assigned_lawyer_id") != user.lawyer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    notes = progress_service.get_case_progress_notes(case_id)
    return {"progress_notes": serialize_docs(notes)}
