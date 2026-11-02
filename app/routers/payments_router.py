# backend/app/routers/payments_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Literal

from ..database import get_db
from ..models import User, Plan
from ..auth import get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CheckoutIn(BaseModel):
    plan_code: str
    billing_cycle: Literal["monthly", "yearly"]
    payment_method: Literal["card", "mobile_money"]
    provider: Literal["stripe", "flutterwave"]
    email: str
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    mobile_money_provider: Optional[str] = None


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.code == payload.plan_code).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    amount = plan.price_yearly if payload.billing_cycle == "yearly" else plan.price_monthly
    if amount <= 0:
        raise HTTPException(400, "Free plan — no checkout needed")

    # STUB — replace with real Stripe/Flutterwave integration
    # For now, just return a placeholder URL that shows what would happen
    if payload.payment_method == "card":
        return {
            "checkout_url": f"/dashboard?checkout=stub&provider=stripe&amount={amount}",
            "stub": True,
        }
    else:
        return {
            "checkout_url": f"/dashboard?checkout=stub&provider=flutterwave&phone={payload.phone_number}",
            "stub": True,
        }