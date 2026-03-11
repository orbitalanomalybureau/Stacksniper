from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponse, TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(user_data: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.register(user_data)
    if not result:
        raise HTTPException(status_code=400, detail="Email already registered")
    user, access_token, refresh_token = result
    _set_refresh_cookie(response, refresh_token)
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(user_data: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.login(user_data)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user, access_token, refresh_token = result
    _set_refresh_cookie(response, refresh_token)
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = AuthService.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    new_access = AuthService._create_token(
        str(user.id),
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        tier=user.tier,
    )
    new_refresh = AuthService._create_token(
        str(user.id),
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        tier=user.tier,
    )
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
