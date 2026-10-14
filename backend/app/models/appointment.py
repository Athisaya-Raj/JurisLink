"""Pydantic models for appointments."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AppointmentCreateRequest(BaseModel):
    case_id: str = Field(..., min_length=1, max_length=100)
    slot_id: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=2000)


class AppointmentStatusUpdateRequest(BaseModel):
    status: str = Field(..., max_length=40)
