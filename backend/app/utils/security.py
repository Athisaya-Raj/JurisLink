"""JWT helpers and the two hardcoded demo accounts.

These credentials are DEMO ONLY and are intentionally fixed by the project
specification. A real deployment would validate against a user store with
hashed passwords.
"""
from __future__ import annotations

import datetime as dt
import hmac
from typing import Any, Dict, Optional

import jwt as pyjwt

from ..config import settings


def authenticate_demo(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Return the JWT claims for a valid demo account, or ``None``.

    Constant-time comparison avoids trivial timing side-channels even though
    the credentials themselves are public demo values.
    """
    user = (username or "").strip().lower()
    supplied = password or ""

    if user == "user" and hmac.compare_digest(supplied, "user"):
        return {
            "sub": "user",
            "role": "user",
            "user_id": settings.DEMO_USER_ID,
        }
    if user == "lawyer" and hmac.compare_digest(supplied, "lawyer"):
        return {
            "sub": "lawyer",
            "role": "lawyer",
            "lawyer_id": settings.DEMO_LAWYER_ID,
        }
    return None


def create_access_token(claims: Dict[str, Any]) -> str:
    """Sign a JWT access token with the configured secret."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = dict(claims)
    payload["iat"] = now
    payload["exp"] = now + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, raising ``jwt.InvalidTokenError`` on failure."""
    return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
