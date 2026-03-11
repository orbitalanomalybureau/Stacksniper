from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_register_returns_tokens_and_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "display_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["tier"] == "free"
    assert data["user"]["trial_expires_at"] is not None


@pytest.mark.asyncio
async def test_register_duplicate_email(client, registered_user):
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "another123",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    response = await client.post("/api/auth/register", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["tier"] == "free"
    assert data["trial_expires_at"] is not None


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
