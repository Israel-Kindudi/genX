"""
Watch live_results/ (master event streams) and client_results/ (client
telemetry snapshots) and broadcast updates.

Anchored to this file's location (parents[1] = backend/), NOT settings.genx_root.

- live_results/session_*/events.jsonl         -> master events (unchanged)
- client_results/{bridge_id}/performance.json -> client_equity snapshots (new)
"""
import json
import asyncio
import logging
from pathlib import Path

from .websocket_manager import manager

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]   # .../genx_website/backend
MASTER_ROOT = BACKEND_ROOT / "live_results"
CLIENT_ROOT = BACKEND_ROOT / "client_results"
logger.info(f"[watcher] master_anchor={MASTER_ROOT}")
logger.info(f"[watcher] client_anchor={CLIENT_ROOT}")


class LiveResultsWatcher:
    """Polls master event streams and client telemetry snapshots."""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.running = False
        self._task = None
        self._offsets = {}
        self._client_mtimes = {}

    # -------- master stream (unchanged behavior) --------

    def _find_event_files(self):
        if not MASTER_ROOT.exists():
            return []
        return list(MASTER_ROOT.glob("session_*/events.jsonl"))

    def _read_new_events(self, path: Path):
        key = str(path)
        last_offset = self._offsets.get(key, 0)
        try:
            file_size = path.stat().st_size
        except Exception:
            return []
        if file_size < last_offset:
            last_offset = 0
        events = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.seek(last_offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                self._offsets[key] = f.tell()
        except Exception as e:
            logger.error(f"[watcher] Error reading {path}: {e}")
            return []
        return events

    def _extract_session_id(self, path: Path) -> str:
        for part in path.parts:
            if part.startswith("session_"):
                return part
        return "unknown"

    # -------- client telemetry (new) --------

    def _find_client_files(self):
        if not CLIENT_ROOT.exists():
            return []
        return list(CLIENT_ROOT.glob("*/performance.json"))

    def _read_client_snapshot(self, path: Path):
        key = str(path)
        try:
            mtime = path.stat().st_mtime
        except Exception:
            return None
        if self._client_mtimes.get(key) == mtime:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[watcher] Error reading client {path}: {e}")
            return None
        self._client_mtimes[key] = mtime
        return data

    # -------- loop --------

    async def _loop(self):
        logger.info(f"[watcher] Starting watcher (interval={self.interval}s)")
        while self.running:
            try:
                await asyncio.sleep(self.interval)

                for path in self._find_event_files():
                    session_id = self._extract_session_id(path)
                    for event in self._read_new_events(path):
                        event_type = event.get("type")
                        data = event.get("data", {}) or {}
                        if event_type == "equity":
                            if "initial_capital" not in data and "initialCapital" in data:
                                data["initial_capital"] = data["initialCapital"]
                            if "account_currency" not in data and "currency" in data:
                                data["account_currency"] = data["currency"]
                        if event_type in ("trade_open", "trade_close", "equity", "capital_flow"):
                            await manager.broadcast({
                                "type": event_type,
                                "session_id": session_id,
                                "data": data,
                                "timestamp": event.get("timestamp"),
                            })

                for path in self._find_client_files():
                    snapshot = self._read_client_snapshot(path)
                    if snapshot is None:
                        continue
                    bridge_id = snapshot.get("bridge_id") or path.parent.name
                    logger.info(f"[watcher] client_equity {bridge_id}")
                    await manager.broadcast({
                        "type": "client_equity",
                        "bridge_id": bridge_id,
                        "data": snapshot,
                        "timestamp": snapshot.get("updated_at"),
                    })

            except Exception as e:
                logger.error(f"[watcher] Error: {e}")
                await asyncio.sleep(self.interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


watcher = LiveResultsWatcher()
# --- END FILE ---