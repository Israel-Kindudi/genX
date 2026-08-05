import streamlit as st

def apply_custom_css():
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
        .glow-text { animation: glow 3s infinite; }
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
        .positive { color: #00ff88 !important; -webkit-text-fill-color: #00ff88 !important; }
        .negative { color: #ff4444 !important; -webkit-text-fill-color: #ff4444 !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 1.5rem; }
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
        .pillar-icon { font-size: 3rem; margin-bottom: 0.5rem; }
        .pillar-title { font-weight: 600; color: #e2e8f0; font-size: 1.1rem; }
        .pillar-desc { font-size: 0.9rem; color: #a0aec0; margin-top: 0.3rem; }
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

def color_pnl(val):
    if isinstance(val, (int, float)):
        color = '#00ff88' if val > 0 else '#ff4444' if val < 0 else 'white'
        return f'color: {color}'
    return ''