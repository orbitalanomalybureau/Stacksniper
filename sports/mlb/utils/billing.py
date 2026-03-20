"""STACKSNIPER MLB — Stripe Billing Integration"""
import os

import stripe

from sports.mlb.data.database import db
from sports.mlb.utils.logger import get_logger

log = get_logger("Billing")

# ── Stripe configuration ─────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs — configured via environment variables
PRICE_IDS = {
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
    "elite": os.getenv("STRIPE_PRICE_ELITE", "price_elite_placeholder"),
    "season_pass": os.getenv("STRIPE_PRICE_SEASON", "price_season_placeholder"),
}

# Tier mapped from price ID (reverse lookup)
_PRICE_TO_TIER = {}


def _build_price_map():
    """Build the reverse price→tier lookup (called lazily)."""
    global _PRICE_TO_TIER
    _PRICE_TO_TIER = {v: k for k, v in PRICE_IDS.items()}


# ── Checkout ─────────────────────────────────────────────────────────

def create_checkout_session(user: dict, price_id: str, trial_days: int = 0) -> dict:
    """Create a Stripe Checkout session and return ``{"url": …}`` or ``{"error": …}``."""
    if not stripe.api_key:
        return {"error": "Stripe is not configured."}

    customer_id = user.get("stripe_customer_id")

    # Create Stripe customer if needed
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            metadata={"stacksniper_user_id": user["id"]},
        )
        customer_id = customer.id
        db.update_user(user["id"], stripe_customer_id=customer_id)

    # Determine mode: subscription for pro/elite, payment for season_pass
    is_season_pass = price_id == PRICE_IDS.get("season_pass")
    mode = "payment" if is_season_pass else "subscription"

    _base = os.getenv("APP_BASE_URL", "http://localhost:3333")
    session_params = {
        "customer": customer_id,
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": mode,
        "success_url": os.getenv("STRIPE_SUCCESS_URL", f"{_base}/dashboard?session_id={{CHECKOUT_SESSION_ID}}"),
        "cancel_url": os.getenv("STRIPE_CANCEL_URL", f"{_base}/pricing"),
        "metadata": {"user_id": str(user["id"])},
    }

    # Add trial period for subscriptions
    if not is_season_pass and trial_days > 0:
        session_params["subscription_data"] = {"trial_period_days": trial_days}

    try:
        session = stripe.checkout.Session.create(**session_params)
        log.info(f"Checkout session created for user {user['id']}: {session.id}")
        return {"url": session.url, "session_id": session.id}
    except stripe.error.StripeError as exc:
        log.error(f"Stripe checkout error: {exc}")
        return {"error": str(exc)}


# ── Webhook ──────────────────────────────────────────────────────────

def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify and process a Stripe webhook event. Returns ``{"status": …}``."""
    if not WEBHOOK_SECRET:
        log.warning("Stripe webhook secret not configured")
        return {"status": "ignored", "reason": "webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        log.warning("Webhook signature verification failed")
        return {"status": "error", "reason": "invalid signature"}
    except ValueError:
        log.warning("Invalid webhook payload")
        return {"status": "error", "reason": "invalid payload"}

    event_type = event["type"]
    data_obj = event["data"]["object"]
    log.info(f"Webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_obj)

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_update(data_obj)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_obj)

    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data_obj)

    return {"status": "ok", "event_type": event_type}


def _handle_checkout_completed(session: dict):
    """Process a completed checkout session."""
    customer_id = session.get("customer")
    user = _find_user_by_customer(customer_id)
    if not user:
        log.warning(f"No user found for customer {customer_id}")
        return

    # For one-time payments (season pass), upgrade immediately
    if session.get("mode") == "payment":
        db.update_user(user["id"], tier="elite", subscription_status="season_pass")
        log.info(f"User {user['id']} upgraded to elite (season pass)")


def _handle_subscription_update(subscription: dict):
    """Process subscription creation or update."""
    customer_id = subscription.get("customer")
    user = _find_user_by_customer(customer_id)
    if not user:
        log.warning(f"No user found for customer {customer_id}")
        return

    status = subscription.get("status", "")
    price_id = ""
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")

    # Determine tier from price
    if not _PRICE_TO_TIER:
        _build_price_map()
    tier = _PRICE_TO_TIER.get(price_id, "pro")
    if tier == "season_pass":
        tier = "elite"

    if status in ("active", "trialing"):
        db.update_user(user["id"], tier=tier, subscription_status=status)
        log.info(f"User {user['id']} subscription updated: tier={tier} status={status}")
    elif status in ("past_due", "unpaid"):
        db.update_user(user["id"], subscription_status=status)
        log.info(f"User {user['id']} subscription past_due/unpaid")


def _handle_subscription_deleted(subscription: dict):
    """Process subscription cancellation."""
    customer_id = subscription.get("customer")
    user = _find_user_by_customer(customer_id)
    if not user:
        return
    db.update_user(user["id"], tier="free", subscription_status="canceled")
    log.info(f"User {user['id']} subscription canceled, downgraded to free")


def _handle_payment_failed(invoice: dict):
    """Process a failed payment."""
    customer_id = invoice.get("customer")
    user = _find_user_by_customer(customer_id)
    if not user:
        return
    db.update_user(user["id"], subscription_status="past_due")
    log.info(f"User {user['id']} payment failed, marked past_due")


# ── Subscription management ─────────────────────────────────────────

def get_subscription(user: dict) -> dict:
    """Return the current subscription status for a user."""
    result = {
        "tier": user.get("tier", "free"),
        "status": user.get("subscription_status", "none"),
        "stripe_customer_id": user.get("stripe_customer_id"),
    }

    customer_id = user.get("stripe_customer_id")
    if customer_id and stripe.api_key:
        try:
            subscriptions = stripe.Subscription.list(customer=customer_id, status="all", limit=1)
            if subscriptions.data:
                sub = subscriptions.data[0]
                result["subscription_id"] = sub.id
                result["current_period_end"] = sub.current_period_end
                result["cancel_at_period_end"] = sub.cancel_at_period_end
                result["trial_end"] = sub.trial_end
        except stripe.error.StripeError as exc:
            log.warning(f"Error fetching subscription: {exc}")

    return result


def cancel_subscription(user: dict) -> dict:
    """Cancel the user's active subscription at period end."""
    customer_id = user.get("stripe_customer_id")
    if not customer_id or not stripe.api_key:
        return {"error": "No active subscription found."}

    try:
        subscriptions = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
        if not subscriptions.data:
            # Also check trialing
            subscriptions = stripe.Subscription.list(customer=customer_id, status="trialing", limit=1)
        if not subscriptions.data:
            return {"error": "No active subscription found."}

        sub = subscriptions.data[0]
        updated = stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
        log.info(f"User {user['id']} subscription set to cancel at period end")
        return {
            "status": "canceling",
            "cancel_at_period_end": True,
            "current_period_end": updated.current_period_end,
        }
    except stripe.error.StripeError as exc:
        log.error(f"Cancel subscription error: {exc}")
        return {"error": str(exc)}


def create_portal_session(user: dict) -> dict:
    """Create a Stripe Customer Portal session so the user can manage billing."""
    customer_id = user.get("stripe_customer_id")
    if not customer_id or not stripe.api_key:
        return {"error": "No Stripe customer found. Subscribe first."}

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=os.getenv("STRIPE_PORTAL_RETURN_URL", os.getenv("APP_BASE_URL", "http://localhost:3333") + "/dashboard"),
        )
        return {"url": session.url}
    except stripe.error.StripeError as exc:
        log.error(f"Portal session error: {exc}")
        return {"error": str(exc)}


# ── Internal helpers ─────────────────────────────────────────────────

def _find_user_by_customer(customer_id: str) :
    """Look up a user by their Stripe customer ID."""
    if not customer_id:
        return None
    # Search via raw query since we don't have a dedicated method
    import sqlite3
    from sports.mlb.data.database import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
