"""Lawyer matching and deterministic assignment.

Lawyers are matched to a predicted category, then ranked by current workload
(active cases + pending invitations) and a stable tie-breaker. Matching never
invents credentials or availability; it operates only on the imported
``lawyer_temp`` records.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ..database import get_db

# Statuses that count toward a lawyer's active case workload.
_ACTIVE_CASE_STATUSES = ["assigned", "in_review"]


def find_eligible_lawyers(category_id: str) -> List[Dict[str, Any]]:
    """Lawyers whose specialization includes the category and who are available."""
    db = get_db()
    return list(
        db["lawyer_temp"].find(
            {
                "specializations": category_id,
                "availability_status": "available",
            }
        )
    )


def _case_workload(lawyer_id: str) -> int:
    return get_db()["case_temp"].count_documents(
        {"assigned_lawyer_id": lawyer_id, "status": {"$in": _ACTIVE_CASE_STATUSES}}
    )


def _invitation_workload(lawyer_id: str) -> int:
    return get_db()["case_invitation_temp"].count_documents(
        {"lawyer_id": lawyer_id, "status": "pending"}
    )


def total_workload(lawyer_id: str) -> int:
    """Active cases + pending invitations (the current load on a lawyer)."""
    return _case_workload(lawyer_id) + _invitation_workload(lawyer_id)


def rank_eligible_lawyers(category_id: str) -> List[Dict[str, Any]]:
    """Eligible lawyers ordered by (workload ascending, lawyer_id ascending)."""
    lawyers = find_eligible_lawyers(category_id)
    scored = [
        (total_workload(l.get("lawyer_id", "")), l.get("lawyer_id", ""), l)
        for l in lawyers
    ]
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored]


def assign_lawyer(
    category_id: str, exclude_lawyer_ids: Optional[Set[str]] = None
) -> Optional[Dict[str, Any]]:
    """Pick the best eligible lawyer for a category, or ``None``.

    Rule (transparent & deterministic):
        1. specialization must include ``category_id``
        2. ``availability_status == "available"``
        3. rank by (workload ascending, lawyer_id ascending)
        4. skip any lawyer whose id is in ``exclude_lawyer_ids`` (already invited)
    """
    excluded = exclude_lawyer_ids or set()
    for lawyer in rank_eligible_lawyers(category_id):
        if lawyer.get("lawyer_id") not in excluded:
            return lawyer
    return None
