
"""
SYNTHX Interactive Dashboard
Unified trade loading, live auto‑refresh, data source filters, and improved UX.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import glob
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="SYNTHX Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLING – (same beautiful dark theme)
# ============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00ff88, #00ccff, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        animation: fadeIn 1s ease-in;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #a0aec0;
        margin-bottom: 2rem;
        border-left: 4px solid #00ff88;
        padding-left: 1rem;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes glow {
        0% { text-shadow: 0 0 10px #00ff88; }
        50% { text-shadow: 0 0 20px #00ccff, 0 0 40px #a855f7; }
        100% { text-shadow: 0 0 10px #00ff88; }
    }
    .glow-text {
        animation: glow 3s infinite;
    }
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #00ccff;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        border-bottom: 2px solid #2d3748;
        padding-bottom: 0.3rem;
    }
    .metric-card {
        background: #1a1a2e;
        padding: 1.2rem;
        border-radius: 16px;
        border: 1px solid #2d3748;
        text-align: center;
        transition: transform 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: #00ff88;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00ff88, #00ccff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #a0aec0;
        margin-top: 0.2rem;
    }
    .positive {
        color: #00ff88 !important;
        -webkit-text-fill-color: #00ff88 !important;
    }
    .negative {
        color: #ff4444 !important;
        -webkit-text-fill-color: #ff4444 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1.2rem;
        font-size: 1rem;
        font-weight: 500;
        border-radius: 8px;
        background: transparent;
        color: #a0aec0;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #00ff88, #00ccff);
        color: #0a0a1a !important;
        font-weight: 600;
    }
    .info-box {
        background: #1a1a2e;
        border-left: 4px solid #00ff88;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #e2e8f0;
    }
    .pillar-card {
        background: #1a1a2e;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #2d3748;
        text-align: center;
        height: 100%;
        transition: all 0.3s;
    }
    .pillar-card:hover {
        border-color: #00ff88;
        box-shadow: 0 0 30px rgba(0,255,136,0.1);
    }
    .pillar-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .pillar-title {
        font-weight: 600;
        color: #e2e8f0;
        font-size: 1.1rem;
    }
    .pillar-desc {
        font-size: 0.9rem;
        color: #a0aec0;
        margin-top: 0.3rem;
    }
    .footer {
        margin-top: 3rem;
        padding: 1.5rem 0;
        border-top: 1px solid #2d3748;
        text-align: center;
        color: #718096;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING FUNCTIONS (CACHED)
# ============================================================================

@st.cache_data(ttl=60)
def load_dna_results():
    dna_files = glob.glob("dna_results/*_DNA.json")
    results = {}
    for file in dna_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
            # Extract symbol and timeframe from filename
            basename = os.path.basename(file)  # e.g., "BreakX 600_PERIOD_M1_data_M1_DNA.json"
            # Remove "_DNA.json" suffix
            name_part = basename.replace('_DNA.json', '')
            # Split by "_PERIOD_"
            if '_PERIOD_' in name_part:
                symbol, rest = name_part.split('_PERIOD_', 1)
                # rest could be "M1_data_M1" or "M5_data_M5"
                # timeframe is the first part before "_data_"
                if '_data_' in rest:
                    timeframe = rest.split('_data_')[0]
                else:
                    # fallback
                    timeframe = rest
            else:
                # fallback: use filename without extension
                symbol = name_part
                timeframe = 'unknown'
            # Store normalised values in the data dict
            data['_normalised_symbol'] = symbol.strip()
            data['_normalised_timeframe'] = timeframe.strip().lower()
            # Also store the original for display? not needed.
            key = f"{symbol.strip()}_{timeframe.strip().lower()}"
            results[key] = data
        except Exception as e:
            continue
    return results
@st.cache_data(ttl=60)
def load_all_trades():
    """Load trades from backtest (research_data) and live sessions (trades.json & events.jsonl)."""
    trades = []
    
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
    
    live_dir = "live_results"
    if os.path.exists(live_dir):
        for session_folder in os.listdir(live_dir):
            if session_folder.startswith("session_"):
                session_path = os.path.join(live_dir, session_folder)
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

# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.title("🧬 SYNTHX")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["🏛️ GenX Vision", "📊 Overview", "🧬 DNA Analysis", "📈 Backtest Results",
     "🎯 Optimization", "💳 Trade Analytics", "📊 Insights", "📈 Live P&L"]
)

st.sidebar.markdown("---")

# ---- Data source filter ----
st.sidebar.subheader("Data Source")
source_filter = st.sidebar.selectbox(
    "Show trades from",
    ["All", "Backtest Only", "Live Only"],
    index=0
)

# ---- DNA Filters ----
# ---- DNA Filters ----
st.sidebar.subheader("DNA Filters")
dna_data_loaded = load_dna_results()
# Use normalised fields from the data
all_symbols = sorted(set([data.get('_normalised_symbol', '') for data in dna_data_loaded.values() if data.get('_normalised_symbol')]))
all_timeframes = sorted(set([data.get('_normalised_timeframe', '') for data in dna_data_loaded.values() if data.get('_normalised_timeframe')]))
# Fallback to key parsing if normalised fields are empty
if not all_symbols:
    all_symbols = sorted(set([k.split('_')[0] for k in dna_data_loaded.keys() if '_' in k]))
if not all_timeframes:
    all_timeframes = sorted(set([k.split('_')[1] if len(k.split('_')) > 1 else '' for k in dna_data_loaded.keys() if '_' in k]))
    all_timeframes = [tf for tf in all_timeframes if tf]
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# STYLING HELPER FOR PnL
# ============================================================================
def color_pnl(val):
    """Color positive/negative PnL."""
    if isinstance(val, (int, float)):
        color = '#00ff88' if val > 0 else '#ff4444' if val < 0 else 'white'
        return f'color: {color}'
    return ''

# ============================================================================
# PAGE: GENX VISION (unchanged)
# ============================================================================
if page == "🏛️ GenX Vision":
    st.markdown('<div class="main-header glow-text">🧬 GenX (SYNTHX)</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Where Markets Meet Genetics – A Quantitative Trading Framework</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    <strong>Abstract</strong><br>
    GenX models financial markets as a <strong>chromosome‑like data structure</strong> – the <strong>Market DNA</strong> – 
    consisting of <strong>8 distinct statistical and behavioural chromosomes</strong>. Each chromosome captures a specific 
    market dimension (volatility, momentum, volume, correlation, fractal structure, regime, efficiency, and stability). 
    By extracting these features using advanced data‑mining techniques and optimising for time complexity, 
    GenX transforms raw price data into a compact, information‑rich representation.
    <br><br>
    The system then employs a <strong>genetic algorithm</strong> to fine‑tune strategy parameters, guided by the DNA 
    profile of each asset. This approach enables adaptive, regime‑aware trading across multiple instruments and timeframes.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="sub-header">🔬 The Four Pillars</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="pillar-card">
            <div class="pillar-icon">🧬</div>
            <div class="pillar-title">Market DNA</div>
            <div class="pillar-desc">8 chromosomes capturing volatility, momentum, volume, correlation, fractal structure, regime, efficiency, and stability.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="pillar-card">
            <div class="pillar-icon">📊</div>
            <div class="pillar-title">Fast Backtester</div>
            <div class="pillar-desc">Vectorised backtesting with pre‑computed indicators, supporting 10+ strategies and multiple symbols/timeframes.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="pillar-card">
            <div class="pillar-icon">🎯</div>
            <div class="pillar-title">Genetic Optimisation</div>
            <div class="pillar-desc">DNA‑guided genetic algorithm to find optimal strategy parameters for each asset, maximising Sharpe/return.</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="pillar-card">
            <div class="pillar-icon">🚀</div>
            <div class="pillar-title">Live Trading</div>
            <div class="pillar-desc">MT5 integration with real‑time order execution, position limits, risk management, and session logging.</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    dna_data = load_dna_results()
    trades_df = load_all_trades()
    sessions = load_live_sessions()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🧬 DNA Profiles", len(dna_data))
    with col2:
        st.metric("📊 Strategies", "10+")
    with col3:
        st.metric("💳 Total Trades", f"{len(trades_df):,}")
    with col4:
        st.metric("📈 Live Sessions", len(sessions))
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#718096; font-size:0.9rem;">
        <p>Built with ❤️ using Python, MetaTrader5, Streamlit, and Plotly.</p>
        <p>Explore the full platform using the navigation on the left.</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# PAGE: OVERVIEW (fixed applymap -> map)
# ============================================================================
elif page == "📊 Overview":
    st.markdown('<div class="main-header">📊 SYNTHX Overview</div>', unsafe_allow_html=True)
    
    dna_data = load_dna_results()
    trades_df = load_all_trades()
    sessions = load_live_sessions()
    
    total_trades = len(trades_df) if not trades_df.empty else 0
    
    live_pnl = 0.0
    for s in sessions:
        df = s['equity_df']
        if not df.empty:
            start = df['equity'].iloc[0]
            end = df['equity'].iloc[-1]
            live_pnl += (end - start)
    
    backtest_pnl = trades_df['pnl'].sum() if not trades_df.empty and 'pnl' in trades_df.columns else 0.0
    if sessions:
        total_pnl = live_pnl
        pnl_source = "Live Sessions"
    else:
        total_pnl = backtest_pnl
        pnl_source = "Backtest"
    
    if not trades_df.empty and 'result' in trades_df.columns:
        win_rate = (trades_df['result'] == 'TP').mean() * 100
    else:
        win_rate = 0.0
    
    if not trades_df.empty and 'pnl' in trades_df.columns:
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    else:
        profit_factor = 0.0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(dna_data)}</div>
            <div class="metric-label">DNA Profiles</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_trades:,}</div>
            <div class="metric-label">Total Trades</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        color_class = "positive" if total_pnl >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {color_class}">${total_pnl:,.2f}</div>
            <div class="metric-label">Total PnL ({pnl_source})</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{win_rate:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{profit_factor:.2f}</div>
            <div class="metric-label">Profit Factor</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown('<div class="sub-header">📊 Recent Trades</div>', unsafe_allow_html=True)
    if not trades_df.empty:
        recent = trades_df.sort_values('entry_time', ascending=False).head(20)
        display_cols = ['symbol', 'direction', 'entry_price', 'exit_price', 'pnl', 'result', 'strategy', 'entry_time']
        available_cols = [c for c in display_cols if c in recent.columns]
        # Apply styling using .map() instead of .applymap()
        styled_df = recent[available_cols].style.map(color_pnl, subset=['pnl'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No trades loaded yet. Run backtests or live trading to collect data.")
    
    if sessions:
        st.markdown('<div class="sub-header">📈 Live Sessions</div>', unsafe_allow_html=True)
        session_info = []
        total_live_pnl = 0.0
        for s in sessions:
            df = s['equity_df']
            if not df.empty:
                start = df['equity'].iloc[0]
                end = df['equity'].iloc[-1]
                change = end - start
                total_live_pnl += change
                session_info.append({
                    'Session': s['session_id'],
                    'Start Equity': f"${start:,.2f}",
                    'End Equity': f"${end:,.2f}",
                    'Change ($)': f"${change:+,.2f}",
                    'Change %': f"{(change/start*100) if start != 0 else 0:+.2f}%"
                })
        st.dataframe(pd.DataFrame(session_info), use_container_width=True)
        st.caption(f"Total PnL from all live sessions: ${total_live_pnl:+,.2f}")
    else:
        st.info("No live sessions found. Run the live engine to collect data.")

# ============================================================================
# PAGE: DNA ANALYSIS (uses selected_symbols & selected_timeframes)
# ============================================================================elif page == "🧬 DNA Analysis":
    st.markdown('<div class="main-header">🧬 DNA Analysis</div>', unsafe_allow_html=True)
    
    dna_data = load_dna_results()
    if not dna_data:
        st.warning("No DNA data found. Run dna_analyzer.py first to generate DNA profiles.")
        st.stop()
    
    # Extract normalised symbols and timeframes
    available_symbols = set()
    available_timeframes = set()
    for key, data in dna_data.items():
        sym = data.get('_normalised_symbol', '')
        tf = data.get('_normalised_timeframe', '')
        if sym and tf:
            available_symbols.add(sym)
            available_timeframes.add(tf)
        else:
            # Fallback parse key
            parts = key.split('_')
            if len(parts) >= 2:
                available_symbols.add(parts[0])
                available_timeframes.add(parts[1])
    
    available_symbols = sorted(available_symbols)
    available_timeframes = sorted(available_timeframes)
    
    # Use sidebar filters; if empty, set defaults
    if 'selected_symbols' not in locals() or not selected_symbols:
        selected_symbols = available_symbols[:3] if len(available_symbols) > 3 else available_symbols
    if 'selected_timeframes' not in locals() or not selected_timeframes:
        selected_timeframes = available_timeframes[:1] if available_timeframes else []
    
    # Filter DNA data
    filtered_dna = {}
    for key, data in dna_data.items():
        sym = data.get('_normalised_symbol', '')
        tf = data.get('_normalised_timeframe', '')
        if not sym or not tf:
            parts = key.split('_')
            if len(parts) >= 2:
                sym, tf = parts[0], parts[1]
        if sym in selected_symbols and tf in selected_timeframes:
            filtered_dna[key] = data
    
    if not filtered_dna:
        st.warning("No DNA data matches the selected filters.")
        st.info(f"Available symbols: {', '.join(available_symbols)}")
        st.info(f"Available timeframes: {', '.join(available_timeframes)}")
        st.info("Please adjust your filters in the sidebar.")
        st.stop()
    
    # ---- DNA Comparison Heatmap ----
    st.markdown('<div class="sub-header">DNA Comparison</div>', unsafe_allow_html=True)
    dna_metrics = []
    for key, data in filtered_dna.items():
        dna = data.get('dna', {})
        sym = data.get('_normalised_symbol', key.split('_')[0])
        tf = data.get('_normalised_timeframe', key.split('_')[1] if len(key.split('_')) > 1 else '')
        dna_metrics.append({
            'key': f"{sym}_{tf}",
            'symbol': sym,
            'timeframe': tf,
            'overall_score': dna.get('overall_score', 0),
            'entropy': dna.get('chromosome_vi', {}).get('normalized_entropy', 0),
            'hurst': dna.get('chromosome_ii', {}).get('hurst_exponent', 0),
            'volatility': dna.get('chromosome_iii', {}).get('realized_vol', 0),
            'jump_rate': dna.get('chromosome_iv', {}).get('jump_intensity', 0),
            'trend_length': dna.get('chromosome_vii', {}).get('avg_trend_length', 0),
            'predictability': dna.get('chromosome_vi', {}).get('predictability', 0)
        })
    df_dna = pd.DataFrame(dna_metrics)
    if not df_dna.empty:
        metrics_to_plot = ['overall_score', 'entropy', 'hurst', 'volatility', 'jump_rate', 'trend_length', 'predictability']
        available_metrics = [m for m in metrics_to_plot if m in df_dna.columns]
        if available_metrics:
            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=df_dna[available_metrics].values.T,
                x=df_dna['key'].values,
                y=available_metrics,
                colorscale='Viridis',
                text=df_dna[available_metrics].values.T.round(2),
                texttemplate='%{text}',
                textfont={"size": 8},
                hoverongaps=False,
                colorbar=dict(title="Value")
            ))
            fig.update_layout(height=400, margin=dict(l=50, r=50, t=50, b=50))
            st.plotly_chart(fig, use_container_width=True)
    
    # ---- Strategy Affinity ----
    st.markdown('<div class="sub-header">Strategy Affinity</div>', unsafe_allow_html=True)
    if filtered_dna:
        selected_key = st.selectbox("Select DNA profile to analyze", list(filtered_dna.keys()))
        if selected_key:
            data = filtered_dna[selected_key]
            dna = data.get('dna', {})
            affinity = dna.get('strategy_affinity', {})
            if affinity:
                fig = go.Figure()
                strategies = list(affinity.keys())
                scores = list(affinity.values())
                colors = ['#00ff88' if s > 70 else '#ffaa00' if s > 50 else '#ff4444' for s in scores]
                fig.add_trace(go.Bar(
                    x=strategies,
                    y=scores,
                    marker_color=colors,
                    text=[f"{s:.0f}%" for s in scores],
                    textposition='auto'
                ))
                fig.update_layout(
                    title=f"Strategy Compatibility for {selected_key}",
                    xaxis_title="Strategy",
                    yaxis_title="Compatibility (%)",
                    height=400,
                    yaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No strategy affinity data available for this DNA profile.")# ============================================================================
# PAGE: BACKTEST RESULTS (unchanged)
# ============================================================================
elif page == "📈 Backtest Results":
    st.markdown('<div class="main-header">📈 Backtest Results</div>', unsafe_allow_html=True)
    opt_results = load_optimization_results()
    if not opt_results:
        st.warning("No backtest results found. Run parameter_optimizer.py first.")
        st.stop()
    rows = []
    for res in opt_results:
        report = res.get('report', {})
        rows.append({
            'strategy': res.get('strategy_name', 'Unknown'),
            'symbol': res.get('symbol', 'Unknown'),
            'trades': report.get('total_trades', 0),
            'win_rate': report.get('win_rate', 0),
            'profit_factor': report.get('profit_factor', 0),
            'total_pnl': report.get('total_pnl', 0),
            'return_pct': report.get('return_pct', 0),
            'sharpe': report.get('sharpe_ratio', 0),
            'max_drawdown': report.get('max_drawdown', 0)
        })
    df_results = pd.DataFrame(rows)
    col1, col2 = st.columns(2)
    with col1:
        strategies = ['All'] + list(df_results['strategy'].unique())
        selected_strategy = st.selectbox("Strategy", strategies)
    with col2:
        symbols = ['All'] + list(df_results['symbol'].unique())
        selected_symbol = st.selectbox("Symbol", symbols)
    filtered_df = df_results.copy()
    if selected_strategy != 'All':
        filtered_df = filtered_df[filtered_df['strategy'] == selected_strategy]
    if selected_symbol != 'All':
        filtered_df = filtered_df[filtered_df['symbol'] == selected_symbol]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Backtests", len(filtered_df))
    with col2:
        st.metric("Avg Trades", f"{filtered_df['trades'].mean():.1f}")
    with col3:
        st.metric("Avg Win Rate", f"{filtered_df['win_rate'].mean():.1f}%")
    with col4:
        st.metric("Avg Sharpe", f"{filtered_df['sharpe'].mean():.2f}")
    st.markdown('<div class="sub-header">Performance Scatter</div>', unsafe_allow_html=True)
    fig = px.scatter(filtered_df, x='sharpe', y='total_pnl', size='trades', color='strategy',
                     hover_data=['symbol', 'win_rate', 'return_pct', 'max_drawdown'],
                     title="Sharpe vs PnL",
                     labels={'sharpe': 'Sharpe Ratio', 'total_pnl': 'Total PnL ($)'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="sub-header">Results Table</div>', unsafe_allow_html=True)
    st.dataframe(filtered_df[['strategy', 'symbol', 'trades', 'win_rate', 'sharpe', 'total_pnl', 'return_pct', 'max_drawdown']],
                 use_container_width=True)

# ============================================================================
# PAGE: OPTIMIZATION (unchanged)
# ============================================================================
elif page == "🎯 Optimization":
    st.markdown('<div class="main-header">🎯 Parameter Optimization</div>', unsafe_allow_html=True)
    best_file = "optimization_results/best_parameters.csv"
    if os.path.exists(best_file):
        df_best = pd.read_csv(best_file)
        st.markdown('<div class="sub-header">Top Performing Parameter Sets</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Top Sharpe", f"{df_best['sharpe_ratio'].max():.3f}")
        with col2:
            st.metric("Top Win Rate", f"{df_best['win_rate'].max():.1f}%")
        with col3:
            st.metric("Top Return", f"{df_best['return_pct'].max():.1f}%")
        st.dataframe(df_best[['strategy', 'symbol', 'trades', 'win_rate', 'sharpe_ratio', 'total_pnl', 'return_pct']].head(20),
                     use_container_width=True)
        st.markdown('<div class="sub-header">Parameter Impact</div>', unsafe_allow_html=True)
        if 'param_lookback' in df_best.columns and 'sharpe_ratio' in df_best.columns:
            fig = px.scatter(df_best, x='param_lookback', y='sharpe_ratio', color='strategy', size='trades',
                             hover_data=['param_stop', 'param_tp'], title="Impact of Lookback on Sharpe Ratio")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No optimization results found. Run parameter_optimizer.py first.")

# ============================================================================
# PAGE: TRADE ANALYTICS (unchanged)
# ============================================================================
elif page == "💳 Trade Analytics":
    st.markdown('<div class="main-header">💳 Trade Analytics</div>', unsafe_allow_html=True)
    trades_df = load_all_trades()
    if trades_df.empty:
        st.warning("No trades found.")
        st.stop()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", len(trades_df))
    with col2:
        win_rate = (trades_df['result'] == 'TP').mean() * 100
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("Avg PnL", f"${trades_df['pnl'].mean():.2f}")
    with col4:
        st.metric("Total PnL", f"${trades_df['pnl'].sum():.2f}")
    st.markdown('<div class="sub-header">📊 PnL Distribution & Cumulative</div>', unsafe_allow_html=True)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("PnL Histogram", "Cumulative PnL"))
    fig.add_trace(go.Histogram(x=trades_df['pnl'], nbinsx=50, name="PnL", marker_color='#00ff88'), row=1, col=1)
    fig.add_vline(x=0, line_dash="dash", line_color="red", row=1, col=1)
    trades_df_sorted = trades_df.sort_values('entry_time')
    trades_df_sorted['cum_pnl'] = trades_df_sorted['pnl'].cumsum()
    fig.add_trace(go.Scatter(x=trades_df_sorted['entry_time'], y=trades_df_sorted['cum_pnl'],
                   name="Cumulative PnL", line=dict(color='#00ccff')), row=1, col=2)
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The histogram shows the distribution of trade PnL; the cumulative curve shows equity growth over time.")
    st.markdown('<div class="sub-header">⏰ Trades by Hour</div>', unsafe_allow_html=True)
    if 'entry_time' in trades_df.columns:
        trades_df['hour'] = trades_df['entry_time'].dt.hour
        hourly = trades_df.groupby('hour').agg({
            'pnl': ['count', 'sum', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        hourly.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
        hourly = hourly.reset_index()
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Trades by Hour", "PnL by Hour"))
        fig.add_trace(go.Bar(x=hourly['hour'], y=hourly['trades'], name="Trades", marker_color='#00ccff'), row=1, col=1)
        fig.add_trace(go.Bar(x=hourly['hour'], y=hourly['total_pnl'], name="Total PnL", marker_color='#00ff88'), row=1, col=2)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Identify which hours yield the most trades and highest PnL.")
    st.markdown('<div class="sub-header">📊 Strategy Performance</div>', unsafe_allow_html=True)
    if 'strategy' in trades_df.columns:
        strategy_perf = trades_df.groupby('strategy').agg({
            'pnl': ['count', 'sum', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        strategy_perf.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
        strategy_perf = strategy_perf.reset_index()
        fig = px.bar(strategy_perf, x='strategy', y='total_pnl', color='win_rate',
                     text='trades', title="Strategy Performance",
                     labels={'total_pnl': 'Total PnL ($)', 'win_rate': 'Win Rate (%)'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Compare strategies by total PnL, win rate, and number of trades.")

# ============================================================================
# PAGE: INSIGHTS (unchanged)
# ============================================================================
elif page == "📊 Insights":
    st.markdown('<div class="main-header">📊 Research Insights</div>', unsafe_allow_html=True)
    insights = load_insights()
    if not insights:
        st.warning("No insights found. Run research_database_jsonl.py first.")
        st.stop()
    if 'best_dna_for_sharpe' in insights:
        st.markdown('<div class="sub-header">🧬 Best DNA for Sharpe Ratio</div>', unsafe_allow_html=True)
        best_dna = insights['best_dna_for_sharpe']
        for key, value in best_dna.items():
            st.markdown(f"""
            **{key.capitalize()}**: Best Range {value.get('best_range', 'N/A')}
            Win Rate: {value.get('win_rate', 0):.1f}% | Avg PnL: ${value.get('avg_pnl', 0):.2f} | Trades: {value.get('trades', 0)}
            """)
    if 'strategy_performance' in insights:
        st.markdown('<div class="sub-header">📊 Strategy Performance</div>', unsafe_allow_html=True)
        strat_perf = insights['strategy_performance']
        if isinstance(strat_perf, dict):
            df_strat = pd.DataFrame(strat_perf).T
            st.dataframe(df_strat, use_container_width=True)
    if 'best_hours' in insights:
        st.markdown('<div class="sub-header">⏰ Best Trading Hours</div>', unsafe_allow_html=True)
        best_hours = insights['best_hours']
        if isinstance(best_hours, dict):
            df_hours = pd.DataFrame(best_hours).T
            st.dataframe(df_hours, use_container_width=True)
    if 'top_parameters' in insights:
        st.markdown('<div class="sub-header">🎯 Top Parameters</div>', unsafe_allow_html=True)
        top_params = insights['top_parameters']
        if top_params:
            df_params = pd.DataFrame(top_params)
            st.dataframe(df_params, use_container_width=True)

# ============================================================================
# PAGE: LIVE P&L (unchanged)
# ============================================================================
elif page == "📈 Live P&L":
    st.markdown('<div class="main-header">📈 Live P&L Tracking</div>', unsafe_allow_html=True)
    sessions = load_live_sessions()
    if not sessions:
        st.warning("No live sessions found. Run the live engine first.")
        st.stop()
    session_ids = [s['session_id'] for s in sessions]
    selected_session = st.selectbox("Select Live Session", session_ids)
    session_data = next(s for s in sessions if s['session_id'] == selected_session)
    df = session_data['equity_df']
    if df.empty:
        st.warning("No equity data in this session.")
        st.stop()
    col1, col2, col3, col4 = st.columns(4)
    start_equity = df['equity'].iloc[0]
    end_equity = df['equity'].iloc[-1]
    max_equity = df['equity'].max()
    min_equity = df['equity'].min()
    change_pct = (end_equity - start_equity) / start_equity * 100 if start_equity != 0 else 0
    drawdown = (max_equity - min_equity) / max_equity * 100 if max_equity != 0 else 0
    with col1:
        st.metric("Start Equity", f"${start_equity:,.2f}")
    with col2:
        st.metric("End Equity", f"${end_equity:,.2f}", delta=f"{change_pct:+.2f}%")
    with col3:
        st.metric("Max Equity", f"${max_equity:,.2f}")
    with col4:
        st.metric("Max Drawdown", f"{drawdown:.2f}%")
    st.markdown('<div class="sub-header">📈 Equity Curve</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['equity'],
                             mode='lines', name='Equity',
                             line=dict(color='#00ff88', width=3),
                             fill='tozeroy', fillcolor='rgba(0,255,136,0.1)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df.get('balance', df['equity']),
                             mode='lines', name='Balance',
                             line=dict(color='#00ccff', width=2, dash='dash')))
    fig.update_layout(height=500,
                      title="Equity and Balance Over Time",
                      xaxis_title="Time",
                      yaxis_title="Value ($)",
                      hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="sub-header">📊 Open Positions</div>', unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['timestamp'], y=df['open_positions'],
                              mode='lines+markers', name='Open Positions',
                              line=dict(color='#a855f7', width=2),
                              marker=dict(size=4)))
    fig2.update_layout(height=300,
                       xaxis_title="Time",
                       yaxis_title="Number of Positions")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('<div class="sub-header">📋 Recent Trade Events</div>', unsafe_allow_html=True)
    trade_events = session_data.get('trade_events', pd.DataFrame())
    if not trade_events.empty:
        trade_events['event_time'] = pd.to_datetime(trade_events['event_time'])
        display = trade_events.sort_values('event_time', ascending=False).head(20)
        cols = ['event_time', 'event_type', 'symbol', 'action', 'entry_price', 'exit_price', 'pnl']
        available = [c for c in cols if c in display.columns]
        st.dataframe(display[available], use_container_width=True)
    else:
        st.info("No trade events in this session.")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("*🧬 SYNTHX Dashboard – Interactive Research Platform*")