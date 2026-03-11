from __future__ import annotations

import os

os.environ["USE_SQLITE_MEMORY"] = "true"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import async_session, engine
from app.models.user import Base, User
from app.services.auth_service import AuthService, pwd_context

# Import all models so metadata registers them
import app.models  # noqa: F401

from app.main import app
from app.middleware.rate_limit import limiter


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after. Reset rate limiter."""
    # Reset rate limiter storage between tests
    limiter.reset()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """Provide a raw DB session for direct model manipulation in tests."""
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def registered_user(client):
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "display_name": "Test User",
    })
    return resp.json()


@pytest_asyncio.fixture
async def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


async def _create_user_with_tier(tier: str, email: str = None):
    """Helper to create a user with a specific tier and return auth headers."""
    if email is None:
        email = f"{tier}@example.com"
    async with async_session() as session:
        user = User(
            email=email,
            hashed_password=pwd_context.hash("testpass123"),
            display_name=f"{tier.title()} User",
            tier=tier,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        from datetime import timedelta
        token = AuthService._create_token(str(user.id), timedelta(minutes=30), tier=tier)
        return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def pro_auth_headers():
    return await _create_user_with_tier("pro")


@pytest_asyncio.fixture
async def elite_auth_headers():
    return await _create_user_with_tier("elite")
