# ============================================================
# backend/app/routers/subscriptions_router.py  — GenX
# ============================================================
import json
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Plan, Subscription, UsageEvent, AuditLog, Invoice
from ..schemas import (
    PlanOut, SubscriptionOut, ChangePlanIn,
    MeSubscriptionOut, UsageOut, InvoiceOut,
)
from ..auth import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _plan_to_out(p: Plan) -> PlanOut:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["features"] = json.loads(p.features_json or "[]")
    return PlanOut(**{k: v for k, v in d.items() if k in PlanOut.model_fields})


def _usage_for_user(db: Session, user_id: int) -> UsageOut:
    month_start = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    def _count(kind: str) -> int:
        return (
            db.query(func.coalesce(func.sum(UsageEvent.units), 0))
              .filter(
                  UsageEvent.user_id == user_id,
                  UsageEvent.kind == kind,
                  UsageEvent.created_at >= month_start,
              )
              .scalar()
            or 0
        )

    return UsageOut(
        live_sessions=_count("live_session"),
        backtests=_count("backtest"),
        mining_runs=_count("mining_run"),
        optimizations=_count("optimization"),
    )


# ---------------------------------------------------------------
# Plans
# ---------------------------------------------------------------
@router.get("/plans", response_model=List[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    plans = (
        db.query(Plan)
          .filter(Plan.is_active == True)  # noqa: E712
          .order_by(Plan.sort_order.asc())
          .all()
    )
    return [_plan_to_out(p) for p in plans]


# ---------------------------------------------------------------
# Me
# ---------------------------------------------------------------
@router.get("/me", response_model=MeSubscriptionOut)
def my_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = user.plan or db.query(Plan).filter(Plan.code == "trial").first()

    sub = (
        db.query(Subscription)
          .filter(Subscription.user_id == user.id)
          .order_by(Subscription.id.desc())
          .first()
    )
    sub_out = None
    if sub:
        sub_out = SubscriptionOut(
            id=sub.id,
            status=sub.status,
            started_at=sub.started_at,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            plan=_plan_to_out(sub.plan) if sub.plan else None,
        )

    return MeSubscriptionOut(
        user_id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        plan=_plan_to_out(plan) if plan else None,
        subscription=sub_out,
        usage=_usage_for_user(db, user.id),
    )


@router.get("/usage", response_model=UsageOut)
def my_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _usage_for_user(db, user.id)


# ---------------------------------------------------------------
# Change / cancel
# ---------------------------------------------------------------
@router.post("/change", response_model=SubscriptionOut)
def change_plan(
    payload: ChangePlanIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the current user's plan.

    Steps:
      1. Validate target plan exists.
      2. Cancel any active subscription.
      3. Create a new subscription with a fresh billing period.
      4. Update user.plan_id.
      5. Create an invoice for the new plan (if amount > 0).
      6. Write an audit log entry.
      7. Return the new subscription.
    """
    if payload.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(400, "billing_cycle must be 'monthly' or 'yearly'")

    plan = db.query(Plan).filter(Plan.code == payload.plan_code).first()
    if not plan:
        raise HTTPException(404, f"Plan '{payload.plan_code}' not found")
    if not plan.is_active:
        raise HTTPException(400, f"Plan '{plan.code}' is not available")

    now = datetime.utcnow()

    # cancel any active subscription
    db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status.in_(["active", "trialing", "past_due"]),
    ).update(
        {"status": "canceled", "cancel_at_period_end": False},
        synchronize_session=False,
    )

    # new subscription
    period_days = 365 if payload.billing_cycle == "yearly" else 30
    period_end = now + timedelta(days=period_days)

    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        started_at=now,
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    db.add(sub)
    db.flush()

    # update user
    user.plan_id = plan.id

    # invoice
    amount = (
        plan.price_yearly
        if payload.billing_cycle == "yearly"
        else plan.price_monthly
    )
    if amount > 0:
        db.add(Invoice(
            user_id=user.id,
            subscription_id=sub.id,
            amount=amount,
            currency=plan.currency or "USD",
            status="paid",
            description=f"{plan.name} plan ({payload.billing_cycle})",
            period_start=now,
            period_end=period_end,
        ))

    # audit
    db.add(AuditLog(
        user_id=user.id,
        actor_id=user.id,
        action="plan.change",
        detail=f"Changed to {plan.code} ({payload.billing_cycle}), amount=${amount:.2f}",
    ))

    db.commit()
    db.refresh(sub)
    db.refresh(user)

    return SubscriptionOut(
        id=sub.id,
        status=sub.status,
        started_at=sub.started_at,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        plan=_plan_to_out(plan),
    )


@router.post("/cancel", response_model=SubscriptionOut)
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = (
        db.query(Subscription)
          .filter(
              Subscription.user_id == user.id,
              Subscription.status.in_(["active", "trialing"]),
          )
          .order_by(Subscription.id.desc())
          .first()
    )
    if not sub:
        raise HTTPException(404, "No active subscription")

    sub.cancel_at_period_end = True
    db.add(AuditLog(
        user_id=user.id,
        actor_id=user.id,
        action="plan.cancel",
        detail="Cancel at period end",
    ))
    db.commit()
    db.refresh(sub)

    return SubscriptionOut(
        id=sub.id,
        status=sub.status,
        started_at=sub.started_at,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        plan=_plan_to_out(sub.plan) if sub.plan else None,
    )


# ---------------------------------------------------------------
# Usage recording
# ---------------------------------------------------------------
@router.post("/usage/record")
def record_usage(
    kind: str,
    units: int = 1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ev = UsageEvent(user_id=user.id, kind=kind, units=units)
    db.add(ev)
    db.commit()
    return {"ok": True, "kind": kind, "units": units}


# ---------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------
@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Invoice)
          .filter(Invoice.user_id == user.id)
          .order_by(Invoice.issued_at.desc())
          .all()
    )
    return rows
# ============================================================
# Public router — no auth required
# ============================================================
public_router = APIRouter(prefix="/api/public", tags=["public"])


@public_router.get("/plans", response_model=List[PlanOut])
def public_plans(db: Session = Depends(get_db)):
    """Public plans list — used by the marketing/landing page."""
    plans = (
        db.query(Plan)
          .filter(Plan.is_active == True)  # noqa: E712
          .order_by(Plan.sort_order.asc())
          .all()
    )
    return [_plan_to_out(p) for p in plans]