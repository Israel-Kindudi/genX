import os
import glob
import json
from typing import Optional, List, Dict, Any
import pandas as pd
from .config import settings


class GenXDataLoader:
    """Read-only access to GenX project files."""

    def __init__(self, root: Optional[str] = None):
        self.root = os.path.abspath(root or settings.genx_root)

    # -------- DNA --------
    def list_dna(self) -> List[Dict[str, Any]]:
        files = glob.glob(os.path.join(self.root, "dna_results", "*_DNA.json"))
        result = []
        for f in files:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                result.append({
                    "file": os.path.basename(f),
                    "symbol": data.get("symbol"),
                    "timeframe": data.get("timeframe"),
                    "bars": data.get("bars", 0),
                })
            except Exception:
                continue
        return result

    def get_dna(self, symbol: str, timeframe: str = "M5") -> Optional[Dict[str, Any]]:
        pattern = os.path.join(self.root, "dna_results", f"*{symbol}*{timeframe}*_DNA.json")
        files = glob.glob(pattern)
        if not files:
            return None
        try:
            with open(files[0]) as f:
                return json.load(f)
        except Exception:
            return None

    # -------- Strategies --------
    def list_strategies(self) -> List[Dict[str, Any]]:
        """Read the strategy map from the optimizer."""
        try:
            import sys
            if self.root not in sys.path:
                sys.path.insert(0, self.root)
            from optimization.strategy_optimizer import STRATEGY_MAP
            return [
                {
                    "name": name,
                    "class": cls.__name__,
                    "parameters": {k: {"min": v[0], "max": v[1]} for k, v in bounds.items()},
                }
                for name, (cls, bounds) in STRATEGY_MAP.items()
            ]
        except Exception as e:
            return [{"error": str(e)}]

    # -------- Backtest summaries --------
    def load_backtest_summaries(self) -> pd.DataFrame:
        files = glob.glob(os.path.join(self.root, "backtest_reports", "*_summary.csv"))
        frames = []
        for f in files:
            try:
                df = pd.read_csv(f)
                df["_file"] = os.path.basename(f)
                frames.append(df)
            except Exception:
                continue
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # -------- Optimized parameters --------
    def load_optimized(self) -> pd.DataFrame:
        files = glob.glob(os.path.join(self.root, "optimized_strategies", "*_final.json"))
        records = []
        for f in files:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                report = data.get("best_report", {}) or {}
                records.append({
                    "strategy": data.get("strategy"),
                    "symbol": data.get("symbol"),
                    "best_fitness": data.get("best_fitness"),
                    "total_trades": report.get("total_trades"),
                    "total_pnl": report.get("total_pnl"),
                    "win_rate": report.get("win_rate"),
                    "sharpe": report.get("sharpe_ratio"),
                    "max_drawdown": report.get("max_drawdown"),
                    "file": os.path.basename(f),
                })
            except Exception:
                continue
        return pd.DataFrame(records)

    # -------- Live sessions --------
    def list_live_sessions(self) -> List[Dict[str, Any]]:
        base = os.path.join(self.root, "live_results")
        if not os.path.isdir(base):
            return []
        sessions = []
        for folder in sorted(os.listdir(base)):
            if not folder.startswith("session_"):
                continue
            path = os.path.join(base, folder)
            trades_file = os.path.join(path, "trades.json")
            trades = []
            if os.path.exists(trades_file):
                try:
                    with open(trades_file) as f:
                        trades = json.load(f)
                except Exception:
                    pass
            closed = [t for t in trades if t.get("status") == "closed"]
            open_ = [t for t in trades if t.get("status") == "open"]
            stale = [t for t in trades if t.get("status") == "stale"]
            pnl = sum(t.get("pnl", 0) or 0 for t in closed)
            sessions.append({
                "session_id": folder,
                "trades": len(trades),
                "closed": len(closed),
                "open": len(open_),
                "stale": len(stale),
                "pnl": round(pnl, 2),
            })
        return sessions

    def get_live_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.root, "live_results", session_id)
        trades_file = os.path.join(path, "trades.json")
        events_file = os.path.join(path, "events.jsonl")
        if not os.path.exists(trades_file):
            return None
        trades = []
        with open(trades_file) as f:
            trades = json.load(f)
        equity = []
        if os.path.exists(events_file):
            with open(events_file) as f:
                for line in f:
                    try:
                        e = json.loads(line.strip())
                        if e.get("type") == "equity":
                            equity.append(e["data"])
                    except Exception:
                        continue
        return {
            "session_id": session_id,
            "trades": trades,
            "equity": equity,
        }

    # -------- Mining results --------
    def list_mining_runs(self) -> List[Dict[str, Any]]:
        base = os.path.join(self.root, "mining_results")
        if not os.path.isdir(base):
            return []
        runs = []
        for folder in sorted(os.listdir(base), reverse=True):
            if not folder.startswith("run_"):
                continue
            meta_file = os.path.join(base, folder, "run_metadata.json")
            meta = {}
            if os.path.exists(meta_file):
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                except Exception:
                    pass
            runs.append({"run_id": folder, "metadata": meta})
        return runs

    def get_mining_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        base = os.path.join(self.root, "mining_results", run_id)
        if not os.path.isdir(base):
            return None
        result = {"run_id": run_id}
        for fname in ["run_metadata.json", "best_per_regime.json"]:
            path = os.path.join(base, fname)
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        result[fname.replace(".json", "")] = json.load(f)
                except Exception:
                    pass
        imp_file = os.path.join(base, "feature_importance.csv")
        if os.path.exists(imp_file):
            try:
                result["feature_importance"] = pd.read_csv(imp_file).to_dict("records")
            except Exception:
                pass
        return result

    # -------- Audit outputs --------
    def list_audit_reports(self) -> List[Dict[str, Any]]:
        base = os.path.join(self.root, "audit_outputs")
        if not os.path.isdir(base):
            return []
        reports = []
        for f in sorted(os.listdir(base), reverse=True):
            if f.endswith(".json"):
                reports.append({"file": f})
        return reports