"""Authentication dependencies (JWT bearer) and role enforcement.

The backend is the single source of truth for identity and role. The frontend
never supplies a lawyer/user id as proof of authorization — only the signed
token is trusted.
"""
from __future__ import annotations

from typing import Callable, Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated principal extracted from a verified JWT."""

    def __init__(self, **claims):
        self.sub: Optional[str] = claims.get("sub")
        self.role: Optional[str] = claims.get("role")
        self.user_id: Optional[str] = claims.get("user_id")
        self.lawyer_id: Optional[str] = claims.get("lawyer_id")
        self.claims: dict = claims

    @property
    def is_user(self) -> bool:
        return self.role == "user"

    @property
    def is_lawyer(self) -> bool:
        return self.role == "lawyer"


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not payload.get("sub") or not payload.get("role"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return AuthUser(**payload)


def require_role(*roles: str) -> Callable:
    """Build a dependency that enforces one of the given roles."""

    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep
