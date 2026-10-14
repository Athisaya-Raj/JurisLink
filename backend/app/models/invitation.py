"""Pydantic models for case invitations."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InvitationDeclineRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)
