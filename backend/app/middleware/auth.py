from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = AuthService.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_effective_tier(user: User) -> str:
    if user.tier != "free":
        return user.tier
    if user.trial_expires_at:
        trial = user.trial_expires_at
        now = datetime.now(timezone.utc)
        # Handle naive datetimes from SQLite
        if trial.tzinfo is None:
            trial = trial.replace(tzinfo=timezone.utc)
        if trial > now:
            return "pro"
    return "free"


def require_tier(min_tier: str):
    tier_levels = {"free": 0, "pro": 1, "elite": 2}

    async def check_tier(user: User = Depends(get_current_user)) -> User:
        if tier_levels.get(get_effective_tier(user), 0) < tier_levels.get(min_tier, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_tier} tier or higher",
            )
        return user

    return check_tier
