# NIWA Road Stormwater Screening (RSS) Model V4

The **Road Stormwater Screening (RSS) Model** is a spatial contaminant transport and downstream accumulation assessment tool developed by NIWA (National Institute of Water and Atmospheric Research, New Zealand) in partnership with Waka Kotahi NZ Transport Agency. 

It evaluates heavy metal accumulation—specifically **Zinc ($\text{Zn}$)** and **Copper ($\text{Cu}$)**—generated from road transport infrastructure and urban land uses across New Zealand's river networks and coastal receiving environments.

---

## 🔬 Model Overview & Contaminant Physics

### 1. Key Contaminant Sources
* **Zinc ($\text{Zinc / Zn}$)**: Primarily driven by vehicular tyre wear and galvanized roof runoff.
* **Copper ($\text{Copper / Cu}$)**: Driven by vehicle brake pad friction and urban industrial/residential impervious surfaces.

### 2. Spatial Scale & Downstream Accumulation
* **River Network**: Uses NIWA's **River Environment Classification (REC)** network covering over 590,000 subcatchment reaches (`nzsegment` IDs).
* **Coastal Terminals**: Aggregates cumulative loads downstream to over 11,000 coastal terminal reaches and estuarine receiving environments.

### 3. Risk Assessment Methodology
The model calculates sediment metal mass concentrations ($\text{mg/kg}$, equivalent to $\text{g/t}$) by dividing cumulative contaminant loads by estimated sediment yield. Concentrations are evaluated against **Threshold Effects Levels (TEL)** and **Cumulative Contaminant Units (CCU)**:

$$\text{CCU} = \frac{\text{Conc}_{\text{Zn}}}{\text{TEL}_{\text{Zn}}} + \frac{\text{Conc}_{\text{Cu}}}{\text{TEL}_{\text{Cu}}}$$

#### Risk Tiers:
* 🔴 **Highest Risk** (Score `5` / `>15`): Severe metal accumulation exceeding upper TEL guidelines.
* 🟠 **Higher Risk** (Score `3` / `15`): Substantial contaminant load relative to sediment yield.
* 🟡 **Medium Risk** (Score `2` / `9`): Moderate contaminant concentration.
* 🟢 **Lower Risk** (Score `1` / `1–8`): Low risk; contaminant detectable above background.
* 🟨 **Lowest Risk** (Score `0`): Minimal concentration.
* ⚪ **No Upstream Sources** (Score `-1`): Catchments with zero urban or roading sources.

---

## 📁 Repository Structure

```text
rss-niwa/
├── RSSModelV4_Feb2021.py       # Core model simulation logic
├── run_model.py                # Command-Line Interface (CLI) runner
├── RSS_UserInterfaceV4.py      # Legacy Tkinter GUI interface
├── InputData/                  # Hydrological & land-use lookup tables
├── InputShapes/                # Base WGS84 GIS shapefiles (REC streams, coastlines)
├── CustomTreatment/            # User-defined Load Reduction Factor (LRF) CSVs
├── Templates/                  # Standard treatment templates
├── Outputs/                    # Simulation run output directories
├── visualise_test_leaflet.html # Interactive Leaflet GIS visualizer
└── visualise_test_outputs.html # Static map scenario comparison dashboard
```

---

## 🚀 How to Run the Model

### Databricks map lookup

The Databricks notebooks map model results by joining `nzsegment` to representative points from the original WGS84 shape files. Build and upload the lookup from the repository root:

```bash
uv run python scripts/build_map_points.py
databricks fs cp InputData/NzsegmentMapPoints.csv dbfs:/FileStore/rss_niwa/InputData/NzsegmentMapPoints.csv --overwrite -p DEV-AAM
```

The lookup is used only for visualization. The stream points come from `SubCatchWGS84.shp`, and coastal points come from `TerminalsWGS84.shp` with a subcatchment fallback for missing terminals.

### 1. Command-Line Interface (CLI) — *Recommended*

Run headlessly without relying on a graphical user interface using `run_model.py`:

```bash
# Basic run (default settings)
uv run python run_model.py --name my_scenario

# Fast run (skips heavy 2.3 GB shapefiles and map images for rapid testing)
uv run python run_model.py --name fast_run --no-shape --no-images

# Custom treatment & color-blind palette
uv run python run_model.py --name custom_scen --road-custom RoadLRF_example.csv --colour-ramp blind

# Run and automatically generate interactive HTML & Leaflet visualizers
uv run python run_model.py --name scenario1 --visualise --force
```

#### CLI Flags (`run_model.py --help`):
* `-n`, `--name`: Scenario / run name (creates output folder `Outputs/<name>/`).
* `-o`, `--output-dir`: Custom output directory.
* `-g`, `--global-param`: `Default` or `User defined` treatment level.
* `--road-custom`: Path/filename in `CustomTreatment/` for road Load Reduction Factors (LRF).
* `--urb-custom`: Path/filename in `CustomTreatment/` for urban stormwater LRF.
* `--no-shape`: Skip generating GIS shapefiles (`Risk_Streams.shp`, `ZincLoads.shp`, etc.).
* `--no-images`: Skip generating JPG map images.
* `-c`, `--colour-ramp`: `traffic` (traffic light) or `blind` (color-blind safe).
* `-f`, `--force`: Overwrite existing output folder without prompt.
* `--visualise`: Automatically generate Leaflet & static HTML visualizers post-run.

---

### 2. Graphical User Interface (GUI)

To use the legacy Tkinter interface:

```bash
uv run python RSS_UserInterfaceV4.py
```

---

### 3. Python API

You can call the core simulation function directly within Python scripts or notebooks:

```python
from RSSModelV4_Feb2021 import RSSModel

status = RSSModel(
    runName="custom_run",
    outputPath="Outputs/custom_run/",
    globalParameter="Default",
    roadLRF=0,
    roadCustom="Templates/RoadLRF_template.csv",
    urbLRF=0,
    urbCustom="Templates/SWLRF_templateFull.csv",
    shape=1,
    jpgimage=1,
    colourList=["#fde7d6", "#66b266", "#9acd32", "#ffff66", "#ffb732", "#ff4d4d"],
    fontColour="black"
)
```

---

## 📊 Output Artifacts & Visualisation

Every run outputs the following into `Outputs/<run_name>/`:

1. **GIS Shapefiles**:
   * `Risk_Streams.shp`: Subcatchment polygons with scenario risk ratings (`LocalRS`, `SHRS`, `RoadsRS`, `UrbanRS`, `CombRS`).
   * `RiskMap_Coast.shp`: Coastal terminal reach points and estuary risk ratings.
   * `ZincLoads.shp` & `CopperLoads.shp`: In-stream generated and cumulative loads ($\text{kg/yr}$).
2. **Risk Map Images**: 10 high-resolution `.jpg` maps covering Streams and Coastal reaches across 5 source scenarios (Combined, Urban, All Roads, State Highways, Local Roads).
3. **CSV Summaries**: Reaches, load totals, and capacity summaries (`CoastalRisk_terminals.csv`, `Capacity.csv`).

### Interactive Visualizers
* [`visualise_test_leaflet.html`](file:///Users/hrishikodthuguli/Projects/rss-niwa/visualise_test_leaflet.html): Interactive Leaflet GIS map with OpenStreetMap/Satellite tiles, search by `nzsegment`, risk tier filtering, and popup attribute inspection.
* [`visualise_test_outputs.html`](file:///Users/hrishikodthuguli/Projects/rss-niwa/visualise_test_outputs.html): Static map dashboard for side-by-side scenario comparisons and reporting.
