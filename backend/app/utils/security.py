"""JWT helpers, password hashing, and demo account authentication.

These credentials are DEMO ONLY and are intentionally fixed by the project
specification. A real deployment would validate against a user store with
hashed passwords.

For new registrations, passwords are hashed using a simple scheme suitable
for demo/development. In production, use bcrypt or argon2.
"""
from __future__ import annotations

import datetime as dt
import hashlib
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


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256 with the JWT secret as salt.
    
    This is a simple scheme suitable for demo/development.
    Production should use bcrypt or argon2.
    """
    salt = settings.JWT_SECRET_KEY.encode("utf-8")
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000  # iterations
    )
    return hashed.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hash."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)



def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, raising ``jwt.InvalidTokenError`` on failure."""
    return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
