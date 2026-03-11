from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_checkout_requires_auth(client):
    response = await client.post("/api/billing/create-checkout-session", json={"tier": "pro"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_checkout_invalid_tier(client, auth_headers):
    response = await client.post(
        "/api/billing/create-checkout-session",
        json={"tier": "invalid"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_subscription_requires_auth(client):
    response = await client.get("/api/billing/subscription")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_subscription_returns_tier(client, auth_headers):
    response = await client.get("/api/billing/subscription", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "free"


@pytest.mark.asyncio
async def test_portal_session_requires_subscription(client, auth_headers):
    response = await client.post("/api/billing/portal-session", headers=auth_headers)
    assert response.status_code == 400
    assert "No active subscription" in response.json()["detail"]
