from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> Optional[Tuple[User, str, str]]:
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            return None
        user = User(
            email=data.email,
            hashed_password=pwd_context.hash(data.password),
            display_name=data.display_name,
            trial_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        access_token = self._create_token(
            str(user.id),
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            tier=user.tier,
        )
        refresh_token = self._create_token(
            str(user.id),
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            tier=user.tier,
        )
        return user, access_token, refresh_token

    async def login(self, data: UserLogin) -> Optional[Tuple[User, str, str]]:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(data.password, user.hashed_password):
            return None
        access_token = self._create_token(
            str(user.id),
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            tier=user.tier,
        )
        refresh_token = self._create_token(
            str(user.id),
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            tier=user.tier,
        )
        return user, access_token, refresh_token

    @staticmethod
    def _create_token(sub: str, expires_delta: timedelta, tier: str = "free") -> str:
        expire = datetime.now(timezone.utc) + expires_delta
        return jwt.encode(
            {"sub": sub, "exp": expire, "tier": tier},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.JWTError:
            return None
