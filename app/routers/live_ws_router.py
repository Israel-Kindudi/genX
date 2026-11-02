"""
backend/app/routers/live_ws_router.py

WebSocket endpoint: /ws/live

Behaviour:
- Accepts the connection
- Delegates to EngineWatcher.subscribe (replays recent history + live events)
- Cleans up on disconnect
- Sends periodic pings to detect dead clients (browsers behind NAT)
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.engine_watcher import get_engine_watcher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])

PING_INTERVAL_SECONDS = 25


@router.websocket("/ws/live")
async def live_ws(ws: WebSocket):
    await ws.accept()
    watcher = get_engine_watcher()

    try:
        await watcher.subscribe(ws)

        # Keep the connection alive; browser clients ignore incoming pings
        # but if they've gone away, send will fail and we drop.
        while True:
            try:
                # We don't expect client messages, but consuming prevents
                # the underlying TCP from piling up unconsumed data.
                await asyncio.wait_for(ws.receive_text(), timeout=PING_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                try:
                    await ws.send_json({"type": "ping", "timestamp": None, "data": {}})
                except Exception:
                    break
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws/live error")
    finally:
        watcher.unsubscribe(ws)
        try:
            await ws.close()
        except Exception:
            pass