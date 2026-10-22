"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies.auth import AuthUser, get_current_user
from ..models.auth import LoginRequest, LoginResponse, LoginUser
from ..services import registration_service
from ..utils.security import authenticate_demo, create_access_token, verify_password

router = APIRouter(tags=["auth"])


class UserRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(default=None, max_length=20)
    location: str = Field(default=None, max_length=255)


class LawyerRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(default=None, max_length=20)
    bar_registration: str = Field(default=None, max_length=100)
    years_experience: int = Field(default=0, ge=0)
    location: str = Field(default=None, max_length=255)
    specializations: list = Field(default_factory=list)


class AuthResponse(BaseModel):
    message: str
    user_id: str = None
    lawyer_id: str = None


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """Log in with username and password.
    
    Supports both demo accounts and registered users/lawyers.
    """
    db = get_db()
    
    # Try demo accounts first (backward compatibility)
    claims = authenticate_demo(payload.username, payload.password)
    if claims is not None:
        token = create_access_token(claims)
        user = LoginUser(
            username=claims["sub"],
            role=claims["role"],
            user_id=claims.get("user_id"),
            lawyer_id=claims.get("lawyer_id"),
        )
        return LoginResponse(access_token=token, user=user)
    
    # Try registered users
    user_doc = db["user_temp"].find_one({"username": payload.username})
    if user_doc and verify_password(payload.password, user_doc.get("password_hash", "")):
        claims = {
            "sub": user_doc["username"],
            "role": "user",
            "user_id": user_doc["user_id"],
        }
        token = create_access_token(claims)
        user = LoginUser(
            username=claims["sub"],
            role=claims["role"],
            user_id=claims.get("user_id"),
        )
        return LoginResponse(access_token=token, user=user)
    
    # Try registered lawyers
    lawyer_doc = db["lawyer_temp"].find_one({"username": payload.username})
    if lawyer_doc and verify_password(payload.password, lawyer_doc.get("password_hash", "")):
        # Check approval status (for future enhancement)
        # if lawyer_doc.get("approval_status") != "approved":
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Your lawyer account is pending admin approval",
        #     )
        claims = {
            "sub": lawyer_doc["username"],
            "role": "lawyer",
            "lawyer_id": lawyer_doc["lawyer_id"],
        }
        token = create_access_token(claims)
        user = LoginUser(
            username=claims["sub"],
            role=claims["role"],
            lawyer_id=claims.get("lawyer_id"),
        )
        return LoginResponse(access_token=token, user=user)
    
    # No matching account
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )


@router.post("/register/user", response_model=AuthResponse)
def register_user(payload: UserRegistrationRequest):
    """Register a new user account."""
    try:
        user_doc = registration_service.register_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            location=payload.location,
        )
        return AuthResponse(
            message="User account created successfully",
            user_id=user_doc["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/register/lawyer", response_model=AuthResponse)
def register_lawyer(payload: LawyerRegistrationRequest):
    """Register a new lawyer account."""
    try:
        lawyer_doc = registration_service.register_lawyer(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            bar_registration=payload.bar_registration,
            years_experience=payload.years_experience,
            location=payload.location,
            specializations=payload.specializations,
        )
        return AuthResponse(
            message="Lawyer account created successfully",
            lawyer_id=lawyer_doc["lawyer_id"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    result = {
        "username": user.sub,
        "role": user.role,
        "user_id": user.user_id,
        "lawyer_id": user.lawyer_id,
    }
    if user.is_lawyer and user.lawyer_id:
        lawyer = get_db()["lawyer_temp"].find_one({"lawyer_id": user.lawyer_id})
        if lawyer:
            result["lawyer_name"] = lawyer.get("full_name")
            result["specialization_names"] = lawyer.get("specialization_names")
    return result
