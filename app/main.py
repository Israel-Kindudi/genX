"""
backend/app/main.py — GenX

Single, consolidated FastAPI application.
"""
import json
import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine, SessionLocal
from .plans_seed import seed_plans
from .routers import payments_router

# after other include_router calls
# Routers
from .routers import (
    auth_router,
    dna_router,
    strategies_router,
    backtest_router,
    live_router,
    mining_router,
    audit_router,
    bridge_router,
)
from .routers.subscriptions_router import router as subs_router, public_router

# WebSocket + watcher infrastructure
from .websocket_manager import manager
from .file_watcher import watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Anchored to this file: backend/app/main.py -> parents[1] = backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
CLIENT_RESULTS_ROOT = BACKEND_ROOT / "client_results"


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="GenX API",
    version="1.0.0",
    description="Backend API for the GenX quantitative trading platform.",
    redirect_slashes=True,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_origins = (
    settings.allowed_origins_list
    if hasattr(settings, "allowed_origins_list")
    else (settings.allowed_origins if hasattr(settings, "allowed_origins") else ["*"])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router)
app.include_router(dna_router.router)
app.include_router(strategies_router.router)
app.include_router(backtest_router.router)
app.include_router(live_router.router)
app.include_router(mining_router.router)
app.include_router(audit_router.router)
app.include_router(subs_router)            # authenticated /api/subscriptions/*
app.include_router(public_router)          # unauthenticated /api/public/plans
app.include_router(payments_router.router)
app.include_router(bridge_router.router)   # /api/bridge/*


# ---------------------------------------------------------------------------
# Snapshot-on-connect
# ---------------------------------------------------------------------------
def _load_client_snapshots():
    """Read currently-known client telemetry snapshots from disk.

    Returns a list of {"bridge_id", "data", "timestamp"} dicts, one per
    performance.json under backend/client_results/*/. Sorted by bridge_id
    for determinism.
    """
    out = []
    if not CLIENT_RESULTS_ROOT.exists():
        return out
    for path in sorted(CLIENT_RESULTS_ROOT.glob("*/performance.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[ws] snapshot read failed {path}: {e}")
            continue
        out.append({
            "bridge_id": data.get("bridge_id") or path.parent.name,
            "data": data,
            "timestamp": data.get("updated_at"),
        })
    return out


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def _startup():
    # 1. Create tables
    Base.metadata.create_all(bind=engine)

    # 2. Seed default plans
    db = SessionLocal()
    try:
        seed_plans(db)
    finally:
        db.close()

    # 3. Start the file watcher
    watcher.start()
    logger.info("✅ GenX API started (watcher running)")


@app.on_event("shutdown")
async def _shutdown():
    await watcher.stop()
    logger.info("🛑 GenX API stopped (watcher halted)")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"name": "GenX API", "status": "ok", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket — /ws/live
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "hello",
            "message": "Connected to GenX live stream",
        })

        # snapshot-on-connect: send currently-known client telemetry to this
        # socket so a fresh dashboard is not blank until the next /sync.
        # GUARD: only when exactly one bridge exists. With >1 we would fan
        # out every client's equity to every socket — a privacy leak. Until
        # per-user auth exists (Seam 3), refuse and log.
        snapshots = _load_client_snapshots()
        if len(snapshots) == 1:
            s = snapshots[0]
            await websocket.send_text(json.dumps({
                "type": "client_equity",
                "bridge_id": s["bridge_id"],
                "data": s["data"],
                "timestamp": s["timestamp"],
            }, default=str))
            logger.info(f"[ws] snapshot-on-connect {s['bridge_id']}")
        elif len(snapshots) > 1:
            logger.warning(
                f"[ws] {len(snapshots)} bridges present; snapshot-on-connect "
                f"disabled pending Seam 3 auth (no fan-out)"
            )

        while True:
            try:
                # Consume client messages; sends heartbeat on idle
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[ws] Error: {e}")
        await manager.disconnect(websocket)
# --- END FILE ---