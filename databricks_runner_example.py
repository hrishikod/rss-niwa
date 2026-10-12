# Databricks notebook source
# MAGIC %md
# MAGIC # NIWA RSS Model: Databricks runner example
# MAGIC
# MAGIC Reads the input CSVs, runs the RSS simulation, writes results to Delta, and maps them using an `nzsegment` coordinate lookup.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configure the run

# COMMAND ----------

dbutils.widgets.text("schema", "rss_niwa", "Schema")
dbutils.widgets.text("scenario", "databricks_example", "Scenario name")

schema = dbutils.widgets.get("schema")
scenario = dbutils.widgets.get("scenario")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load CSV inputs from DBFS

# COMMAND ----------

import pandas as pd
import re

input_dir = "/dbfs/FileStore/rss_niwa/InputData"
catchment_df = pd.read_csv(
    f"{input_dir}/CatchmentDataREC2_4.csv", encoding="latin1"
)
road_df = (
    pd.read_csv(f"{input_dir}/RAMMsegments.csv", encoding="latin1")
    .set_index("Concat_ID")
)

print(f"Loaded {len(catchment_df):,} catchments and {len(road_df):,} road segments")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run the model

# COMMAND ----------

import sys
from pathlib import Path

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
bundle_root = (Path("/Workspace") / notebook_path.lstrip("/")).parent
if not (bundle_root / "rss_core").is_dir():
    raise FileNotFoundError(f"rss_core package not found at {bundle_root / 'rss_core'}")
sys.path.insert(0, str(bundle_root))

from rss_core import RSSParameters, run_rss_pipeline

result = run_rss_pipeline(
    catchment_df=catchment_df,
    road_df=road_df,
    params=RSSParameters(),
    verbose=True,
)

print(f"Stream simulation generated: {len(result.stream_results):,} records")
print(f"Coastal simulation generated: {len(result.coastal_results):,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save results to Delta

# COMMAND ----------

spark.sql(f"CREATE DATABASE IF NOT EXISTS `hive_metastore`.`{schema}`")

stream_table = f"hive_metastore.{schema}.stream_risks"
coastal_table = f"hive_metastore.{schema}.coastal_risks"

def delta_safe_columns(dataframe):
    dataframe = dataframe.copy()
    dataframe.columns = [
        re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", name)).strip("_")
        for name in dataframe.columns
    ]
    if len(dataframe.columns) != len(set(dataframe.columns)):
        raise ValueError("Column name normalization produced duplicate names")
    return dataframe


spark.createDataFrame(delta_safe_columns(result.stream_results)).write.format("delta").mode("overwrite").saveAsTable(stream_table)
spark.createDataFrame(delta_safe_columns(result.coastal_results)).write.format("delta").mode("overwrite").saveAsTable(coastal_table)

print(f"Saved {stream_table} and {coastal_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display the interactive map
# MAGIC
# MAGIC The map lookup is generated from `InputShapes/SubCatchWGS84.shp` and `InputShapes/TerminalsWGS84.shp` and uploaded to `dbfs:/FileStore/rss_niwa/InputData/NzsegmentMapPoints.csv`.

# COMMAND ----------

from rss_core import attach_map_points, generate_interactive_map_html

mapped_stream, mapped_coastal = attach_map_points(
    result.stream_results,
    result.coastal_results,
    f"{input_dir}/NzsegmentMapPoints.csv",
)
print(
    f"Mapped {mapped_stream['lat'].notna().sum():,} stream and "
    f"{mapped_coastal['lat'].notna().sum():,} coastal reaches"
)

html_content = generate_interactive_map_html(
    mapped_stream,
    mapped_coastal,
    title=f"NIWA RSS Model - {scenario}",
)

visualizer_directory = f"dbfs:/FileStore/{schema}/visualisations"
visualizer_path = f"{visualizer_directory}/{scenario}.html"
dbutils.fs.mkdirs(visualizer_directory)
dbutils.fs.put(visualizer_path, html_content, overwrite=True)
print(f"Saved map to {visualizer_path}")

displayHTML(html_content)
