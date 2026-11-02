# ============================================================
# backend/app/models.py  — GenX
# ============================================================
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


# ---------- Users ----------
# ============================================================
# backend/app/models.py  — GenX
# ============================================================
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, Text,
)
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    full_name       = Column(String, nullable=True)
    
    # Allow nullable password for OAuth users
    hashed_password = Column(String, nullable=True) 

    # NEW FIELDS
    phone_number    = Column(String, nullable=True)
    country         = Column(String, nullable=True)
    is_verified     = Column(Boolean, default=False)
    auth_provider   = Column(String, default="local") # "local" or "google"

    role            = Column(String, default="user")
    is_active       = Column(Boolean, default=True)
    email_verified         = Column(Boolean, default=False)   # <-- ADD if missing
    email_verified_at      = Column(DateTime, nullable=True) 
    plan_id         = Column(Integer, ForeignKey("plans.id"), nullable=True)
    last_login      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Terms acceptance record
    terms_accepted_at       = Column(DateTime, nullable=True)
    terms_accepted_version  = Column(String, nullable=True)

    # Relationships (cleaned up duplicates)
    plan          = relationship("Plan", lazy="joined")
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )

# ... (Leave Plan, Subscription, Invoice, UsageEvent, AuditLog unchanged) ...


# ---------- Plans ----------
class Plan(Base):
    __tablename__ = "plans"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String, unique=True, index=True)
    name        = Column(String)
    description = Column(String, default="")

    price_monthly = Column(Float, default=0.0)
    price_yearly  = Column(Float, default=0.0)
    currency      = Column(String, default="USD")

    # ----- cycle-based -----
    max_cycles    = Column(Integer, default=100)
    cycles_expire = Column(Boolean, default=True)
    trial_days    = Column(Integer, nullable=True)

    # ----- broker / mirroring -----
    max_mt5_accounts       = Column(Integer, default=1)
    max_symbols            = Column(Integer, default=2)
    max_strategies         = Column(Integer, default=1)
    all_symbols_visible    = Column(Boolean, default=True)
    all_strategies_visible = Column(Boolean, default=True)

    # ----- equity -----
    max_account_equity = Column(Float, default=0.0)   # 0 = unlimited

    # ----- legacy limits (kept so other routers don't break) -----
    max_live_sessions     = Column(Integer, default=1)
    max_backtests_per_day = Column(Integer, default=50)
    max_mining_runs       = Column(Integer, default=0)

    # ----- feature flags -----
    allow_ml_filter        = Column(Boolean, default=False)
    allow_regime_detection = Column(Boolean, default=False)
    allow_api_access       = Column(Boolean, default=False)
    allow_multi_terminal   = Column(Boolean, default=False)

    # ----- extras -----
    support_response_hours   = Column(Integer, default=72)
    latency_tier             = Column(String, default="best_effort")   # best_effort | standard | priority | dedicated
    api_access               = Column(String, default="none")          # none | read_only | full
    custom_risk_rails        = Column(Boolean, default=False)
    early_access_symbols     = Column(Boolean, default=False)
    signal_channel           = Column(Boolean, default=False)
    custom_hub               = Column(Boolean, default=False)
    white_label              = Column(Boolean, default=False)
    dedicated_infrastructure = Column(Boolean, default=False)

    features_json = Column(Text, default="[]")
    is_active     = Column(Boolean, default=True)
    sort_order    = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)


# ---------- Subscriptions ----------
class Subscription(Base):
    __tablename__ = "subscriptions"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    status               = Column(String, default="active")   # active|past_due|canceled|trialing
    started_at           = Column(DateTime, default=datetime.utcnow)
    current_period_end   = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)

    external_ref = Column(String, nullable=True)
    meta_json    = Column(Text, default="{}")

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", lazy="joined")


# ---------- Invoices ----------
class Invoice(Base):
    __tablename__ = "invoices"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    amount      = Column(Float, default=0.0)
    currency    = Column(String, default="USD")
    status      = Column(String, default="paid")     # paid | pending | failed | refunded
    description = Column(String, default="")

    period_start = Column(DateTime, nullable=True)
    period_end   = Column(DateTime, nullable=True)
    issued_at    = Column(DateTime, default=datetime.utcnow, index=True)
    external_ref = Column(String, nullable=True)


# ---------- Usage Events ----------
class UsageEvent(Base):
    __tablename__ = "usage_events"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    kind       = Column(String, index=True)    # live_session | backtest | optimization | mining_run | cycle
    units      = Column(Integer, default=1)
    detail     = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ---------- Audit Log ----------
class AuditLog(Base):
    __tablename__ = "audit_log"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    action     = Column(String, index=True)
    detail     = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # ============================================================
# Payment Intents (mobile money + card checkout)
# ============================================================
class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    plan_id       = Column(Integer, ForeignKey("plans.id"), nullable=False)

    amount        = Column(Float, default=0.0)
    currency      = Column(String, default="USD")
    billing_cycle = Column(String, default="monthly")

    status        = Column(String, default="pending", index=True)
    # pending | requires_action | processing | succeeded | failed | canceled

    provider      = Column(String, default="stub")
    provider_ref  = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, index=True)

    meta_json     = Column(Text, default="{}")

    created_at    = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at  = Column(DateTime, nullable=True)

    user = relationship("User")
    plan = relationship("Plan")

# ---------- Client Bridges (Seam 3: bridge -> user mapping) ----------
class ClientBridge(Base):
    __tablename__ = "client_bridges"

    id         = Column(Integer, primary_key=True, index=True)
    bridge_id  = Column(String, unique=True, index=True, nullable=False)
    token      = Column(String, nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    label      = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen  = Column(DateTime, nullable=True)
