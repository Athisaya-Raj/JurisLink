"""Pydantic models for authentication."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginUser(BaseModel):
    username: str
    role: str
    user_id: Optional[str] = None
    lawyer_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginUser
