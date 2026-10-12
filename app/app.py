"""Display RSS maps saved by the Databricks notebooks and job."""

import os

import streamlit as st
import streamlit.components.v1 as components
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config


st.set_page_config(page_title="NIWA RSS Model", page_icon="🌊", layout="wide")

schema = os.getenv("RSS_SCHEMA", "rss_niwa")
map_directory = f"/FileStore/{schema}/visualisations"


@st.cache_resource
def workspace_client() -> WorkspaceClient:
    return WorkspaceClient(config=Config())


@st.cache_data(ttl=60)
def available_maps() -> list[str]:
    if not workspace_client().dbfs.exists(map_directory):
        return []
    return sorted(
        info.path.rsplit("/", 1)[-1].removesuffix(".html")
        for info in workspace_client().dbfs.list(map_directory)
        if info.path and info.path.endswith(".html") and not info.is_dir
    )


st.title("NIWA RSS Model")
st.caption("Interactive maps from completed RSS model runs")

try:
    scenarios = available_maps()
except Exception as error:
    st.error(f"Could not read maps from DBFS: {error}")
    st.stop()

if not scenarios:
    st.info(
        f"No maps have been saved at `dbfs:{map_directory}` yet. "
        "Run the final map cell in the RSS notebook or the simulation job, then refresh this page."
    )
    st.stop()

scenario = st.selectbox("Scenario", scenarios, index=len(scenarios) - 1)
map_path = f"{map_directory}/{scenario}.html"

try:
    with workspace_client().dbfs.download(map_path) as map_file:
        html = map_file.read().decode("utf-8")
except Exception as error:
    st.error(f"Could not load {scenario}: {error}")
    st.stop()

components.html(html, height=680, scrolling=True)
