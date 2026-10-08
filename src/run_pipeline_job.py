# Databricks notebook source
# MAGIC %md
# MAGIC # NIWA RSS Model simulation job
# MAGIC
# MAGIC Loads the source tables, runs the model for the selected scenario, writes the results to Delta, and saves an interactive map.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Job parameters

# COMMAND ----------

dbutils.widgets.text("scenario_name", "default_simulation", "Scenario name")
dbutils.widgets.text("schema", "rss_niwa", "Schema")

scenario = dbutils.widgets.get("scenario_name")
schema = dbutils.widgets.get("schema")

print(f"=== Starting RSS Model Job: Scenario '{scenario}' ===")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load inputs
# MAGIC
# MAGIC Reads `<schema>.bronze_catchments` and `<schema>.bronze_roads` from the Hive metastore. If those tables are unavailable, it reads the CSV files uploaded to `dbfs:/FileStore/rss_niwa/InputData/`.

# COMMAND ----------

import pandas as pd

try:
    catchment_df = spark.table(f"{schema}.bronze_catchments").toPandas()
    road_df = (
        spark.table(f"{schema}.bronze_roads")
        .toPandas()
        .set_index("Concat_ID")
    )
    print("Loaded inputs from Delta tables.")
except Exception as error:
    print(f"Could not load Hive tables ({error}). Loading CSV files from DBFS...")
    input_dir = "/dbfs/FileStore/rss_niwa/InputData"
    catchment_df = pd.read_csv(
        f"{input_dir}/CatchmentDataREC2_4.csv", encoding="latin1"
    )
    road_df = (
        pd.read_csv(f"{input_dir}/RAMMsegments.csv", encoding="latin1")
        .set_index("Concat_ID")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run the model

# COMMAND ----------

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

stream_table = f"{schema}.gold_stream_risks_{scenario}"
coastal_table = f"{schema}.gold_coastal_risks_{scenario}"

spark.createDataFrame(result.stream_results).write.format("delta").mode("overwrite").saveAsTable(stream_table)
spark.createDataFrame(result.coastal_results).write.format("delta").mode("overwrite").saveAsTable(coastal_table)

print(f"Saved {stream_table} and {coastal_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save and display the interactive map

# COMMAND ----------

from rss_core import generate_interactive_map_html

html_content = generate_interactive_map_html(
    result.stream_results,
    result.coastal_results,
    title=f"NIWA RSS Model - {scenario}",
)

visualizer_path = f"dbfs:/FileStore/{schema}/visualisations/{scenario}.html"
dbutils.fs.mkdirs(f"dbfs:/FileStore/{schema}/visualisations")
dbutils.fs.put(visualizer_path, html_content, overwrite=True)
print(f"Saved visualizer to {visualizer_path}")

displayHTML(html_content)

# COMMAND ----------

print("=== Simulation job complete. ===")
