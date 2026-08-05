import streamlit as st
import pandas as pd
import json
import os
import glob
from datetime import datetime

@st.cache_data(ttl=60)
def load_dna_results():
    dna_files = glob.glob("dna_results/*_DNA.json")
    results = {}
    for file in dna_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
            # Parse symbol and timeframe from filename
            basename = os.path.basename(file)  # e.g., "BreakX 600_PERIOD_M1_data_M1_DNA.json"
            name = basename.replace('_DNA.json', '')  # remove suffix
            if '_PERIOD_' in name:
                parts = name.split('_PERIOD_')
                symbol = parts[0].strip()
                rest = parts[1]  # e.g., "M1_data_M1"
                if '_data_' in rest:
                    tf_part = rest.split('_data_')[0]
                    timeframe = tf_part.strip()
                else:
                    timeframe = rest.strip()
            else:
                # fallback: use data fields
                symbol = data.get('symbol', '')
                timeframe = data.get('timeframe', '')
            # Normalise timeframe to lowercase for consistent keys
            key = f"{symbol}_{timeframe}"
            results[key] = data
            # Store normalised fields for quick access
            data['_normalised_symbol'] = symbol
            data['_normalised_timeframe'] = timeframe
        except Exception as e:
            continue
    return results

@st.cache_data(ttl=60)
def load_all_trades():
    trades = []
    # Backtest
    backtest_file = "research_data/trades.jsonl"
    if os.path.exists(backtest_file):
        with open(backtest_file, 'r') as f:
            for line in f:
                try:
                    trade = json.loads(line.strip())
                    if 'entry_time' in trade:
                        trades.append(trade)
                except:
                    continue
    # Live sessions
    live_dir = "live_results"
    if os.path.exists(live_dir):
        for session_folder in os.listdir(live_dir):
            if session_folder.startswith("session_"):
                session_path = os.path.join(live_dir, session_folder)
                # trades.json
                trades_file = os.path.join(session_path, "trades.json")
                if os.path.exists(trades_file):
                    try:
                        with open(trades_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for trade in data:
                                    if 'entry_time' in trade:
                                        trades.append(trade)
                    except:
                        pass
                # events.jsonl (trade_close events)
                events_file = os.path.join(session_path, "events.jsonl")
                if os.path.exists(events_file):
                    with open(events_file, 'r') as f:
                        for line in f:
                            try:
                                event = json.loads(line.strip())
                                if event.get('type') == 'trade_close':
                                    data = event['data']
                                    trade = {
                                        'symbol': data.get('symbol'),
                                        'direction': data.get('action', 'UNKNOWN'),
                                        'entry_price': data.get('entry_price'),
                                        'exit_price': data.get('exit_price'),
                                        'pnl': data.get('pnl'),
                                        'result': 'TP' if data.get('pnl', 0) > 0 else 'SL',
                                        'strategy': data.get('strategy'),
                                        'entry_time': data.get('entry_time'),
                                        'exit_time': event.get('timestamp'),
                                    }
                                    if trade.get('entry_time'):
                                        trades.append(trade)
                            except:
                                continue
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    for col in ['entry_time', 'exit_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

@st.cache_data(ttl=60)
def load_optimization_results():
    opt_file = "optimization_results/optimization_results.json"
    if os.path.exists(opt_file):
        with open(opt_file, 'r') as f:
            return json.load(f)
    return []

@st.cache_data(ttl=60)
def load_insights():
    insights_file = "research_data/insights.json"
    if os.path.exists(insights_file):
        with open(insights_file, 'r') as f:
            return json.load(f)
    return {}

@st.cache_data(ttl=10)
def load_live_sessions():
    sessions = []
    base_dir = "live_results"
    if not os.path.exists(base_dir):
        return sessions
    for folder in os.listdir(base_dir):
        if folder.startswith("session_"):
            session_path = os.path.join(base_dir, folder)
            events_file = os.path.join(session_path, "events.jsonl")
            if os.path.exists(events_file):
                equity_data = []
                trade_events = []
                with open(events_file, 'r') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            if event.get('type') == 'equity':
                                data = event.get('data', {})
                                equity_data.append({
                                    'timestamp': event.get('timestamp'),
                                    'equity': data.get('equity'),
                                    'balance': data.get('balance'),
                                    'open_positions': data.get('open_positions'),
                                    'cycle': data.get('cycle')
                                })
                            elif event.get('type') in ['trade_open', 'trade_close']:
                                evt = event['data'].copy()
                                evt['event_time'] = event.get('timestamp')
                                evt['event_type'] = event.get('type')
                                trade_events.append(evt)
                        except:
                            continue
                if equity_data:
                    df_equity = pd.DataFrame(equity_data)
                    df_equity['timestamp'] = pd.to_datetime(df_equity['timestamp'])
                    sessions.append({
                        'session_id': folder,
                        'path': session_path,
                        'equity_df': df_equity,
                        'trade_events': pd.DataFrame(trade_events) if trade_events else pd.DataFrame()
                    })
    return sessions