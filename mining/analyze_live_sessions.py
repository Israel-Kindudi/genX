#!/usr/bin/env python
"""
Analyze live trading sessions – direction bias, win/loss, and performance.
Reads trades.json from each session folder and generates reports.
"""

import os
import sys
import json
import glob
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================================
#  DATA LOADING
# ============================================================================

def load_all_trades():
    """Load trades from all live sessions (trades.json)."""
    base_dir = "live_results"
    if not os.path.exists(base_dir):
        print("❌ live_results/ folder not found.")
        return pd.DataFrame()

    all_trades = []
    for folder in os.listdir(base_dir):
        if folder.startswith("session_"):
            trades_file = os.path.join(base_dir, folder, "trades.json")
            if os.path.exists(trades_file):
                try:
                    with open(trades_file, 'r') as f:
                        trades = json.load(f)
                    if isinstance(trades, list):
                        for t in trades:
                            t['session'] = folder
                        all_trades.extend(trades)
                except Exception as e:
                    print(f"⚠️ Error reading {trades_file}: {e}")

    if not all_trades:
        return pd.DataFrame()

    df = pd.DataFrame(all_trades)
    # Convert times
    for col in ['entry_time', 'exit_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def load_equity_events():
    """Load equity events from events.jsonl for each session."""
    base_dir = "live_results"
    if not os.path.exists(base_dir):
        return pd.DataFrame()

    equity_data = []
    for folder in os.listdir(base_dir):
        if folder.startswith("session_"):
            events_file = os.path.join(base_dir, folder, "events.jsonl")
            if os.path.exists(events_file):
                with open(events_file, 'r') as f:
                    for line in f:
                        try:
                            ev = json.loads(line.strip())
                            if ev.get('type') == 'equity':
                                data = ev.get('data', {})
                                equity_data.append({
                                    'session': folder,
                                    'timestamp': ev['timestamp'],
                                    'equity': data.get('equity'),
                                    'balance': data.get('balance'),
                                    'open_positions': data.get('open_positions'),
                                })
                        except:
                            continue
    if not equity_data:
        return pd.DataFrame()
    df = pd.DataFrame(equity_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# ============================================================================
#  ANALYSIS
# ============================================================================

def analyze_live_trades(df):
    if df.empty:
        print("❌ No trade data found.")
        return

    print("\n" + "="*80)
    print("📊 LIVE TRADES ANALYSIS")
    print("="*80)
    print(f"Total trades: {len(df)}")

    # Separate by status
    closed = df[df['status'] == 'closed']
    open_trades = df[df['status'] == 'open']
    stale = df[df['status'] == 'stale']

    print(f"  Closed (with PnL): {len(closed)}")
    print(f"  Open: {len(open_trades)}")
    print(f"  Stale (removed locally): {len(stale)}")

    # Direction distribution
    print("\n📈 Direction Distribution (All Trades):")
    dir_counts = df['action'].value_counts()
    print(dir_counts.to_string())
    if len(dir_counts) > 0:
        buy_pct = (dir_counts.get('BUY', 0) / len(df)) * 100
        print(f"  BUY: {dir_counts.get('BUY', 0)} ({buy_pct:.1f}%)")
        print(f"  SELL: {dir_counts.get('SELL', 0)} ({100 - buy_pct:.1f}%)")

    # Closed trades analysis
    if not closed.empty:
        print("\n📊 Closed Trades (with PnL):")
        print(f"  Total: {len(closed)}")
        print(f"  Win rate: {(closed['pnl'] > 0).mean() * 100:.1f}%")
        print(f"  Total PnL: ${closed['pnl'].sum():.2f}")
        print(f"  Avg PnL: ${closed['pnl'].mean():.2f}")

        # Win/Loss by direction
        print("\n  Win/Loss by Direction:")
        for direction in closed['action'].unique():
            subset = closed[closed['action'] == direction]
            win_rate = (subset['pnl'] > 0).mean() * 100
            total_pnl = subset['pnl'].sum()
            print(f"    {direction}: {len(subset)} trades, Win: {win_rate:.1f}%, PnL: ${total_pnl:.2f}")

        # Exit reasons
        print("\n  Exit Reason Distribution:")
        reason_counts = closed['close_reason'].value_counts()
        print(reason_counts.to_string())

        # By strategy
        if 'strategy' in closed.columns:
            print("\n🧬 Performance by Strategy:")
            strat_perf = closed.groupby('strategy').agg({
                'ticket': 'count',
                'pnl': ['sum', 'mean'],
                'action': lambda x: (x == 'BUY').sum() if len(x) > 0 else 0
            })
            # Simplify columns
            strat_perf.columns = ['Trades', 'Total PnL', 'Avg PnL', 'BUY_Count']
            strat_perf['Win Rate'] = closed.groupby('strategy')['pnl'].apply(lambda x: (x > 0).mean() * 100)
            strat_perf['BUY%'] = (strat_perf['BUY_Count'] / strat_perf['Trades']) * 100
            print(strat_perf.round(2).to_string())

        # By symbol
        if 'symbol' in closed.columns:
            print("\n💹 Performance by Symbol:")
            sym_perf = closed.groupby('symbol').agg({
                'ticket': 'count',
                'pnl': ['sum', 'mean']
            })
            sym_perf.columns = ['Trades', 'Total PnL', 'Avg PnL']
            sym_perf['Win Rate'] = closed.groupby('symbol')['pnl'].apply(lambda x: (x > 0).mean() * 100)
            print(sym_perf.round(2).to_string())

    else:
        print("\nNo closed trades to analyse.")

    # ---- Visualisations ----
    # Direction pie
    fig_dir = go.Figure(data=[go.Pie(labels=dir_counts.index, values=dir_counts.values, hole=0.4,
                                     marker=dict(colors=['#00ff88', '#ff4444']))])
    fig_dir.update_layout(title="Trade Direction Distribution")

    # Win/Loss by direction (if closed trades exist)
    if not closed.empty:
        fig_win = go.Figure()
        for d in closed['action'].unique():
            subset = closed[closed['action'] == d]
            if not subset.empty:
                win_pct = (subset['pnl'] > 0).mean() * 100
                loss_pct = 100 - win_pct
                fig_win.add_trace(go.Bar(name=d, x=['Win', 'Loss'], y=[win_pct, loss_pct]))
        fig_win.update_layout(title="Win/Loss Rate by Direction", barmode='group')

        # PnL distribution
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Histogram(x=closed['pnl'], nbinsx=50, marker_color='#00ccff'))
        fig_pnl.update_layout(title="PnL Distribution", xaxis_title="PnL ($)")
    else:
        fig_win = None
        fig_pnl = None

    # Equity curve
    eq_df = load_equity_events()
    fig_eq = None
    if not eq_df.empty:
        fig_eq = go.Figure()
        for session in eq_df['session'].unique():
            sess_df = eq_df[eq_df['session'] == session]
            fig_eq.add_trace(go.Scatter(x=sess_df['timestamp'], y=sess_df['equity'],
                                        mode='lines', name=session))
        fig_eq.update_layout(title="Equity Curves by Session", xaxis_title="Time", yaxis_title="Equity ($)")

    # Display plots (if running in interactive environment)
    fig_dir.show()
    if fig_win:
        fig_win.show()
    if fig_pnl:
        fig_pnl.show()
    if fig_eq:
        fig_eq.show()

    # Save summary to CSV
    if not closed.empty:
        closed.to_csv("live_trades_analysis.csv", index=False)
        print("\n💾 Closed trades saved to live_trades_analysis.csv")

# ============================================================================
#  MAIN
# ============================================================================

if __name__ == "__main__":
    df = load_all_trades()
    analyze_live_trades(df)