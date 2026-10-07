"""
rss_core: Modular, headless implementation of the NIWA Road Stormwater Screening (RSS) Model.
Ready for Databricks notebooks, Databricks Apps, and local workflows.
"""
from .config import RSSParameters
from .emissions import calculate_road_emissions, calculate_urban_emissions
from .accumulator import accumulate_network_loads
from .risk import calculate_stream_risk, calculate_coastal_risk
from .pipeline import run_rss_pipeline, RSSModelResult
from .visualizer import generate_interactive_map_html

__all__ = [
    "RSSParameters",
    "calculate_road_emissions",
    "calculate_urban_emissions",
    "accumulate_network_loads",
    "calculate_stream_risk",
    "calculate_coastal_risk",
    "run_rss_pipeline",
    "RSSModelResult",
    "generate_interactive_map_html"
]

