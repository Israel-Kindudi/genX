"""
WebSocket connection manager for broadcasting live updates.
"""

import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active.add(websocket)
        logger.info(f"[ws] Client connected. Total: {len(self.active)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active.discard(websocket)
        logger.info(f"[ws] Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected clients."""
        if not self.active:
            return
        payload = json.dumps(message, default=str)
        dead = set()
        async with self._lock:
            for ws in self.active:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.warning(f"[ws] Send failed: {e}")
                    dead.add(ws)
            for ws in dead:
                self.active.discard(ws)


manager = ConnectionManager()