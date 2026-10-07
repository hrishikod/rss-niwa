"""
Job task entry point for Databricks execution.
Loads input datasets, runs rss_core simulation pipeline, and persists gold Delta tables.
"""
import argparse
import sys
import os

# Add repo root to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyspark.sql import SparkSession
import pandas as pd
from rss_core import run_rss_pipeline, RSSParameters, generate_interactive_map_html


def main():
    parser = argparse.ArgumentParser(description="Run RSS Model in Databricks")
    parser.add_argument("--scenario", default="default_simulation", help="Scenario run name")
    parser.add_argument("--catalog", default="main", help="Unity Catalog name")
    parser.add_argument("--schema", default="rss_niwa", help="Schema name")
    args = parser.parse_args()

    spark = SparkSession.builder.getOrCreate()
    print(f"=== Starting RSS Model Job: Scenario '{args.scenario}' ===")

    # 1. Load inputs from Delta tables if available, else fallback to files
    try:
        catch_df = spark.table(f"{args.catalog}.{args.schema}.bronze_catchments").toPandas()
        road_df = spark.table(f"{args.catalog}.{args.schema}.bronze_roads").toPandas().set_index("Concat_ID")
        print("Loaded inputs from Delta tables.")
    except Exception as e:
        print(f"Could not load Delta tables ({e}). Loading from CSV...")
        catch_df = pd.read_csv("InputData/CatchmentDataREC2_4.csv", encoding="latin1")
        road_df = pd.read_csv("InputData/RAMMsegments.csv", encoding="latin1").set_index("Concat_ID")

    # 2. Run simulation pipeline
    result = run_rss_pipeline(
        catchment_df=catch_df,
        road_df=road_df,
        params=RSSParameters(),
        verbose=True
    )

    # 3. Write results to Delta Lake
    stream_spark_df = spark.createDataFrame(result.stream_results)
    coastal_spark_df = spark.createDataFrame(result.coastal_results)

    stream_table = f"{args.catalog}.{args.schema}.gold_stream_risks_{args.scenario}"
    coastal_table = f"{args.catalog}.{args.schema}.gold_coastal_risks_{args.scenario}"

    print(f"Writing stream risks to {stream_table}...")
    stream_spark_df.write.format("delta").mode("overwrite").saveAsTable(stream_table)

    print(f"Writing coastal risks to {coastal_table}...")
    coastal_spark_df.write.format("delta").mode("overwrite").saveAsTable(coastal_table)

    # 4. Generate visualization HTML and save to DBFS / volume
    html_str = generate_interactive_map_html(
        result.stream_results,
        result.coastal_results,
        title=f"NIWA RSS Model - {args.scenario}"
    )

    out_html_path = f"/Volumes/{args.catalog}/{args.schema}/visualisations/{args.scenario}.html"
    try:
        with open(out_html_path, "w", encoding="utf-8") as f:
            f.write(html_str)
        print(f"Saved visualizer to volume: {out_html_path}")
    except Exception:
        # Fallback to local file
        with open(f"{args.scenario}_visualiser.html", "w", encoding="utf-8") as f:
            f.write(html_str)
        print(f"Saved local visualizer: {args.scenario}_visualiser.html")

    print("=== Simulation job complete. ===")


if __name__ == "__main__":
    main()

