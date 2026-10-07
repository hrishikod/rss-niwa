"""
Databricks Notebook & Databricks App Example.

Demonstrates how to run the refactored NIWA RSS Model in Databricks:
1. Loading input data from Delta tables / Parquet / CSV.
2. Executing the modular pipeline.
3. Writing results back to Delta tables.
4. Rendering the interactive visualizer in Databricks Apps (or notebooks via displayHTML).
"""
import pandas as pd
from rss_core import run_rss_pipeline, RSSParameters, generate_interactive_map_html

# ==============================================================================
# 1. LOAD INPUT DATA (From Spark/Delta or Pandas)
# ==============================================================================
# In Databricks, load from Delta tables:
# catch_df = spark.table("bronze_catchment_rec2_4").toPandas()
# road_df = spark.table("bronze_ramm_segments").toPandas()

# Local / Parquet fallback:
catch_df = pd.read_csv("InputData/CatchmentDataREC2_4.csv", encoding="latin1")
road_df = pd.read_csv("InputData/RAMMsegments.csv", encoding="latin1").set_index("Concat_ID")

# ==============================================================================
# 2. RUN MODEL WITH CUSTOM PARAMETERS (Optional)
# ==============================================================================
params = RSSParameters()  # or RSSParameters.from_dict({"ZnVEF1": 0.35})

result = run_rss_pipeline(
    catchment_df=catch_df,
    road_df=road_df,
    params=params,
    verbose=True
)

# ==============================================================================
# 3. SAVE RESULTS TO DELTA LAKE (In Databricks)
# ==============================================================================
# spark.createDataFrame(result.stream_results).write.format("delta").mode("overwrite").saveAsTable("gold_stream_risks")
# spark.createDataFrame(result.coastal_results).write.format("delta").mode("overwrite").saveAsTable("gold_coastal_risks")

print(f"Stream simulation generated: {len(result.stream_results):,} records")
print(f"Coastal simulation generated: {len(result.coastal_results):,} records")

# ==============================================================================
# 4. RENDER FOR DATABRICKS APPS (Streamlit / Dash / displayHTML)
# ==============================================================================
# In a Databricks Notebook:
# displayHTML(generate_interactive_map_html(result.stream_results, result.coastal_results))

# For a Databricks App (HTML file output):
html_content = generate_interactive_map_html(
    result.stream_results,
    result.coastal_results,
    title="Databricks App - NIWA RSS Model"
)

with open("databricks_app_visualiser.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Exported Databricks App visualizer: databricks_app_visualiser.html")

