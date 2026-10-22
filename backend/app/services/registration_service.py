"""User and lawyer registration service.

Handles registration for new users and lawyers, storing them in the application-managed
user_temp and lawyer_temp collections.
"""
from __future__ import annotations

import random
import re
import string
from typing import Any, Dict, Optional

from bson import ObjectId

from ..config import settings
from ..database import get_db
from ..utils.security import hash_password, verify_password


def _generate_id(prefix: str) -> str:
    """Generate a unique ID with timestamp and random suffix."""
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{rand}"


def _validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def _validate_password(password: str) -> tuple[bool, Optional[str]]:
    """Validate password strength.
    
    Returns (is_valid, error_message).
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    return True, None


def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new user (client).
    
    Args:
        username: Unique username for login
        email: Email address (unique)
        password: Plain-text password (will be hashed)
        full_name: User's full name
        phone: Phone number (optional)
        location: City or location (optional)
    
    Returns:
        User document with user_id, username, email, etc.
    
    Raises:
        ValueError: If validation fails or user already exists.
    """
    db = get_db()
    
    # Validation
    username = (username or "").strip()
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() if phone else None
    location = (location or "").strip() if location else None
    
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if not email or not _validate_email(email):
        raise ValueError("Please enter a valid email address.")
    if not full_name:
        raise ValueError("Please enter your full name.")
    if not password:
        raise ValueError("Password is required.")
    
    is_valid_pwd, pwd_error = _validate_password(password)
    if not is_valid_pwd:
        raise ValueError(pwd_error)
    
    # Check for existing username
    if db["user_temp"].find_one({"username": username}):
        raise ValueError(f"Username '{username}' is already taken.")
    
    # Check for existing email
    if db["user_temp"].find_one({"email": email}):
        raise ValueError(f"Email '{email}' is already registered.")
    
    # Create user document
    user_id = _generate_id("USER")
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    
    user_doc = {
        "_id": ObjectId(),
        "user_id": user_id,
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "full_name": full_name,
        "phone": phone,
        "location": location,
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }
    
    db["user_temp"].insert_one(user_doc)
    
    # Return user document without password hash
    user_doc.pop("password_hash")
    return user_doc


def register_lawyer(
    username: str,
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    bar_registration: Optional[str] = None,
    years_experience: Optional[int] = None,
    location: Optional[str] = None,
    specializations: Optional[list] = None,
) -> Dict[str, Any]:
    """Register a new lawyer.
    
    Args:
        username: Unique username for login
        email: Email address (unique)
        password: Plain-text password (will be hashed)
        full_name: Lawyer's full name
        phone: Phone number (optional)
        bar_registration: Bar council registration number (optional)
        years_experience: Years of legal experience (optional)
        location: City or location (optional)
        specializations: List of legal category IDs (optional)
    
    Returns:
        Lawyer document with lawyer_id, username, email, etc.
    
    Raises:
        ValueError: If validation fails or lawyer already exists.
    """
    db = get_db()
    
    # Validation
    username = (username or "").strip()
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() if phone else None
    bar_registration = (bar_registration or "").strip() if bar_registration else None
    location = (location or "").strip() if location else None
    specializations = specializations or []
    
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if not email or not _validate_email(email):
        raise ValueError("Please enter a valid email address.")
    if not full_name:
        raise ValueError("Please enter your full name.")
    if not password:
        raise ValueError("Password is required.")
    
    is_valid_pwd, pwd_error = _validate_password(password)
    if not is_valid_pwd:
        raise ValueError(pwd_error)
    
    if years_experience is not None and years_experience < 0:
        raise ValueError("Years of experience must be a positive number.")
    
    # Check for existing username
    if db["user_temp"].find_one({"username": username}):
        raise ValueError(f"Username '{username}' is already taken.")
    if db["lawyer_temp"].find_one({"username": username}):
        raise ValueError(f"Username '{username}' is already taken.")
    
    # Check for existing email
    if db["user_temp"].find_one({"email": email}):
        raise ValueError(f"Email '{email}' is already registered.")
    if db["lawyer_temp"].find_one({"email": email}):
        raise ValueError(f"Email '{email}' is already registered.")
    
    # Create lawyer document
    lawyer_id = _generate_id("LAW")
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    
    # Get specialization names if provided
    specialization_names = []
    if specializations:
        categories = db["legal_categories_temp"].find(
            {"category_id": {"$in": specializations}},
            {"category_id": 1, "name": 1}
        )
        specialization_names = [c.get("name", c.get("category_id")) for c in categories]
    
    lawyer_doc = {
        "_id": ObjectId(),
        "lawyer_id": lawyer_id,
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "full_name": full_name,
        "phone": phone,
        "bar_registration": bar_registration,
        "years_experience": years_experience or 0,
        "location": location,
        "specializations": specializations,
        "specialization_names": specialization_names,
        "role": "lawyer",
        "approval_status": "pending",  # New lawyers require admin approval
        "created_at": now,
        "updated_at": now,
        "available_slots": [],  # Empty initially
        "availability_status": "available",
    }
    
    db["lawyer_temp"].insert_one(lawyer_doc)
    
    # Return lawyer document without password hash
    lawyer_doc.pop("password_hash")
    return lawyer_doc
