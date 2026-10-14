"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..dependencies.auth import AuthUser, get_current_user
from ..models.auth import LoginRequest, LoginResponse, LoginUser
from ..utils.security import authenticate_demo, create_access_token

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    claims = authenticate_demo(payload.username, payload.password)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(claims)
    user = LoginUser(
        username=claims["sub"],
        role=claims["role"],
        user_id=claims.get("user_id"),
        lawyer_id=claims.get("lawyer_id"),
    )
    return LoginResponse(access_token=token, user=user)


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
            result["lawyer_name"] = lawyer.get("name")
            result["specialization_names"] = lawyer.get("specialization_names")
    return result
