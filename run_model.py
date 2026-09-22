#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface (CLI) to run the NIWA Road Stormwater Screening (RSS) Model
without requiring the Tkinter graphical user interface (GUI).

Usage examples:
    # Run default test scenario
    python run_model.py --name test

    # Run custom scenario with shapefiles and map images disabled (fast run)
    python run_model.py --name fast_run --no-shape --no-images

    # Run with custom road treatment file and color-blind palette
    python run_model.py --name custom_scen --road-custom CustomTreatment/RoadLRF_scenario1.csv --colour-ramp blind

    # Run and automatically generate interactive HTML & Leaflet visualizers
    python run_model.py --name scenario1 --visualise
"""

import os
import sys
import argparse
import time

# PALETTES and resolve_custom_file definitions

# Color palettes (matching GUI)
PALETTES = {
    "traffic": {
        "colors": ["#fde7d6", "#66b266", "#9acd32", "#ffff66", "#ffb732", "#ff4d4d"],
        "font_color": "black",
        "description": "Traffic light palette (Beige, Green, Lime, Yellow, Orange, Red)"
    },
    "blind": {
        "colors": ["#e5f5f9", "#fcc5c0", "#f768a1", "#dd3497", "#ae017e", "#7a0177"],
        "font_color": "white",
        "description": "Color-blind safe palette (ColorBrewer pink/magenta/purple)"
    }
}


def resolve_custom_file(file_arg, default_path, prefix=""):
    """Resolve a custom treatment file path."""
    if not file_arg:
        return 0, default_path

    # Check direct path
    if os.path.isfile(file_arg):
        return 1, file_arg

    # Check in CustomTreatment/ directory
    candidate = os.path.join("CustomTreatment", file_arg)
    if os.path.isfile(candidate):
        return 1, candidate

    print(f"Error: Custom treatment file '{file_arg}' not found (checked '{file_arg}' and '{candidate}').")
    sys.exit(1)


def generate_visualisations(output_dir, run_name):
    """Generate interactive static & Leaflet visualizers for the simulation outputs."""
    print("\n--- Generating Interactive Visualisations ---")
    try:
        # Import the visualizer generation functions if available or run inline
        from scratch.generate_leaflet_viewer import generate_leaflet_map
        generate_leaflet_map(output_dir)
    except Exception:
        # Inline generator script execution
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), "scratch", "generate_leaflet_viewer.py")
        if os.path.isfile(script_path):
            subprocess.run([sys.executable, script_path], check=False)
    print(f"Visualisations ready in {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="NIWA Road Stormwater Screening (RSS) Model CLI Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_model.py -n my_run
  python run_model.py -n test --force
  python run_model.py -n quick_test --no-shape --no-images
  python run_model.py -n road_test --road-custom RoadLRF_example.csv --visualise
        """
    )

    parser.add_argument(
        "-n", "--name",
        default="test",
        help="Scenario / run name (used to name the output folder). Default: 'test'"
    )

    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Custom output directory path. Default: 'Outputs/<name>/'"
    )

    parser.add_argument(
        "-g", "--global-param",
        choices=["Default", "User defined"],
        default="Default",
        help="Global parameter choice for default level of treatment. Default: 'Default'"
    )

    parser.add_argument(
        "--road-custom",
        default=None,
        help="Path or filename (in CustomTreatment/) for road runoff LRF. Enables road treatment."
    )

    parser.add_argument(
        "--urb-custom",
        default=None,
        help="Path or filename (in CustomTreatment/) for urban stormwater LRF. Enables urban treatment."
    )

    parser.add_argument(
        "--no-shape",
        action="store_true",
        help="Disable generating GIS shapefiles (Risk_Streams, RiskMap_Coast, ZincLoads, CopperLoads)."
    )

    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Disable generating JPG risk map images."
    )

    parser.add_argument(
        "-c", "--colour-ramp",
        choices=["traffic", "blind"],
        default="traffic",
        help="Colour ramp: 'traffic' (traffic light) or 'blind' (color-blind safe). Default: 'traffic'"
    )

    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output directory without asking for confirmation."
    )

    parser.add_argument(
        "--visualise",
        action="store_true",
        help="Automatically generate interactive HTML and Leaflet visualizers after the run completes."
    )

    args = parser.parse_args()

    run_name = args.name.strip()
    if not run_name:
        print("Error: Scenario name cannot be empty.")
        sys.exit(1)

    # Determine output path
    output_path = args.output_dir if args.output_dir else os.path.join("Outputs", run_name)
    if not output_path.endswith("/"):
        output_path += "/"

    # Check if directory exists
    if os.path.isdir(output_path):
        if not args.force:
            response = input(f"Warning: Output directory '{output_path}' already exists. Overwrite? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Run aborted by user.")
                sys.exit(0)
    else:
        os.makedirs(output_path, exist_ok=True)

    # Resolve custom treatment files
    road_lrf, road_custom = resolve_custom_file(
        args.road_custom,
        default_path="Templates/RoadLRF_template.csv"
    )
    urb_lrf, urb_custom = resolve_custom_file(
        args.urb_custom,
        default_path="Templates/SWLRF_templateFull.csv"
    )

    # Flags
    shape = 0 if args.no_shape else 1
    jpgimage = 0 if args.no_images else 1

    # Palette
    palette_info = PALETTES[args.colour_ramp]
    colour_list = palette_info["colors"]
    font_colour = palette_info["font_color"]

    # Print run summary
    print("=" * 60)
    print(" NIWA RSS Model (Road Stormwater Screening) - Headless Run")
    print("=" * 60)
    print(f" Scenario Name     : {run_name}")
    print(f" Output Directory  : {output_path}")
    print(f" Global Parameter  : {args.global_param}")
    print(f" Road Treatment    : {'Custom (' + road_custom + ')' if road_lrf else 'Default / None'}")
    print(f" Urban Treatment   : {'Custom (' + urb_custom + ')' if urb_lrf else 'Default / None'}")
    print(f" Generate Shapes   : {'Yes' if shape else 'No'}")
    print(f" Generate Maps     : {'Yes' if jpgimage else 'No'}")
    print(f" Colour Ramp       : {args.colour_ramp} ({palette_info['description']})")
    print("=" * 60)
    print("Starting simulation...\n")

    # Ensure headless matplotlib backend before importing model
    try:
        import matplotlib
        matplotlib.use("Agg")
        from RSSModelV4_Feb2021 import RSSModel
    except ImportError as e:
        print(f"\nError importing model dependencies: {e}", file=sys.stderr)
        print("Please ensure you are running in the project virtual environment:", file=sys.stderr)
        print("  uv run python run_model.py [options]", file=sys.stderr)
        print("  or activate .venv: source .venv/bin/activate && python run_model.py [options]\n", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()

    try:
        result_message = RSSModel(
            run_name,
            output_path,
            args.global_param,
            road_lrf,
            road_custom,
            urb_lrf,
            urb_custom,
            shape,
            jpgimage,
            colour_list,
            font_colour
        )

        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print(f" Simulation finished in {elapsed:.1f} seconds ({elapsed / 60:.2f} minutes).")
        print(f" Status: {result_message}")
        print(f" Outputs saved to: {output_path}")
        print("=" * 60)

        if args.visualise:
            generate_visualisations(output_path, run_name)

    except KeyboardInterrupt:
        print("\nSimulation aborted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nSimulation failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
