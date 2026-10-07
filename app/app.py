"""
Databricks App: Streamlit interactive frontend for the NIWA RSS Model.
Allows selecting scenarios, triggering runs, and viewing the interactive Leaflet map.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import sys

# Ensure rss_core is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rss_core import run_rss_pipeline, RSSParameters, generate_interactive_map_html

st.set_page_config(
    page_title="NIWA RSS Model - Databricks App",
    page_icon="🌊",
    layout="wide"
)

st.title("🌊 NIWA RSS Model: Road & Stream Contaminant Assessment")
st.markdown("Interactive screening tool for Zinc ($\text{Zn}$) and Copper ($\text{Cu}$) accumulation across New Zealand catchments.")

# Sidebar controls
st.sidebar.header("Simulation Settings")
scenario_name = st.sidebar.text_input("Scenario Name", value="databricks_test")
colour_ramp = st.sidebar.selectbox("Color Palette", ["traffic", "blind"])

st.sidebar.markdown("---")
st.sidebar.subheader("Urban Source Control")
source_control = st.sidebar.checkbox("Apply Roof Source Control", value=False)

if st.sidebar.button("🚀 Run Simulation", type="primary"):
    with st.spinner("Running model pipeline..."):
        try:
            # Load inputs (from Delta or local sample)
            catch_path = "InputData/CatchmentDataREC2_4.csv"
            road_path = "InputData/RAMMsegments.csv"
            
            if os.path.exists(catch_path) and os.path.exists(road_path):
                catch_df = pd.read_csv(catch_path, encoding="latin1")
                road_df = pd.read_csv(road_path, encoding="latin1").set_index("Concat_ID")
                
                params = RSSParameters()
                result = run_rss_pipeline(catch_df, road_df, params=params, verbose=False)
                
                st.session_state["result"] = result
                st.success(f"Simulation completed in {result.elapsed_seconds:.1f} seconds!")
            else:
                st.error("Input data files not found in workspace.")
        except Exception as e:
            st.error(f"Simulation error: {e}")

# Render map if result exists
if "result" in st.session_state:
    result = st.session_state["result"]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Stream Reaches", f"{len(result.stream_results):,}")
    col2.metric("Coastal Reaches", f"{len(result.coastal_results):,}")
    col3.metric("Computation Time", f"{result.elapsed_seconds:.1f}s")
    
    html_map = generate_interactive_map_html(
        result.stream_results,
        result.coastal_results,
        title=f"NIWA RSS Model: {scenario_name}"
    )
    
    components.html(html_map, height=750, scrolling=True)
else:
    st.info("👈 Configure parameters on the left and click **Run Simulation** to generate the interactive map.")

