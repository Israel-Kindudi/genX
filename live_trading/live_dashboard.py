#!/usr/bin/env python
"""
Live Trading Dashboard for real-time monitoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import MetaTrader5 as mt5
import json
import os
import sys
from datetime import datetime, timedelta

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import DATA_DIR

st.set_page_config(page_title="SYNTHX Live Dashboard", layout="wide")

# -------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------
def get_mt5_positions():
    if not mt5.initialize():
        return []
    positions = mt5.positions_get()
    mt5.shutdown()
    return positions if positions else []

def get_mt5_account_info():
    if not mt5.initialize():
        return None
    acc = mt5.account_info()
    mt5.shutdown()
    return acc

def get_live_ohlc(symbol, bars=200):
    if not mt5.initialize():
        return None
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, bars)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], unit='s')
    df.set_index('Date', inplace=True)
    return df

def load_performance_file():
    # In real system, you'd read from a log file or database
    # Here we just simulate some data
    if os.path.exists("live_performance.json"):
        with open("live_performance.json", 'r') as f:
            return json.load(f)
    # Return dummy data for demo
    return {
        'total_trades': 42,
        'win_rate': 58.6,
        'total_pnl': 1250.34,
        'sharpe': 1.23,
        'strategy_performance': {
            'Scalping DMI+MACD (default)': {'trades': 18, 'pnl': 450.20, 'win_rate': 61.2},
            'Scalping DMI+MACD (tuned)': {'trades': 15, 'pnl': 380.15, 'win_rate': 56.7},
            'Scalping HMA+Stoch (tuned)': {'trades': 9, 'pnl': 420.00, 'win_rate': 66.7},
        }
    }

# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------
st.sidebar.title("🧬 SYNTHX Live")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data"):
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Position Limits")
st.sidebar.write("Max total: 7")
st.sidebar.write("Max per strategy: 3")

st.sidebar.markdown("---")
st.sidebar.subheader("Status")
positions = get_mt5_positions()
st.sidebar.write(f"Open positions: {len(positions)}")

# -------------------------------------------------------------------
# Account Info
# -------------------------------------------------------------------
acc = get_mt5_account_info()
if acc:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Balance", f"${acc.balance:,.2f}")
    col2.metric("Equity", f"${acc.equity:,.2f}")
    col3.metric("Margin", f"${acc.margin:,.2f}")
    col4.metric("Free Margin", f"${acc.margin_free:,.2f}")

# -------------------------------------------------------------------
# Performance Summary
# -------------------------------------------------------------------
perf = load_performance_file()
st.subheader("📊 Performance Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trades", perf.get('total_trades', 0))
col2.metric("Win Rate", f"{perf.get('win_rate', 0):.1f}%")
col3.metric("Total PnL", f"${perf.get('total_pnl', 0):.2f}")
col4.metric("Sharpe", f"{perf.get('sharpe', 0):.2f}")

# -------------------------------------------------------------------
# Strategy Performance Table
# -------------------------------------------------------------------
if 'strategy_performance' in perf:
    df_strat = pd.DataFrame(perf['strategy_performance']).T
    df_strat.columns = ['Trades', 'PnL', 'Win Rate %']
    st.subheader("📈 Strategy Performance")
    st.dataframe(df_strat, use_container_width=True)

# -------------------------------------------------------------------
# Open Positions
# -------------------------------------------------------------------
st.subheader("💼 Open Positions")
if positions:
    pos_data = []
    for pos in positions:
        pos_data.append({
            'Symbol': pos.symbol,
            'Type': pos.type_string,
            'Volume': pos.volume,
            'Entry': pos.price_open,
            'Current': pos.price_current,
            'PnL': pos.profit,
            'SL': pos.sl,
            'TP': pos.tp,
            'Comment': pos.comment,
        })
    df_pos = pd.DataFrame(pos_data)
    st.dataframe(df_pos, use_container_width=True)

    # Profit distribution
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_pos['Symbol'],
        y=df_pos['PnL'],
        text=df_pos['PnL'].apply(lambda x: f"${x:.2f}"),
        textposition='auto',
        marker_color=['green' if x > 0 else 'red' for x in df_pos['PnL']]
    ))
    fig.update_layout(title="PnL per Position", xaxis_title="Symbol", yaxis_title="PnL ($)")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No open positions")

# -------------------------------------------------------------------
# Price Charts
# -------------------------------------------------------------------
st.subheader("📉 Live Price Charts")
symbols = ["BreakX 600", "BreakX 1200", "BreakX 1800"]
tabs = st.tabs(symbols)

for idx, sym in enumerate(symbols):
    with tabs[idx]:
        df = get_live_ohlc(sym, 200)
        if df is None:
            st.warning(f"No data for {sym}")
            continue
        # Plot candlestick
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=sym
        ))
        fig.update_layout(
            title=f"{sym} - Price",
            yaxis_title="Price",
            height=400,
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# Log (placeholder)
# -------------------------------------------------------------------
st.subheader("📋 Live Log")
log_text = st.text_area("Log Output", height=200, value="Waiting for updates...")
if st.button("Clear Log"):
    st.experimental_rerun()