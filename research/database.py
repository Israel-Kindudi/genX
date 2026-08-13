"""
Research Database – Load and store trade data from multiple sources.
Combines backtest trades (research_data/trades.jsonl) and live session trades (live_results/*/trades.json).
"""

import os
import json
import glob
import pandas as pd
from datetime import datetime

class ResearchDatabase:
    def __init__(self, include_live=True):
        """
        include_live: If True, also load trades from live_results.
        """
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.trades_file = os.path.join(self.base_dir, "research_data", "trades.jsonl")
        self.live_dir = os.path.join(self.base_dir, "live_results")
        self.include_live = include_live
        os.makedirs(os.path.dirname(self.trades_file), exist_ok=True)

    def _load_backtest_trades(self):
        """Load trades from the research_data/trades.jsonl file."""
        trades = []
        if os.path.exists(self.trades_file):
            with open(self.trades_file, 'r') as f:
                for line in f:
                    try:
                        trades.append(json.loads(line.strip()))
                    except:
                        continue
        return trades

    def _load_live_trades(self):
        """Load trades from all live_results sessions."""
        trades = []
        if not os.path.exists(self.live_dir):
            return trades
        for folder in os.listdir(self.live_dir):
            if folder.startswith("session_"):
                session_path = os.path.join(self.live_dir, folder)
                trades_file = os.path.join(session_path, "trades.json")
                if os.path.exists(trades_file):
                    try:
                        with open(trades_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for t in data:
                                    t['session_id'] = folder
                                    trades.append(t)
                    except Exception as e:
                        print(f"⚠️ Error reading {trades_file}: {e}")
        return trades

    def read_all_trades(self):
        """Read all trades from backtest and live sessions."""
        all_trades = []
        all_trades.extend(self._load_backtest_trades())
        if self.include_live:
            all_trades.extend(self._load_live_trades())
        
        if not all_trades:
            print("⚠️ No trades found in any source.")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_trades)
        # Convert time columns
        for col in ['entry_time', 'exit_time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    def append_trade(self, trade):
        """Append a single trade to the research_data/trades.jsonl file."""
        with open(self.trades_file, 'a') as f:
            json.dump(trade, f, default=str)
            f.write('\n')

    def append_trades(self, trades):
        """Append multiple trades to the research_data/trades.jsonl file."""
        with open(self.trades_file, 'a') as f:
            for trade in trades:
                json.dump(trade, f, default=str)
                f.write('\n')

    def sync_live_to_research(self):
        """
        Copy all live session trades to research_data/trades.jsonl (deduplicate by ticket).
        """
        live_trades = self._load_live_trades()
        # Read existing research trades
        existing = self._load_backtest_trades()
        existing_tickets = {t.get('ticket') for t in existing if 'ticket' in t}
        
        new_trades = [t for t in live_trades if t.get('ticket') not in existing_tickets]
        if new_trades:
            self.append_trades(new_trades)
            print(f"✅ Synced {len(new_trades)} new live trades to research database.")
        else:
            print("✅ No new trades to sync.")

    def get_win_rate_by_strategy(self):
        """Return win rate per strategy from closed trades."""
        df = self.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        closed = df[df['status'] == 'closed']
        if closed.empty:
            return pd.DataFrame()
        return closed.groupby('strategy')['pnl'].apply(lambda x: (x > 0).mean() * 100).round(2)