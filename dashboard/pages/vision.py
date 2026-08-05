import streamlit as st
from dashboard.utils import load_dna_results, load_all_trades, load_live_sessions

def show():
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