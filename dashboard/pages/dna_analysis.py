import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.utils import load_dna_results

def show():
    st.markdown('<div class="main-header">🧬 DNA Analysis</div>', unsafe_allow_html=True)
    dna_data = load_dna_results()
    if not dna_data:
        st.warning("No DNA data found. Run dna_analyzer.py first.")
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
            parts = key.split('_')
            if len(parts) >= 2:
                available_symbols.add(parts[0])
                available_timeframes.add(parts[1])
    available_symbols = sorted(available_symbols)
    available_timeframes = sorted(available_timeframes)
    
    # Use sidebar filters; if empty, set defaults
    if 'selected_symbols' not in st.session_state:
        st.session_state.selected_symbols = available_symbols[:3]
    if 'selected_timeframes' not in st.session_state:
        st.session_state.selected_timeframes = available_timeframes[:1]
    
    selected_symbols = st.session_state.selected_symbols
    selected_timeframes = st.session_state.selected_timeframes
    
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
    
    # DNA Comparison Heatmap
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
    
    # Strategy Affinity
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
                st.info("No strategy affinity data available for this DNA profile.")