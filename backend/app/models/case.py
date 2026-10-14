"""Pydantic models for cases."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CaseSubmitRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1, max_length=10000)
    supporting_info: Optional[str] = Field(default=None, max_length=5000)
    preferred_date: Optional[str] = Field(default=None, max_length=100)
    # Client-generated idempotency key to guard against duplicate submissions.
    client_request_id: Optional[str] = Field(default=None, max_length=128)


class CaseStatusUpdateRequest(BaseModel):
    status: str = Field(..., max_length=40)


class CaseDetailResponse(BaseModel):
    case: Dict[str, Any]
    prediction: Optional[Dict[str, Any]] = None
    lawyer: Optional[Dict[str, Any]] = None
    appointments: list = []
