"""Stripe billing integration for subscription management."""

from __future__ import annotations

import logging
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

TIER_PRICE_MAP = {
    "pro": settings.STRIPE_PRICE_PRO_MONTHLY,
    "elite": settings.STRIPE_PRICE_ELITE_MONTHLY,
}

PRICE_TIER_MAP = {v: k for k, v in TIER_PRICE_MAP.items() if v}


class StripeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_checkout_session(
        self, user_id: str, user_email: str, tier: str
    ) -> Optional[str]:
        price_id = TIER_PRICE_MAP.get(tier)
        if not price_id:
            return None
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.CORS_ORIGINS}/dashboard?upgrade=success",
            cancel_url=f"{settings.CORS_ORIGINS}/pricing?canceled=true",
            metadata={"user_id": user_id, "tier": tier},
        )
        return session.url

    async def create_portal_session(self, stripe_customer_id: str) -> Optional[str]:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{settings.CORS_ORIGINS}/dashboard",
        )
        return session.url

    async def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return {"error": "Invalid signature"}

        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data_object)

        return {"type": event_type, "handled": True}

    async def _handle_checkout_completed(self, session: dict) -> None:
        user_id = session.get("metadata", {}).get("user_id")
        tier = session.get("metadata", {}).get("tier", "pro")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        if not user_id:
            return
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        user.tier = tier
        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.trial_expires_at = None
        await self.db.commit()

    async def _handle_subscription_updated(self, subscription: dict) -> None:
        customer_id = subscription.get("customer")
        if not customer_id:
            return
        result = await self.db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
            new_tier = PRICE_TIER_MAP.get(price_id, user.tier)
            user.tier = new_tier
        if subscription.get("status") != "active":
            user.tier = "free"
        await self.db.commit()

    async def _handle_subscription_deleted(self, subscription: dict) -> None:
        customer_id = subscription.get("customer")
        if not customer_id:
            return
        result = await self.db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        user.tier = "free"
        user.stripe_subscription_id = None
        await self.db.commit()

    async def _handle_payment_failed(self, invoice: dict) -> None:
        customer_id = invoice.get("customer")
        if not customer_id:
            return
        logger.warning("Payment failed for customer %s", customer_id)
