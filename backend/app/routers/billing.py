from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import CheckoutRequest
from app.services.stripe_service import StripeService

router = APIRouter()


@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.tier not in ("pro", "elite"):
        raise HTTPException(status_code=400, detail="Invalid tier")
    service = StripeService(db)
    url = await service.create_checkout_session(
        user_id=str(user.id),
        user_email=user.email,
        tier=body.tier,
    )
    if not url:
        raise HTTPException(status_code=400, detail="Could not create checkout session")
    return {"url": url}


@router.post("/portal-session")
async def create_portal_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    service = StripeService(db)
    url = await service.create_portal_session(user.stripe_customer_id)
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    service = StripeService(db)
    result = await service.handle_webhook(payload, sig_header)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"received": True}


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_user),
):
    return {
        "tier": user.tier,
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_subscription_id": user.stripe_subscription_id,
    }
