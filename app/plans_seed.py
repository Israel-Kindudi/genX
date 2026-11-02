# ============================================================
# backend/app/plans_seed.py  — GenX 5-tier plan catalogue
# ============================================================
import json
from sqlalchemy.orm import Session
from .models import Plan


DEFAULT_PLANS = [
    # ------------------------------------------------------------------
    # TRIAL
    # ------------------------------------------------------------------
    {
        "code": "trial",
        "name": "Trial",
        "description": "Try the platform risk-free.",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "currency": "USD",

        "max_cycles": 100,
        "cycles_expire": True,
        "trial_days": 30,

        "max_mt5_accounts": 1,
        "max_symbols": 2,
        "max_strategies": 2,
        "all_symbols_visible": True,
        "all_strategies_visible": True,

        "max_account_equity": 1000.0,

        "max_live_sessions": 1,
        "max_backtests_per_day": 50,
        "max_mining_runs": 0,

        "allow_ml_filter": False,
        "allow_regime_detection": False,
        "allow_api_access": False,
        "allow_multi_terminal": False,

        "support_response_hours": 72,
        "latency_tier": "best_effort",
        "api_access": "none",
        "custom_risk_rails": False,
        "early_access_symbols": False,
        "signal_channel": False,
        "custom_hub": False,
        "white_label": False,
        "dedicated_infrastructure": False,

        "features_json": json.dumps([
            "100 cycles (30-day expiry)",
            "1 MT5 account",
            "All symbols & strategies visible",
            "Mirror 2 symbols at a time",
            "Equity cap $1,000",
            "Community support",
        ]),
        "sort_order": 0,
    },

    # ------------------------------------------------------------------
    # STARTER
    # ------------------------------------------------------------------
    {
        "code": "starter",
        "name": "Starter",
        "description": "For individual traders getting serious.",
        "price_monthly": 49.0,
        "price_yearly": 490.0,
        "currency": "USD",

        "max_cycles": 1000,
        "cycles_expire": False,
        "trial_days": None,

        "max_mt5_accounts": 1,
        "max_symbols": 5,
        "max_strategies": 3,
        "all_symbols_visible": True,
        "all_strategies_visible": True,

        "max_account_equity": 5000.0,

        "max_live_sessions": 1,
        "max_backtests_per_day": 200,
        "max_mining_runs": 5,

        "allow_ml_filter": False,
        "allow_regime_detection": False,
        "allow_api_access": False,
        "allow_multi_terminal": False,

        "support_response_hours": 48,
        "latency_tier": "standard",
        "api_access": "none",
        "custom_risk_rails": False,
        "early_access_symbols": False,
        "signal_channel": False,
        "custom_hub": False,
        "white_label": False,
        "dedicated_infrastructure": False,

        "features_json": json.dumps([
            "1,000 cycles (never expire)",
            "1 MT5 account",
            "Mirror 5 symbols",
            "Mirror 3 strategies",
            "Equity cap $5,000 (per account)",
            "Standard latency",
            "48h support response",
        ]),
        "sort_order": 1,
    },

    # ------------------------------------------------------------------
    # PRO  ⭐ featured
    # ------------------------------------------------------------------
    {
        "code": "pro",
        "name": "Pro",
        "description": "The full GenX research engine.",
        "price_monthly": 119.0,
        "price_yearly": 1190.0,
        "currency": "USD",

        "max_cycles": 5000,
        "cycles_expire": False,
        "trial_days": None,

        "max_mt5_accounts": 3,
        "max_symbols": 999,
        "max_strategies": 99,
        "all_symbols_visible": True,
        "all_strategies_visible": True,

        "max_account_equity": 50000.0,

        "max_live_sessions": 3,
        "max_backtests_per_day": 1000,
        "max_mining_runs": 20,

        "allow_ml_filter": True,
        "allow_regime_detection": True,
        "allow_api_access": False,
        "allow_multi_terminal": True,

        "support_response_hours": 24,
        "latency_tier": "priority",
        "api_access": "read_only",
        "custom_risk_rails": True,
        "early_access_symbols": False,
        "signal_channel": False,
        "custom_hub": False,
        "white_label": False,
        "dedicated_infrastructure": False,

        "features_json": json.dumps([
            "5,000 cycles",
            "Up to 3 MT5 accounts",
            "All symbols, all strategies",
            "Equity cap $50,000 per account",
            "Priority latency",
            "24h support response",
            "Read-only API",
            "Custom risk rails",
        ]),
        "sort_order": 2,
    },

    # ------------------------------------------------------------------
    # FIRM
    # ------------------------------------------------------------------
    {
        "code": "firm",
        "name": "Firm",
        "description": "For funded traders and small desks.",
        "price_monthly": 299.0,
        "price_yearly": 2990.0,
        "currency": "USD",

        "max_cycles": 15000,
        "cycles_expire": False,
        "trial_days": None,

        "max_mt5_accounts": 10,
        "max_symbols": 999,
        "max_strategies": 99,
        "all_symbols_visible": True,
        "all_strategies_visible": True,

        "max_account_equity": 0.0,

        "max_live_sessions": 10,
        "max_backtests_per_day": 999999,
        "max_mining_runs": 999999,

        "allow_ml_filter": True,
        "allow_regime_detection": True,
        "allow_api_access": True,
        "allow_multi_terminal": True,

        "support_response_hours": 4,
        "latency_tier": "priority",
        "api_access": "full",
        "custom_risk_rails": True,
        "early_access_symbols": True,
        "signal_channel": True,
        "custom_hub": True,
        "white_label": False,
        "dedicated_infrastructure": False,

        "features_json": json.dumps([
            "15,000 cycles",
            "Up to 10 MT5 accounts",
            "All symbols + early access",
            "Dedicated signal channel",
            "Full API",
            "4h support response",
            "Custom hub available",
            "Unlimited account equity",
        ]),
        "sort_order": 3,
    },

    # ------------------------------------------------------------------
    # FIRM XL  🏛 enterprise
    # ------------------------------------------------------------------
    {
        "code": "firm_xl",
        "name": "Firm XL",
        "description": "White-label infrastructure for prop firms.",
        "price_monthly": 1299.0,
        "price_yearly": 12990.0,
        "currency": "USD",

        "max_cycles": 50000,
        "cycles_expire": False,
        "trial_days": None,

        "max_mt5_accounts": 999,
        "max_symbols": 999,
        "max_strategies": 99,
        "all_symbols_visible": True,
        "all_strategies_visible": True,

        "max_account_equity": 0.0,

        "max_live_sessions": 999,
        "max_backtests_per_day": 999999,
        "max_mining_runs": 999999,

        "allow_ml_filter": True,
        "allow_regime_detection": True,
        "allow_api_access": True,
        "allow_multi_terminal": True,

        "support_response_hours": 1,
        "latency_tier": "dedicated",
        "api_access": "full",
        "custom_risk_rails": True,
        "early_access_symbols": True,
        "signal_channel": True,
        "custom_hub": True,
        "white_label": True,
        "dedicated_infrastructure": True,

        "features_json": json.dumps([
            "50,000 cycles",
            "Unlimited MT5 accounts",
            "White-label option",
            "Dedicated infrastructure",
            "Full API + webhooks",
            "1h support response",
            "Custom hub",
            "Volume pricing",
        ]),
        "sort_order": 4,
    },
]


def seed_plans(db: Session) -> None:
    """Idempotent — creates missing plans, updates existing ones."""
    for spec in DEFAULT_PLANS:
        existing = db.query(Plan).filter(Plan.code == spec["code"]).first()
        if not existing:
            db.add(Plan(**spec))
        else:
            for k, v in spec.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
    db.commit()