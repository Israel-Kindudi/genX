# dashboard/app.py (new section)

import streamlit as st
import pandas as pd
from mining.pipeline import DataMiningPipeline

def show_mining_results():
    st.subheader("🔬 Data Mining Insights")

    if st.button("Run Data Mining (may take a while)"):
        with st.spinner("Running data mining..."):
            pipeline = DataMiningPipeline()
            results = pipeline.run()
            pipeline.save_results()

        # Display results
        st.write("### Feature Importance")
        fig = pipeline.model_results['feature_importance'].plot(kind='bar', x='feature', y='importance')
        st.pyplot(fig)

        st.write("### Regime Performance")
        st.dataframe(results['regime_performance'])
        # Validation Results Section
st.subheader("✅ Strategy Validation Results")

# Load validation results
validation_file = "validation_results/validation_summary.csv"
if os.path.exists(validation_file):
    df_val = pd.read_csv(validation_file)
    st.dataframe(df_val, use_container_width=True)
    
    # Show deployment readiness
    readiness_file = "validation_results/deployment_readiness.csv"
    if os.path.exists(readiness_file):
        df_ready = pd.read_csv(readiness_file)
        st.subheader("🚀 Deployment Readiness")
        st.dataframe(df_ready, use_container_width=True)
else:
    st.info("Run validation first: python validation/validator.py")