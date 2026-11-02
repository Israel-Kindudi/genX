from functools import lru_cache
from .data_loader import GenXDataLoader
from .config import settings

# ============================================================
# Append to backend/app/dependencies.py
# ============================================================
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Plan
from .auth import get_current_user  # your existing dep


def require_active(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Account is suspended. Contact support.")
    return user


def require_plan(*codes: str):
    """Usage: user = Depends(require_plan('pro','elite'))"""
    def _dep(user: User = Depends(require_active), db: Session = Depends(get_db)):
        plan_code = user.plan.code if user.plan else "free"
        if plan_code not in codes:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This feature requires plan: {', '.join(codes)}. "
                f"Current plan: {plan_code}.",
            )
        return user
    return _dep


def get_user_plan(user: User, db: Session) -> Plan:
    if user.plan:
        return user.plan
    return db.query(Plan).filter(Plan.code == "free").first()

@lru_cache()
def get_loader() -> GenXDataLoader:
    return GenXDataLoader(settings.genx_root)