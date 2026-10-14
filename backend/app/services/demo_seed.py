"""Idempotent demo seeding for the lawyer invitation workflow.

Creates (only if missing) clearly-labelled synthetic cases in the demo
lawyer's specialization with pending and accepted invitations. Re-running
is a no-op when the records already exist, and existing real/seed records are
never overwritten or deleted.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from bson import ObjectId

from ..config import settings
from ..database import get_db
from . import invitation_service, progress_service


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _make_past_timestamp(hours_ago: int) -> str:
    """Generate a timestamp some hours in the past."""
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours_ago)
    return past.isoformat()


def seed_demo() -> Dict[str, Any]:
    """Seed demo cases: one pending invitation and 2+ accepted cases with progress notes.

    Returns a summary describing what was created vs. already present.
    Maintains backward compatibility with expected test fields.
    """
    db = get_db()
    case_id_pending = settings.DEMO_SEED_CASE_ID
    lawyer_id = settings.DEMO_LAWYER_ID
    user_id = settings.DEMO_USER_ID

    lawyer = db["lawyer_temp"].find_one({"lawyer_id": lawyer_id})
    if lawyer is None:
        raise RuntimeError(
            f"DEMO_LAWYER_ID '{lawyer_id}' was not found in lawyer_temp. "
            "Configure it to an existing lawyer record before seeding."
        )

    category_id = (lawyer.get("specializations") or ["FAM01"])[0]
    category_name = (lawyer.get("specialization_names") or [category_id])[0]
    
    # === PENDING INVITATION CASE (MAIN SEED) ===
    case = db["case_temp"].find_one({"case_id": case_id_pending})
    case_created = False
    if case is None:
        case = {
            "_id": ObjectId(),
            "case_id": case_id_pending,
            "user_id": user_id,
            "title": "Sample family dispute (demo invitation)",
            "description": (
                "My spouse and I have a serious disagreement about our marital "
                "rights and responsibilities, and I would like legal guidance."
            ),
            "supporting_info": (
                "Synthetic demonstration case seeded for the lawyer invitation workflow."
            ),
            "predicted_category_id": category_id,
            "predicted_category_name": category_name,
            "prediction_confidence": 0.9,
            "prediction_explanation": "Automated classification; not legal advice.",
            "prediction_review_recommended": False,
            "status": "pending_assignment",
            "created_at": _make_past_timestamp(72),
            "updated_at": _make_past_timestamp(72),
            "demo_only": True,
            "demo_seed": True,
        }
        db["case_temp"].insert_one(case)
        case_created = True

    # Create pending invitation if not exists
    existing_inv = db[invitation_service.INVITATION_COLLECTION].find_one(
        {"case_id": case_id_pending, "lawyer_id": lawyer_id}
    )
    invitation_created = False
    if existing_inv is None:
        invitation_service.create_invitation(case, lawyer=lawyer)
        invitation_created = True

    invitation = db[invitation_service.INVITATION_COLLECTION].find_one(
        {"case_id": case_id_pending, "lawyer_id": lawyer_id}
    )

    # Main return value for backward compatibility with tests
    result = {
        "case_id": case_id_pending,
        "case_created": case_created,
        "invitation_created": invitation_created,
        "lawyer_id": lawyer_id,
        "lawyer_name": lawyer.get("name"),
        "invitation_status": invitation.get("status") if invitation else None,
        "invitation_id": invitation.get("invitation_id") if invitation else None,
        "accepted_cases": [],  # Track created accepted cases for reference
    }

    # === ACCEPTED CASE 1: With appointment (only create if seed enables extra demos) ===
    # Only create these if not already created in a previous seed run
    case_id_accepted_1 = "DEMO-CASE-ACCEPTED-001"
    case_1_existing = db["case_temp"].find_one({"case_id": case_id_accepted_1})
    if case_1_existing is None:
        case_1 = {
            "_id": ObjectId(),
            "case_id": case_id_accepted_1,
            "user_id": user_id,
            "title": "Tenancy rights question",
            "description": (
                "My landlord has not returned my security deposit after I vacated the apartment. "
                "I provided proper notice and left the premises in good condition."
            ),
            "supporting_info": "Vacated 3 months ago. Landlord claims repairs needed but provided no itemized list.",
            "predicted_category_id": category_id,
            "predicted_category_name": category_name,
            "prediction_confidence": 0.85,
            "prediction_explanation": "Automated classification; not legal advice.",
            "prediction_review_recommended": False,
            "status": "assigned",
            "assigned_lawyer_id": lawyer_id,
            "assigned_lawyer_doc_id": str(lawyer.get("_id", "")),
            "assigned_lawyer_name": lawyer.get("name", ""),
            "created_at": _make_past_timestamp(120),
            "updated_at": _make_past_timestamp(24),
            "accepted_at": _make_past_timestamp(96),
            "demo_only": True,
            "demo_seed": True,
        }
        db["case_temp"].insert_one(case_1)
        
        # Add progress note
        try:
            progress_service.add_progress_note(
                case_id_accepted_1,
                lawyer_id,
                "Initial consultation completed with client. Reviewed lease terms and deposit conditions. Will prepare legal letter to landlord requesting itemized claim.",
                "progress",
            )
        except Exception:
            pass
        
        result["accepted_cases"].append({
            "case_id": case_id_accepted_1,
            "title": case_1.get("title"),
            "created": True,
        })

    # === ACCEPTED CASE 2: With consultation completed ===
    case_id_accepted_2 = "DEMO-CASE-ACCEPTED-002"
    case_2_existing = db["case_temp"].find_one({"case_id": case_id_accepted_2})
    if case_2_existing is None:
        case_2 = {
            "_id": ObjectId(),
            "case_id": case_id_accepted_2,
            "user_id": user_id,
            "title": "Employment contract review",
            "description": (
                "I have been offered a new position with a non-compete clause. "
                "I would like to understand my rights and obligations under this clause."
            ),
            "supporting_info": "Current employer in same industry. Contract period is 2 years.",
            "predicted_category_id": category_id,
            "predicted_category_name": category_name,
            "prediction_confidence": 0.88,
            "prediction_explanation": "Automated classification; not legal advice.",
            "prediction_review_recommended": False,
            "status": "in_review",
            "assigned_lawyer_id": lawyer_id,
            "assigned_lawyer_doc_id": str(lawyer.get("_id", "")),
            "assigned_lawyer_name": lawyer.get("name", ""),
            "created_at": _make_past_timestamp(168),
            "updated_at": _make_past_timestamp(12),
            "accepted_at": _make_past_timestamp(144),
            "demo_only": True,
            "demo_seed": True,
        }
        db["case_temp"].insert_one(case_2)
        
        # Add progress notes
        try:
            progress_service.add_progress_note(
                case_id_accepted_2,
                lawyer_id,
                "Initial consultation completed. Reviewed non-compete clause - appears overly broad and potentially unenforceable in our jurisdiction.",
                "progress",
            )
            progress_service.add_progress_note(
                case_id_accepted_2,
                lawyer_id,
                "Follow-up consultation held. Provided drafted counter-proposal for client to present to employer. Advised on enforceability precedents.",
                "progress",
            )
        except Exception:
            pass
        
        result["accepted_cases"].append({
            "case_id": case_id_accepted_2,
            "title": case_2.get("title"),
            "created": True,
        })

    return result
