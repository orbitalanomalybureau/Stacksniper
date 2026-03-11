"""Tests for Stripe webhook handling with mocked Stripe API."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.user import User


@pytest.mark.asyncio
async def test_webhook_checkout_completed(client, registered_user, db_session):
    """checkout.session.completed webhook should upgrade user tier."""
    # Get user from DB to find the ID
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one()

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user.id), "tier": "pro"},
                "customer": "cus_test123",
                "subscription": "sub_test123",
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        response = await client.post(
            "/api/billing/webhook",
            content=b"fake-payload",
            headers={"stripe-signature": "fake-sig"},
        )
    assert response.status_code == 200

    # Verify user was upgraded
    await db_session.refresh(user)
    assert user.tier == "pro"
    assert user.stripe_customer_id == "cus_test123"
    assert user.stripe_subscription_id == "sub_test123"


@pytest.mark.asyncio
async def test_webhook_subscription_deleted(client, registered_user, db_session):
    """customer.subscription.deleted webhook should downgrade to free."""
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one()
    user.tier = "pro"
    user.stripe_customer_id = "cus_test456"
    user.stripe_subscription_id = "sub_test456"
    await db_session.commit()

    fake_event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": "cus_test456",
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        response = await client.post(
            "/api/billing/webhook",
            content=b"fake-payload",
            headers={"stripe-signature": "fake-sig"},
        )
    assert response.status_code == 200

    await db_session.refresh(user)
    assert user.tier == "free"
    assert user.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    """Invalid Stripe signature should return 400."""
    with patch("stripe.Webhook.construct_event", side_effect=__import__("stripe").error.SignatureVerificationError("bad sig", "sig")):
        response = await client.post(
            "/api/billing/webhook",
            content=b"fake-payload",
            headers={"stripe-signature": "bad-sig"},
        )
    assert response.status_code == 400
    assert "Invalid signature" in response.json()["detail"]
