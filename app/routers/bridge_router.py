"""
bridge_router.py — client bridge onboarding + telemetry ingest (Seam 3, step 2/4).

  POST /api/bridge/register -> requires user JWT (require_active); creates a
                               client_bridges row (bridge_id -> user_id) and
                               returns {bridge_id, token}.
  POST /api/bridge/sync     -> requires X-Bridge-Token; validates against the
                               client_bridges row (DB, not memory); writes
                               <backend>/client_results/{bridge_id}/performance.json.

Anchored to this file's location. backend/app/routers/bridge_router.py:
parents[0]=routers, [1]=app, [2]=backend. NOT settings.genx_root.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import require_active
from ..database import get_db
from ..models import ClientBridge, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["bridge"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]   # .../genx_website/backend
CLIENT_RESULTS_ROOT = BACKEND_ROOT / "client_results"
logger.info(f"[bridge] client_results anchor: {CLIENT_RESULTS_ROOT}")


class RegisterIn(BaseModel):
    label: str = Field(default="", max_length=120)


class RegisterOut(BaseModel):
    bridge_id: str
    token: str


class Position(BaseModel):
    ticket: int
    symbol: str
    action: str
    pnl: float = 0.0


class SyncIn(BaseModel):
    bridge_id: str
    equity: float
    balance: float
    open_positions: int = 0
    positions: list[Position] = []
    initial_capital: float = 0.0
    currency: str = "USD"
    latency_ms: int | None = None
    engine_connected: bool = True


def _require_bridge(db: Session, bridge_id: str, token: str | None) -> ClientBridge:
    if token is None:
        raise HTTPException(status_code=401, detail="missing bridge token")
    row = db.query(ClientBridge).filter(ClientBridge.bridge_id == bridge_id).first()
    if row is None or not secrets.compare_digest(row.token, token):
        raise HTTPException(status_code=403, detail="unknown bridge or bad token")
    return row


@router.post("/register", response_model=RegisterOut)
def register(
    body: RegisterIn,
    user: User = Depends(require_active),
    db: Session = Depends(get_db),
) -> RegisterOut:
    bridge_id = "br_" + secrets.token_hex(4)
    token = secrets.token_hex(16)
    row = ClientBridge(
        bridge_id=bridge_id,
        token=token,
        user_id=user.id,
        label=body.label,
    )
    db.add(row)
    db.commit()
    logger.info(f"[bridge] registered {bridge_id} user_id={user.id} label={body.label!r}")
    return RegisterOut(bridge_id=bridge_id, token=token)


@router.post("/sync")
def sync(
    body: SyncIn,
    x_bridge_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = _require_bridge(db, body.bridge_id, x_bridge_token)

    out_dir = CLIENT_RESULTS_ROOT / body.bridge_id
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "bridge_id": body.bridge_id,
        "user_id": row.user_id,
        "equity": body.equity,
        "balance": body.balance,
        "open_positions": body.open_positions,
        "positions": [p.model_dump() for p in body.positions],
        "initial_capital": body.initial_capital,
        "currency": body.currency,
        "latency_ms": body.latency_ms,
        "engine_connected": body.engine_connected,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    target = out_dir / "performance.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    row.last_seen = datetime.utcnow()
    db.commit()

    logger.info(f"[bridge] sync {body.bridge_id} user_id={row.user_id} equity={body.equity} -> {target}")
    return {"ok": True, "bridge_id": body.bridge_id, "wrote": str(target)}
# --- END FILE ---