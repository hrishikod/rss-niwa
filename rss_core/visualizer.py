"""
Visualization generator for the NIWA RSS Model.
Generates self-contained interactive Leaflet HTML maps suitable for
Databricks Apps, Streamlit, Dash, or direct browser viewing.
"""
import json
import math
import pandas as pd
from typing import Optional


def attach_map_points(
    stream_df: pd.DataFrame,
    coastal_df: pd.DataFrame,
    points_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join WGS84 map points to model results by nzsegment."""
    points = pd.read_csv(points_path, usecols=["kind", "nzsegment", "lat", "lng"])
    mapped = []
    stream_lookup = None
    for kind, results in (("stream", stream_df), ("coastal", coastal_df)):
        lookup = points.loc[points["kind"] == kind, ["nzsegment", "lat", "lng"]]
        if lookup["nzsegment"].duplicated().any():
            raise ValueError(f"Duplicate nzsegment values in {kind} map points")
        if kind == "stream":
            stream_lookup = lookup
        if "lat" in results.columns or "lng" in results.columns:
            raise ValueError("Results already contain map coordinates")
        mapped.append(results.merge(lookup, on="nzsegment", how="left", validate="many_to_one"))

    missing_coastal = mapped[1]["lat"].isna()
    if missing_coastal.any():
        fallback = mapped[1].loc[missing_coastal, ["nzsegment"]].merge(
            stream_lookup, on="nzsegment", how="left", validate="many_to_one"
        )
        mapped[1].loc[missing_coastal, ["lat", "lng"]] = fallback[["lat", "lng"]].to_numpy()
    return mapped[0], mapped[1]


def generate_interactive_map_html(
    stream_df: pd.DataFrame,
    coastal_df: pd.DataFrame,
    max_stream_features: int = 25000,
    title: str = "NIWA RSS Model - Databricks Visualizer"
) -> str:
    """
    Produce a standalone HTML string containing an interactive Leaflet map
    with stream subcatchment centroids and coastal terminal reaches.
    """
    level_map = {
        'Highest': 5,
        'Higher': 4,
        'Medium': 3,
        'Lower': 2,
        'Lowest': 1,
        'No upstream sources': 0
    }

    def coordinates(row):
        lat = row.get("lat", row.get("latitude", row.get("Y")))
        lng = row.get("lng", row.get("longitude", row.get("X")))
        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            return None
        if not (math.isfinite(lat) and math.isfinite(lng)):
            return None
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return None
        return round(lat, 5), round(lng, 5)

    # 1. Process coastal data
    coast_records = []

    # Extract scenario columns
    scen_prefixes = ["Combined", "Urban", "All Roads", "State Highways", "Local Roads"]

    for _, row in coastal_df.iterrows():
        point = coordinates(row)
        if point is None:
            continue
        nzseg = int(row.get("nzsegment", 0))

        scores = [float(row.get(f"Risk Score _ {s}", -1.0)) for s in scen_prefixes]
        levels = [level_map.get(str(row.get(f"Risk Level _ {s}", "")), -1) for s in scen_prefixes]

        coast_records.append([*point, nzseg, scores, levels])

    # 2. Process stream data (filter to elevated risks to keep payload light)
    stream_records = []
    elevated_streams = stream_df[
        stream_df["Risk Level _ Combined"].isin(["Lower", "Medium", "Higher", "Highest"])
    ].head(max_stream_features)

    for _, row in elevated_streams.iterrows():
        point = coordinates(row)
        if point is None:
            continue
        nzseg = int(row.get("nzsegment", 0))

        scores = [float(row.get(f"Risk Score _ {s}", -1.0)) for s in scen_prefixes]
        levels = [level_map.get(str(row.get(f"Risk Level _ {s}", "")), -1) for s in scen_prefixes]

        stream_records.append([*point, nzseg, scores, levels])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    html, body {{ margin: 0; padding: 0; }}
    body {{ min-height: 650px; display: flex; flex-direction: column; }}
    .map-container {{ position: relative; height: 600px; min-height: 600px; width: 100%; }}
    #map {{ height: 600px; width: 100%; }}
    .active-scen {{ background: #0284c7 !important; color: white !important; font-weight: 600; }}
  </style>
</head>
<body class="bg-slate-50">
  <header class="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between shadow-sm z-10">
    <div class="flex items-center gap-2">
      <span class="px-2 py-0.5 text-xs font-bold rounded bg-sky-100 text-sky-800">Databricks App</span>
      <h1 class="text-sm font-bold text-slate-900">{title}</h1>
    </div>
    <div class="text-xs text-slate-500 font-mono">
      Mapped Coastal Reaches: {len(coast_records):,} | Mapped Stream Reaches: {len(stream_records):,}
    </div>
  </header>

  <div class="map-container">
    <div id="map"></div>
    {'<div class="absolute bottom-4 left-4 z-[1000] bg-white p-3 rounded shadow text-sm">No reach coordinates found. Add latitude and longitude columns to plot results.</div>' if not coast_records and not stream_records else ''}

    <!-- Floating scenario selector -->
    <div class="absolute top-4 left-4 z-[1000] bg-white/95 backdrop-blur-md rounded-xl p-3 border border-slate-200 shadow-lg text-xs space-y-2">
      <div class="font-bold text-slate-800">Contaminant Scenario</div>
      <div class="grid grid-cols-2 gap-1">
        <button onclick="setScenario(0)" id="scen-0" class="px-2.5 py-1.5 rounded border border-slate-200 text-left active-scen">Combined</button>
        <button onclick="setScenario(1)" id="scen-1" class="px-2.5 py-1.5 rounded border border-slate-200 text-left bg-slate-50">Urban</button>
        <button onclick="setScenario(2)" id="scen-2" class="px-2.5 py-1.5 rounded border border-slate-200 text-left bg-slate-50">All Roads</button>
        <button onclick="setScenario(3)" id="scen-3" class="px-2.5 py-1.5 rounded border border-slate-200 text-left bg-slate-50">Highways</button>
        <button onclick="setScenario(4)" id="scen-4" class="col-span-2 px-2.5 py-1.5 rounded border border-slate-200 text-left bg-slate-50">Local Roads</button>
      </div>
      <div class="text-[10px] text-slate-400 border-t pt-1.5">
        🔴 Highest | 🟠 Higher | 🟡 Medium | 🟢 Lower | ⚪ None
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    if (typeof L === 'undefined') {{
      document.getElementById('map').innerHTML = '<p style="padding:16px;font:14px sans-serif">Map library could not load. Check access to unpkg.com from your browser.</p>';
    }} else {{
    const COAST_DATA = {json.dumps(coast_records)};
    const STREAM_DATA = {json.dumps(stream_records)};
    const SCENARIOS = ['Combined', 'Urban', 'All Roads', 'State Highways', 'Local Roads'];
    const LEVEL_COLORS = {{ 5: '#ff0000', 4: '#ffa500', 3: '#ffff00', 2: '#9acd32', 1: '#ffe4c4', 0: '#e0f7fa', '-1': '#cbd5e1' }};

    let currentScen = 0;
    const map = L.map('map', {{ center: [-41.0, 174.0], zoom: 6, preferCanvas: true }});

    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);

    function render() {{
      layerGroup.clearLayers();
      STREAM_DATA.forEach(p => {{
        const lvl = p[4][currentScen];
        L.circleMarker([p[0], p[1]], {{
          radius: 2,
          fillColor: LEVEL_COLORS[lvl] || '#999',
          stroke: false,
          fillOpacity: 0.65
        }}).bindTooltip(`Stream reach ${{p[2]}}: Score ${{p[3][currentScen]}}`).addTo(layerGroup);
      }});
      COAST_DATA.forEach(p => {{
        const lvl = p[4][currentScen];
        const color = LEVEL_COLORS[lvl] || '#999';
        L.circleMarker([p[0], p[1]], {{
          radius: lvl >= 4 ? 6 : 4,
          fillColor: color,
          color: '#1e293b',
          weight: 0.8,
          fillOpacity: 0.85
        }}).bindTooltip(`Reach ${{p[2]}}: Score ${{p[3][currentScen]}}`).addTo(layerGroup);
      }});
    }}

    window.setScenario = function(idx) {{
      currentScen = idx;
      for (let i = 0; i < 5; i++) {{
        document.getElementById('scen-' + i).className = i === idx
          ? 'px-2.5 py-1.5 rounded border border-slate-200 text-left active-scen' + (i === 4 ? ' col-span-2' : '')
          : 'px-2.5 py-1.5 rounded border border-slate-200 text-left bg-slate-50' + (i === 4 ? ' col-span-2' : '');
      }}
      render();
    }};

    render();
    }}
  </script>
</body>
</html>
"""
    return html
