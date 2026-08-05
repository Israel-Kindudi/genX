"""
SYNTHX Interactive Dashboard – Modular Entry Point
Uses relative imports for robustness.
"""

import sys
import os

# ---- Add project root to sys.path for absolute imports (fallback) ----
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---- Use relative imports within the dashboard package ----
import streamlit as st
from datetime import datetime

# Relative imports (work when run as a module: python -m dashboard.app)
from dashboard.utils import apply_custom_css, load_dna_results
from dashboard.pages import vision, overview, dna_analysis, backtest_results, optimization, trade_analytics, insights, live_pnl

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================
st.set_page_config(
    page_title="SYNTHX Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()

# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.title("🧬 SYNTHX")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏛️ GenX Vision", "📊 Overview", "🧬 DNA Analysis", "📈 Backtest Results",
     "🎯 Optimization", "💳 Trade Analytics", "📊 Insights", "📈 Live P&L"]
)

st.sidebar.markdown("---")

# Data source filter
st.sidebar.subheader("Data Source")
source_filter = st.sidebar.selectbox(
    "Show trades from",
    ["All", "Backtest Only", "Live Only"],
    index=0
)

# DNA Filters
st.sidebar.subheader("DNA Filters")
dna_data = load_dna_results()
available_symbols = sorted(set(
    data.get('_normalised_symbol', key.split('_')[0])
    for key, data in dna_data.items()
)) if dna_data else []
available_timeframes = sorted(set(
    data.get('_normalised_timeframe', key.split('_')[1] if len(key.split('_')) > 1 else '')
    for key, data in dna_data.items()
)) if dna_data else []

if available_symbols:
    selected_symbols = st.sidebar.multiselect(
        "Symbols",
        available_symbols,
        default=available_symbols[:3] if available_symbols else []
    )
else:
    selected_symbols = []

if available_timeframes:
    selected_timeframes = st.sidebar.multiselect(
        "Timeframes",
        available_timeframes,
        default=available_timeframes[:1] if available_timeframes else []
    )
else:
    selected_timeframes = []

st.session_state.selected_symbols = selected_symbols
st.session_state.selected_timeframes = selected_timeframes
st.session_state.source_filter = source_filter

if page in ["📊 Overview", "📈 Live P&L"]:
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh live data", value=False)
    if auto_refresh:
        refresh_interval = st.sidebar.slider("Refresh interval (seconds)", min_value=5, max_value=60, value=10)
        try:
            import streamlit_autorefresh as st_autorefresh
            st_autorefresh.st_autorefresh(interval=refresh_interval * 1000, key="autorefresh")
        except:
            pass

st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# PAGE DISPATCH
# ============================================================================
if page == "🏛️ GenX Vision":
    vision.show()
elif page == "📊 Overview":
    overview.show()
elif page == "🧬 DNA Analysis":
    dna_analysis.show()
elif page == "📈 Backtest Results":
    backtest_results.show()
elif page == "🎯 Optimization":
    optimization.show()
elif page == "💳 Trade Analytics":
    trade_analytics.show()
elif page == "📊 Insights":
    insights.show()
elif page == "📈 Live P&L":
    live_pnl.show()

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("*🧬 SYNTHX Dashboard – Interactive Research Platform*")