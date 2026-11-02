"""
backend/app/services/engine_watcher.py

Watches the GenX engine's session directory and broadcasts events to
WebSocket subscribers.

Design:
- On startup, finds the newest session directory under GENX_ROOT/live_results/
- Tails the newest events.jsonl inside it
- On rotation (new session dir), switches to the new file automatically
- Maintains a bounded in-memory buffer so late-joining clients get recent history
- Normalizes events into the exact shapes the frontend expects

The engine writes events in this shape (as produced by live_trading_ml_gate_v2):
    {"timestamp": "...", "type": "trade_open", "data": {...}}
    {"timestamp": "...", "type": "trade_close", "data": {...}}
    {"timestamp": "...", "type": "equity", "data": {...}}

The frontend expects the same shape but with `session_id` at the top level.
We inject it from the directory name.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# How many recent events to keep for late-joining clients.
HISTORY_SIZE = 500

# How often to check for a new session directory / file growth.
POLL_INTERVAL_SECONDS = 1.0


class EngineWatcher:
    """
    Single instance per process. Started by FastAPI lifespan.
    Exposes broadcast and subscribe; underlying tail is an asyncio task.
    """

    def __init__(self, genx_root: Path):
        self.genx_root = Path(genx_root)
        self.live_results_dir = self.genx_root / "live_results"

        self._history: Deque[Dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self._subscribers: Set[WebSocket] = set()

        self._current_session: Optional[str] = None
        self._current_path: Optional[Path] = None
        self._current_offset: int = 0

        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="engine-watcher")
        logger.info("Engine watcher started on %s", self.live_results_dir)

    async def stop(self) -> None:
        self._shutdown_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        logger.info("Engine watcher stopped")

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------
    async def subscribe(self, ws: WebSocket) -> None:
        """Register a websocket and replay recent history."""
        self._subscribers.add(ws)
        # Replay history so late joiners get context
        for event in list(self._history):
            try:
                await ws.send_json(event)
            except Exception:
                self._subscribers.discard(ws)
                return

    def unsubscribe(self, ws: WebSocket) -> None:
        self._subscribers.discard(ws)

    async def _broadcast(self, event: Dict[str, Any]) -> None:
        self._history.append(event)
        dead: List[WebSocket] = []
        for ws in list(self._subscribers):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._subscribers.discard(ws)

    # ------------------------------------------------------------------
    # Tail loop
    # ------------------------------------------------------------------
    async def _run(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("engine_watcher tick failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _tick(self) -> None:
        latest = self._find_latest_session()
        if latest is None:
            return

        session_name, events_path = latest
        if session_name != self._current_session:
            # New session — reset
            self._current_session = session_name
            self._current_path = events_path
            self._current_offset = 0
            logger.info("Engine watcher switched to session %s", session_name)

        if not self._current_path or not self._current_path.exists():
            return

        try:
            size = self._current_path.stat().st_size
        except OSError:
            return

        if size <= self._current_offset:
            return

        # Read new lines
        try:
            with self._current_path.open("r", encoding="utf-8") as f:
                f.seek(self._current_offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    event = self._normalize(raw)
                    if event is not None:
                        await self._broadcast(event)
                self._current_offset = f.tell()
        except OSError:
            logger.warning("Could not read %s", self._current_path)

    def _find_latest_session(self) -> Optional[tuple[str, Path]]:
        if not self.live_results_dir.exists():
            return None
        sessions = [
            d for d in self.live_results_dir.iterdir()
            if d.is_dir() and d.name.startswith("session_")
        ]
        if not sessions:
            return None
        latest = max(sessions, key=lambda d: d.name)
        events = latest / "events.jsonl"
        if not events.exists():
            return None
        return latest.name, events

    # ------------------------------------------------------------------
    # Normalization — produce frontend-expected shape
    # ------------------------------------------------------------------
    def _normalize(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ev_type = raw.get("type") or raw.get("event")
        if not ev_type:
            return None

        # Some engine versions use "event" as the type key
        if "type" not in raw and "event" in raw:
            raw = {**raw, "type": raw["event"]}

        # Session ID: engine writes it under data sometimes, or we infer
        data = raw.get("data") or {}

        session_id = (
            raw.get("session_id")
            or data.get("session_id")
            or self._current_session
            or "unknown"
        )

        timestamp = raw.get("timestamp") or datetime.now(timezone.utc).isoformat()

        # Reconcile equity field aliases
        if ev_type == "equity":
            data = dict(data)
            data.setdefault(
                "initial_capital",
                data.get("initialCapital", None),
            )
            data.setdefault(
                "account_currency",
                data.get("currency", "USD"),
            )
            data.setdefault("equity", 0.0)
            data.setdefault("balance", 0.0)
            data.setdefault("open_positions", 0)
            data.setdefault("cycle", 0)

        return {
            "type": ev_type,
            "session_id": session_id,
            "timestamp": timestamp,
            "data": data,
        }


# Module-level singleton, wired by main.py
engine_watcher: Optional[EngineWatcher] = None


def get_engine_watcher() -> EngineWatcher:
    if engine_watcher is None:
        raise RuntimeError(
            "Engine watcher not initialized. Was lifespan() run?"
        )
    return engine_watcher