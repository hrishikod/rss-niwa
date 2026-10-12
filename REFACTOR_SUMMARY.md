# RSS NIWA refactor summary

_Status as of 12 October 2026_

## What changed

- **Databricks bundle:** The bundle is named `rss-niwa` and defines one simulation job and one Streamlit app. The job uses a classic job cluster because serverless Jobs compute is unavailable in this workspace. The app name is controlled by a bundle variable.
- **Notebook entry points:** `src/run_pipeline_job.py` and `databricks_runner_example.py` are Databricks notebooks. They read the existing catchment and prepared RAMM road CSVs from `dbfs:/FileStore/rss_niwa/InputData/`, run `rss_core`, and write `stream_risks` and `coastal_risks` Delta tables in `hive_metastore.rss_niwa`. Output column names are normalized for Delta. Both notebooks now add the deployed bundle root to Python's import path so they can find `rss_core`.
- **Map coordinates:** `scripts/build_map_points.py` creates `InputData/NzsegmentMapPoints.csv` from the WGS84 subcatchment polygons and terminal points. `rss_core.attach_map_points` joins those coordinates to model results by `nzsegment`, with a subcatchment fallback for terminal IDs without a terminal point.
- **Map output:** Both notebooks generate interactive Leaflet HTML and save it as `dbfs:/FileStore/rss_niwa/visualisations/<scenario>.html`. The current map shows representative points, not full subcatchment polygons or road lines.
- **Databricks app:** The Streamlit app lists saved scenario maps from DBFS and displays the selected HTML file. It shows an empty state when no map has been saved. Its source and launch command are in `app/`.

## What the model documentation clarified

The NIWA RSS V.4 report identifies `nzsegment` as a REC 2.4 **stream segment and subcatchment ID**. `RAMMsegments.csv` already contains road subsections created by intersecting RAMM centrelines with REC subcatchments and urban/rural land cover. The current calculation code consumes those prepared rows, aggregates road loads by `nzsegment`, and routes loads downstream. The map lookup uses WGS84 longitude and latitude (EPSG:4326); Leaflet displays them over Web Mercator tiles.

## Current deployment status

- The Databricks app has started and displayed its page, but the last observed page could not find `/FileStore/rss_niwa/visualisations`. No successful save of a scenario HTML map has been confirmed.
- An interactive run of `run_pipeline_job` failed at `import rss_core`. The import-path fix is present locally. A later `databricks bundle deploy` timed out during a Workspace `mkdirs` request, so that fix has **not been confirmed deployed**.
- The input files and generated map lookup are ignored by Git. Their presence in local `InputData/` does not establish that all three files are present in DBFS.
- A successful end-to-end Databricks job run and populated app map remain unconfirmed.

## Next steps

1. **Confirm DBFS inputs:** Check that `CatchmentDataREC2_4.csv`, `RAMMsegments.csv`, and `NzsegmentMapPoints.csv` exist under `dbfs:/FileStore/rss_niwa/InputData/`. Generate and upload the lookup if needed:

   ```bash
   uv run python scripts/build_map_points.py
   databricks fs cp InputData/NzsegmentMapPoints.csv dbfs:/FileStore/rss_niwa/InputData/NzsegmentMapPoints.csv --overwrite -p DEV-AAM
   ```

2. **Deploy the updated job and run it:** Retry after the Workspace API timeout. Chain the commands so the job cannot run against an older deployment:

   ```bash
   databricks bundle deploy --select jobs.rss_model_simulation_job -p DEV-AAM -t dev &&
   databricks bundle run rss_model_simulation_job -p DEV-AAM -t dev
   ```

3. **Confirm outputs:** The job should report `Saved visualizer to dbfs:/FileStore/rss_niwa/visualisations/default_simulation.html`. Confirm the two Hive metastore tables were written, then refresh the app. Its scenario list is cached for up to 60 seconds.
4. **Improve the map if needed:** Join stream results to `SubCatchWGS84.shp` polygons for a true subcatchment risk map. Keep terminal points for coastal results. This is a visualisation change; the current risk calculation need not change for it.
5. **Consider a new road input pipeline later:** To replace prepared `RAMMsegments.csv` with `barry.simple_vertices`, first intersect those road geometries with REC subcatchments and urban/rural areas, then attach traffic attributes and produce the fields expected by `rss_core`. This is a separate input-preparation refactor and has not been implemented.

The report used for the spatial interpretation is the local PDF `Final draft to WK, Sept 13, 2020.pdf`, whose title page identifies it as the September 2021 RSS V.4 report; see sections 3.3.1–3.3.3.
