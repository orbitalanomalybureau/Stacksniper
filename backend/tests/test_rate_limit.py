from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_rate_limit_unauthenticated(client):
    """Unauthenticated requests are limited to 10/minute (default_limits)."""
    for _ in range(10):
        await client.get("/health")
    response = await client.get("/health")
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_authenticated_user(client, auth_headers):
    """Authenticated users have their own rate limit bucket (keyed by user ID)."""
    for _ in range(10):
        await client.get("/api/auth/me", headers=auth_headers)
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_separate_buckets(client, auth_headers):
    """Authenticated user has separate bucket from unauthenticated requests."""
    # Exhaust the anonymous bucket
    for _ in range(10):
        await client.get("/health")
    anon_resp = await client.get("/health")
    assert anon_resp.status_code == 429
    # Authenticated user should still have their own bucket
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_response_body(client):
    """429 response should include rate limit exceeded detail."""
    for _ in range(10):
        await client.get("/health")
    response = await client.get("/health")
    assert response.status_code == 429
    data = response.json()
    assert "Rate limit exceeded" in data.get("error", data.get("detail", ""))
