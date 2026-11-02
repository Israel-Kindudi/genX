# backend/app/routers/auth_router.py
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional

import resend
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature

from ..config import settings
from ..database import get_db
from ..models import (
    User, Plan, Subscription, Invoice,
    PaymentIntent, UsageEvent, AuditLog,
)
from ..schemas import (
    UserCreate, UserOut, UserUpdate,
    UserAdminOut, UserAdminUpdate, UserActivityOut,
    PlanOut, Token, VerifyEmailIn, VerifyEmailOut,
)
from ..auth import (
    get_current_user, create_access_token, verify_password,
    hash_password, require_admin, ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Verification token serializer (for email links) ──
SECRET = os.getenv("JWT_SECRET", "fallback-secret")
serializer = URLSafeTimedSerializer(SECRET, salt="email-verify")

resend.api_key = os.getenv("RESEND_API_KEY")


def send_verification_email(email: str, token: str):
    """Send verification email via Resend, or log to console if not configured."""
    verify_url = f"https://genx.vortech.markets/verify-email?token={token}"

    if not resend.api_key:
        print(f"\n[EMAIL VERIFY] URL: {verify_url}\n", flush=True)
        return

    try:
        resend.Emails.send({
            "from": os.getenv("RESEND_FROM_EMAIL", "GenX <noreply@genx.vortech.markets>"),
            "to": email,
            "subject": "Verify your GenX account",
            "html": f"""
                <h2>Welcome to GenX</h2>
                <p>Click the link below to verify your email address:</p>
                <p><a href="{verify_url}">Verify email</a></p>
                <p>This link expires in 24 hours.</p>
            """,
        })
    except Exception as e:
        print(f"[EMAIL ERROR] {e}", flush=True)
        print(f"[EMAIL VERIFY FALLBACK] URL: {verify_url}", flush=True)


def _plan_out(p: Plan | None) -> PlanOut | None:
    if not p:
        return None
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["features"] = json.loads(p.features_json or "[]")
    return PlanOut(**{k: v for k, v in d.items() if k in PlanOut.model_fields})


# ============================================================
# PUBLIC: Register
# ============================================================
@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    - Sends a verification email.
    - Returns a JWT so the user is logged in immediately.
    - Verification can be completed later by clicking the email link.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")

    is_first_user = db.query(User).count() == 0
    trial_plan = db.query(Plan).filter(Plan.code == "trial").first()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name or "",
        role="admin" if is_first_user else "user",
        is_active=True,
        email_verified=False,
        plan_id=trial_plan.id if trial_plan else None,
        terms_accepted_at=datetime.utcnow() if payload.terms_accepted else None,
        terms_accepted_version=payload.terms_version if payload.terms_accepted else None,
    )
    db.add(user)
    db.flush()

    # Send verification email with signed token
    verify_token = serializer.dumps({"email": user.email})
    send_verification_email(user.email, verify_token)

    # Audit trail
    db.add(AuditLog(
        user_id=user.id,
        actor_id=user.id,
        action="user.register",
        detail=f"role={'admin' if is_first_user else 'user'} terms={payload.terms_accepted}",
    ))

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role})
    return Token(access_token=token, token_type="bearer")


# ============================================================
# PUBLIC: Verify Email
# ============================================================
@router.post("/verify-email", response_model=VerifyEmailOut)
def verify_email_post(payload: VerifyEmailIn, db: Session = Depends(get_db)):
    """Verify email via signed token (called from frontend POST)."""
    try:
        data = serializer.loads(payload.token, max_age=86400)  # 24h
    except BadSignature:
        raise HTTPException(400, "Invalid or expired token")

    email = data.get("email")
    if not email:
        raise HTTPException(400, "Token missing email claim")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.add(AuditLog(
            user_id=user.id,
            actor_id=user.id,
            action="user.email_verified",
            detail=f"Verified {email}",
        ))
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role})
    return VerifyEmailOut(access_token=token, message="Email verified successfully")


@router.get("/verify-email")
def verify_email_get(token: str, db: Session = Depends(get_db)):
    """Verify email via GET (for direct email link clicks)."""
    try:
        data = serializer.loads(token, max_age=86400)
    except BadSignature:
        raise HTTPException(400, "Invalid or expired token")

    user = db.query(User).filter(User.email == data["email"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.commit()

    return {"message": "Email verified successfully"}


# ============================================================
# PUBLIC: Login
# ============================================================
@router.post("/token", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not user.hashed_password:
        raise HTTPException(401, "Invalid credentials")
    if not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")

    # NOTE: We do NOT block login on unverified email — the user gets a
    # banner in the dashboard. Only block actions that require verification.

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.email, "role": user.role})
    return Token(access_token=token, token_type="bearer")


# ============================================================
# AUTHENTICATED: Me
# ============================================================
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ============================================================
# ADMIN: User management
# ============================================================
@router.get("/users", response_model=List[UserAdminOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        UserAdminOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            plan=_plan_out(u.plan),
            last_login=u.last_login,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")

    changes = []

    if payload.role is not None and payload.role != u.role:
        if payload.role not in ("admin", "user", "viewer"):
            raise HTTPException(400, "Invalid role")
        changes.append(f"role {u.role}→{payload.role}")
        u.role = payload.role

    if payload.is_active is not None and payload.is_active != u.is_active:
        changes.append(f"active {u.is_active}→{payload.is_active}")
        u.is_active = payload.is_active

    if payload.full_name is not None:
        u.full_name = payload.full_name

    if payload.plan_code is not None:
        plan = db.query(Plan).filter(Plan.code == payload.plan_code).first()
        if not plan:
            raise HTTPException(400, f"Unknown plan {payload.plan_code}")
        changes.append(f"plan→{plan.code}")
        u.plan_id = plan.id

    if payload.force_verify:
        u.email_verified = True
        u.email_verified_at = datetime.utcnow()
        changes.append("force_verify=True")

    if changes:
        db.add(AuditLog(
            user_id=u.id,
            actor_id=admin.id,
            action="user.update",
            detail="; ".join(changes),
        ))
    db.commit()
    db.refresh(u)

    return UserAdminOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        plan=_plan_out(u.plan),
        last_login=u.last_login,
        created_at=u.created_at,
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")

    db.query(Subscription).filter(Subscription.user_id == u.id).delete()
    db.query(Invoice).filter(Invoice.user_id == u.id).delete()
    db.query(PaymentIntent).filter(PaymentIntent.user_id == u.id).delete()
    db.query(UsageEvent).filter(UsageEvent.user_id == u.id).delete()
    db.query(AuditLog).filter(AuditLog.user_id == u.id).delete()

    email = u.email
    db.delete(u)
    db.add(AuditLog(
        actor_id=admin.id,
        action="user.delete",
        detail=f"Hard deleted user {email}",
    ))
    db.commit()
    return {"ok": True}


@router.get("/users/{user_id}/activity", response_model=List[UserActivityOut])
def user_activity(
    user_id: int,
    limit: int = 50,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog)
          .filter(AuditLog.user_id == user_id)
          .order_by(AuditLog.created_at.desc())
          .limit(limit)
          .all()
    )