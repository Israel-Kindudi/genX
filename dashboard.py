"""
SYNTHX Interactive Dashboard
Visualizes DNA profiles, backtest results, optimization outcomes, live trading, and trade analytics.
Enhanced with Hero Page, Live PnL tracking, and rich explanations.
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
from datetime import datetime
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
# STYLING – Enhanced with animations & gradients
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Space Grotesk', sans-serif;
    }
    
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
    
    .footer {
        margin-top: 3rem;
        padding: 1.5rem 0;
        border-top: 1px solid #2d3748;
        text-align: center;
        color: #718096;
        font-size: 0.9rem;
    }
    
    /* Dark scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        background: #0a0a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: #2d3748;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #00ff88;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING FUNCTIONS (cached)
# ============================================================================

@st.cache_data
def load_dna_results():
    dna_files = glob.glob("dna_results/*_DNA.json")
    results = {}
    for file in dna_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                symbol = data.get('symbol', os.path.basename(file).replace('_DNA.json', ''))
                timeframe = data.get('timeframe', 'unknown')
                key = f"{symbol}_{timeframe}"
                results[key] = data
        except:
            continue
    return results

@st.cache_data
def load_optimization_results():
    opt_file = "optimization_results/optimization_results.json"
    if os.path.exists(opt_file):
        with open(opt_file, 'r') as f:
            return json.load(f)
    return []

@st.cache_data
def load_trades():
    trades_file = "research_data/trades.jsonl"
    if not os.path.exists(trades_file):
        return pd.DataFrame()
    trades = []
    with open(trades_file, 'r') as f:
        for line in f:
            try:
                trades.append(json.loads(line.strip()))
            except:
                continue
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    for col in ['entry_time', 'exit_time', 'created_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df

@st.cache_data
def load_insights():
    insights_file = "research_data/insights.json"
    if os.path.exists(insights_file):
        with open(insights_file, 'r') as f:
            return json.load(f)
    return {}

@st.cache_data
def load_live_sessions():
    """List all live_result sessions and load equity data from events.jsonl."""
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
                        except:
                            continue
                if equity_data:
                    df_equity = pd.DataFrame(equity_data)
                    df_equity['timestamp'] = pd.to_datetime(df_equity['timestamp'])
                    sessions.append({
                        'session_id': folder,
                        'path': session_path,
                        'equity_df': df_equity,
                        'trade_events': []  # we can load trade events separately if needed
                    })
    return sessions

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("🧬 SYNTHX")
st.sidebar.markdown("---")

# Navigation – with Hero first
page = st.sidebar.radio(
    "Navigation",
    ["🏛️ GenX Vision", "📊 Overview", "🧬 DNA Analysis", "📈 Backtest Results", 
     "🎯 Optimization", "💳 Trade Analytics", "📊 Insights", "📈 Live P&L"]
)

st.sidebar.markdown("---")

# Filters
st.sidebar.subheader("Filters")
symbols = []
dna_data = load_dna_results()
for key in dna_data.keys():
    if '_' in key:
        sym = key.split('_')[0]
        if sym not in symbols:
            symbols.append(sym)

if symbols:
    selected_symbols = st.sidebar.multiselect(
        "Symbols",
        symbols,
        default=symbols[:1] if symbols else []
    )
else:
    selected_symbols = []

timeframes = ['1m', '5m', '15m', '30m', '1h', '4h']
selected_timeframes = st.sidebar.multiselect(
    "Timeframes",
    timeframes,
    default=['5m']
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# PAGE: GENX VISION (HERO)
# ============================================================================

if page == "🏛️ GenX Vision":
    st.markdown('<div class="main-header glow-text">🧬 GenX (SYNTHX)</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Where Markets Meet Genetics – A Quantitative Trading Framework</div>', unsafe_allow_html=True)
    
    # Abstract
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
    
    # Key Pillars
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
    
    # Quick stats
    dna_data = load_dna_results()
    trades_df = load_trades()
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
# PAGE: OVERVIEW (enhanced with live data)
# ============================================================================

elif page == "📊 Overview":
    st.markdown('<div class="main-header">📊 SYNTHX Overview</div>', unsafe_allow_html=True)
    
    dna_data = load_dna_results()
    trades_df = load_trades()
    insights = load_insights()
    sessions = load_live_sessions()
    
    # Metrics row
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
            <div class="metric-value">{len(trades_df):,}</div>
            <div class="metric-label">Total Trades</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        total_pnl = trades_df['pnl'].sum() if not trades_df.empty else 0
        color_class = "positive" if total_pnl >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {color_class}">${total_pnl:,.2f}</div>
            <div class="metric-label">Total PnL</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        win_rate = (trades_df['result'] == 'TP').mean() * 100 if not trades_df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{win_rate:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        profit_factor = 0
        if not trades_df.empty:
            gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{profit_factor:.2f}</div>
            <div class="metric-label">Profit Factor</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent trades
    st.markdown('<div class="sub-header">📊 Recent Trades</div>', unsafe_allow_html=True)
    if not trades_df.empty:
        recent = trades_df.sort_values('entry_time', ascending=False).head(20)
        display_cols = ['symbol', 'direction', 'entry_price', 'exit_price', 'pnl', 'result', 'strategy']
        available_cols = [c for c in display_cols if c in recent.columns]
        st.dataframe(recent[available_cols], use_container_width=True)
    else:
        st.info("No trades loaded yet. Run backtests to collect data.")
    
    # Live sessions summary
    if sessions:
        st.markdown('<div class="sub-header">📈 Live Sessions</div>', unsafe_allow_html=True)
        session_info = []
        for s in sessions:
            df = s['equity_df']
            if not df.empty:
                start_equity = df['equity'].iloc[0]
                end_equity = df['equity'].iloc[-1]
                change_pct = (end_equity - start_equity) / start_equity * 100 if start_equity != 0 else 0
                session_info.append({
                    'Session': s['session_id'],
                    'Start Equity': f"${start_equity:,.2f}",
                    'End Equity': f"${end_equity:,.2f}",
                    'Change %': f"{change_pct:+.2f}%"
                })
        st.dataframe(pd.DataFrame(session_info), use_container_width=True)

# ============================================================================
# PAGE: DNA ANALYSIS
# ============================================================================

elif page == "🧬 DNA Analysis":
    st.markdown('<div class="main-header">🧬 DNA Analysis</div>', unsafe_allow_html=True)
    
    dna_data = load_dna_results()
    
    if not dna_data:
        st.warning("No DNA data found. Run dna_analyzer.py first.")
        st.stop()
    
    # Filter DNA data
    filtered_dna = {}
    for key, data in dna_data.items():
        symbol_match = any(s in key for s in selected_symbols) if selected_symbols else True
        tf_match = any(tf in key for tf in selected_timeframes) if selected_timeframes else True
        if symbol_match and tf_match:
            filtered_dna[key] = data
    
    if not filtered_dna:
        st.warning("No DNA data matches the selected filters.")
        st.stop()
    
    # DNA Comparison Chart
    st.markdown('<div class="sub-header">DNA Comparison</div>', unsafe_allow_html=True)
    
    # Extract DNA metrics
    dna_metrics = []
    for key, data in filtered_dna.items():
        dna = data.get('dna', {})
        scores = data.get('scores', {})
        
        dna_metrics.append({
            'key': key,
            'symbol': key.split('_')[0] if '_' in key else key,
            'timeframe': key.split('_')[1] if '_' in key else 'unknown',
            'overall_score': dna.get('overall_score', 0),
            'entropy': dna.get('chromosome_vi', {}).get('normalized_entropy', 0),
            'hurst': dna.get('chromosome_ii', {}).get('hurst_exponent', 0),
            'volatility': dna.get('chromosome_iii', {}).get('realized_vol', 0),
            'jump_rate': dna.get('chromosome_iv', {}).get('jump_intensity', 0),
            'trend_length': dna.get('chromosome_vii', {}).get('avg_trend_length', 0),
            'predictability': dna.get('chromosome_vi', {}).get('predictability', 0),
            'is_synthetic': dna.get('chromosome_viii', {}).get('is_synthetic', False),
            'best_strategy': max(dna.get('strategy_affinity', {}), key=dna.get('strategy_affinity', {}).get) if dna.get('strategy_affinity') else 'N/A'
        })
    
    df_dna = pd.DataFrame(dna_metrics)
    
    # Heatmap of DNA metrics
    fig = go.Figure()
    
    metrics_to_plot = ['overall_score', 'entropy', 'hurst', 'volatility', 'jump_rate', 'trend_length', 'predictability']
    available_metrics = [m for m in metrics_to_plot if m in df_dna.columns]
    
    if available_metrics:
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
        
        fig.update_layout(
            title="DNA Metrics Heatmap",
            height=400,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Strategy Affinity
    st.markdown('<div class="sub-header">Strategy Affinity</div>', unsafe_allow_html=True)
    
    # Show strategy affinity for selected DNA
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
            st.info("No strategy affinity data available.")

# ============================================================================
# PAGE: BACKTEST RESULTS
# ============================================================================

elif page == "📈 Backtest Results":
    st.markdown('<div class="main-header">📈 Backtest Results</div>', unsafe_allow_html=True)
    
    # Load optimization results
    opt_results = load_optimization_results()
    
    if not opt_results:
        st.warning("No backtest results found. Run parameter_optimizer.py first.")
        st.stop()
    
    # Convert to DataFrame
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
            'max_drawdown': report.get('max_drawdown', 0),
            'parameters': res.get('parameters', {})
        })
    
    df_results = pd.DataFrame(rows)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        strategies = ['All'] + list(df_results['strategy'].unique())
        selected_strategy = st.selectbox("Strategy", strategies)
    
    with col2:
        symbols = ['All'] + list(df_results['symbol'].unique())
        selected_symbol = st.selectbox("Symbol", symbols)
    
    # Apply filters
    filtered_df = df_results.copy()
    if selected_strategy != 'All':
        filtered_df = filtered_df[filtered_df['strategy'] == selected_strategy]
    if selected_symbol != 'All':
        filtered_df = filtered_df[filtered_df['symbol'] == selected_symbol]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Backtests", len(filtered_df))
    with col2:
        st.metric("Avg Trades", f"{filtered_df['trades'].mean():.1f}")
    with col3:
        st.metric("Avg Win Rate", f"{filtered_df['win_rate'].mean():.1f}%")
    with col4:
        st.metric("Avg Sharpe", f"{filtered_df['sharpe'].mean():.2f}")
    
    # Scatter plot
    st.markdown('<div class="sub-header">Performance Scatter</div>', unsafe_allow_html=True)
    
    fig = px.scatter(
        filtered_df,
        x='sharpe',
        y='total_pnl',
        size='trades',
        color='strategy',
        hover_data=['symbol', 'win_rate', 'return_pct', 'max_drawdown'],
        title="Sharpe vs PnL",
        labels={'sharpe': 'Sharpe Ratio', 'total_pnl': 'Total PnL ($)'}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Results table
    st.markdown('<div class="sub-header">Results Table</div>', unsafe_allow_html=True)
    st.dataframe(
        filtered_df[['strategy', 'symbol', 'trades', 'win_rate', 'sharpe', 'total_pnl', 'return_pct', 'max_drawdown']],
        use_container_width=True
    )

# ============================================================================
# PAGE: OPTIMIZATION
# ============================================================================

elif page == "🎯 Optimization":
    st.markdown('<div class="main-header">🎯 Parameter Optimization</div>', unsafe_allow_html=True)
    
    # Load best parameters
    best_file = "optimization_results/best_parameters.csv"
    
    if os.path.exists(best_file):
        df_best = pd.read_csv(best_file)
        
        st.markdown('<div class="sub-header">Top Performing Parameter Sets</div>', unsafe_allow_html=True)
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Top Sharpe", f"{df_best['sharpe_ratio'].max():.3f}")
        with col2:
            st.metric("Top Win Rate", f"{df_best['win_rate'].max():.1f}%")
        with col3:
            st.metric("Top Return", f"{df_best['return_pct'].max():.1f}%")
        
        # Best parameters table
        st.dataframe(
            df_best[['strategy', 'symbol', 'trades', 'win_rate', 'sharpe_ratio', 'total_pnl', 'return_pct']].head(20),
            use_container_width=True
        )
        
        # Parameter visualization
        st.markdown('<div class="sub-header">Parameter Impact</div>', unsafe_allow_html=True)
        
        # Show distribution of parameters for top performers
        fig = px.scatter(
            df_best,
            x='param_lookback',
            y='sharpe_ratio',
            color='strategy',
            size='trades',
            hover_data=['param_stop', 'param_tp'],
            title="Impact of Lookback on Sharpe Ratio"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.warning("No optimization results found. Run parameter_optimizer.py first.")

# ============================================================================
# PAGE: TRADE ANALYTICS
# ============================================================================

elif page == "💳 Trade Analytics":
    st.markdown('<div class="main-header">💳 Trade Analytics</div>', unsafe_allow_html=True)
    trades_df = load_trades()
    if trades_df.empty:
        st.warning("No trades found.")
        st.stop()
    
    # Summary metrics with explanations
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", len(trades_df), help="Total number of closed trades.")
    with col2:
        win_rate = (trades_df['result'] == 'TP').mean() * 100
        st.metric("Win Rate", f"{win_rate:.1f}%", help="Percentage of trades that hit take-profit.")
    with col3:
        st.metric("Avg PnL", f"${trades_df['pnl'].mean():.2f}", help="Average profit/loss per trade.")
    with col4:
        st.metric("Total PnL", f"${trades_df['pnl'].sum():.2f}", help="Cumulative profit/loss.")
    
    # PnL Distribution
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
    
    # Trade by Hour
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
    
    # Trade by Strategy
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
# PAGE: INSIGHTS
# ============================================================================

elif page == "📊 Insights":
    st.markdown('<div class="main-header">📊 Research Insights</div>', unsafe_allow_html=True)
    
    insights = load_insights()
    
    if not insights:
        st.warning("No insights found. Run research_database_jsonl.py first.")
        st.stop()
    
    # Display insights
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
# PAGE: LIVE P&L (NEW – Fixed)
# ============================================================================

elif page == "📈 Live P&L":
    st.markdown('<div class="main-header">📈 Live P&L Tracking</div>', unsafe_allow_html=True)
    
    sessions = load_live_sessions()
    if not sessions:
        st.warning("No live sessions found. Run the live engine first.")
        st.stop()
    
    # Select session
    session_ids = [s['session_id'] for s in sessions]
    selected_session = st.selectbox("Select Live Session", session_ids)
    session_data = next(s for s in sessions if s['session_id'] == selected_session)
    
    df = session_data['equity_df']
    if df.empty:
        st.warning("No equity data in this session.")
        st.stop()
    
    # Metrics
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
        color = "normal" if change_pct >= 0 else "inverse"
        st.metric("End Equity", f"${end_equity:,.2f}", delta=f"{change_pct:+.2f}%")
    with col3:
        st.metric("Max Equity", f"${max_equity:,.2f}")
    with col4:
        st.metric("Max Drawdown", f"{drawdown:.2f}%")
    
    # Equity curve
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
    
    # Open positions count
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
    
    # Trade events
    st.markdown('<div class="sub-header">📋 Trade Events</div>', unsafe_allow_html=True)
    # Load trade events from events.jsonl
    events_file = os.path.join(session_data['path'], "events.jsonl")
    trade_events = []
    if os.path.exists(events_file):
        with open(events_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get('type') in ['trade_open', 'trade_close']:
                        # Add timestamp from top level
                        evt = event['data'].copy()
                        evt['timestamp'] = event.get('timestamp')
                        evt['event_type'] = event.get('type')
                        trade_events.append(evt)
                except:
                    continue
    if trade_events:
        df_events = pd.DataFrame(trade_events)
        df_events['timestamp'] = pd.to_datetime(df_events['timestamp'])
        df_events = df_events.sort_values('timestamp', ascending=False)
        # Select columns to display
        display_cols = ['timestamp', 'event_type', 'symbol', 'action', 'entry_price', 'exit_price', 'pnl']
        available_cols = [c for c in display_cols if c in df_events.columns]
        st.dataframe(df_events[available_cols], use_container_width=True)
    else:
        st.info("No trade events in this session.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("*🧬 SYNTHX Dashboard – Interactive Research Platform*")
st.markdown("---")