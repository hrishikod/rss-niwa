"""
Pipeline orchestrator for the NIWA RSS Model.
Runs end-to-end simulation on user-provided DataFrames, returning clean result DataFrames.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
import pandas as pd
import numpy as np
import time

from .config import RSSParameters
from .emissions import calculate_road_emissions, calculate_urban_emissions
from .accumulator import accumulate_network_loads
from .risk import calculate_stream_risk, calculate_coastal_risk


@dataclass
class RSSModelResult:
    stream_results: pd.DataFrame
    coastal_results: pd.DataFrame
    road_segments: pd.DataFrame
    elapsed_seconds: float


def run_rss_pipeline(
    catchment_df: pd.DataFrame,
    road_df: pd.DataFrame,
    params: Optional[RSSParameters] = None,
    road_lrf_df: Optional[pd.DataFrame] = None,
    urban_lrf_df: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> RSSModelResult:
    """
    Run the complete RSS model on in-memory DataFrames.
    
    Args:
        catchment_df: Catchment data containing REC 2.4 attributes.
        road_df: RAMMSegments road data.
        params: RSSParameters instance (defaults used if None).
        road_lrf_df: Optional custom road treatment LRF table.
        urban_lrf_df: Optional custom urban treatment LRF table.
        verbose: Whether to print progress messages.
    """
    t0 = time.time()
    if params is None:
        params = RSSParameters()

    if verbose:
        print(f"Starting RSS simulation pipeline ({len(catchment_df):,} reaches, {len(road_df):,} road segments)...")

    # 1. Ensure catchment data is sorted by Hydseq
    catch_df = catchment_df.sort_values(by=["Hydseq"]).copy()
    n_cat = len(catch_df)

    # Pre-build lookup dictionaries for slope and drainage
    slope_dict = dict(zip(catch_df["nzsegment"], catch_df["RSSslopeClass"]))
    drain_dict = dict(zip(catch_df["nzsegment"], catch_df["RSSdrainClass"]))

    # 2. Road emissions
    if verbose:
        print("Calculating road emissions and Level of Service...")
    ramm_updated, road_by_subcatch = calculate_road_emissions(
        road_df, slope_dict, drain_dict, params, road_lrf_df
    )

    # 3. Base output dataframe initialized with catchment metadata
    base_cols = [
        "nzsegment", "CATAREA", "Hydseq", "FNODE", "TNODE", "Region",
        "cumSedLoad", "StreamLength_km", "Terminal", "Estuary", "EstTrapEff"
    ]
    output_df = catch_df[base_cols].copy().set_index("nzsegment")

    # Join road loads to catchment output
    output_df = output_df.join(road_by_subcatch, how="left").fillna(0.0)

    # 4. Urban emissions
    if verbose:
        print("Calculating urban land-use loads...")
    urban_emissions_df = calculate_urban_emissions(
        catch_df, output_df, params, urban_lrf_df
    )
    output_df = output_df.join(urban_emissions_df, how="left").fillna(0.0)

    # Combined local loads
    gen_zn_local_road = output_df["genRoadZnLocal"].values
    gen_cu_local_road = output_df["genRoadCuLocal"].values
    area_local_road = output_df["areaRoadLocal"].values

    gen_zn_sh_road = output_df["genRoadZnSH"].values
    gen_cu_sh_road = output_df["genRoadCuSH"].values
    area_sh_road = output_df["areaRoadSH"].values

    gen_zn_urb = output_df["genUrbZn"].values
    gen_cu_urb = output_df["genUrbCu"].values
    area_urb = output_df["builtArea"].values

    # 5. Downstream topological accumulation
    if verbose:
        print("Accumulating loads and impervious areas downstream...")
    mean_q = catch_df["MeanQ"].values
    volumes = mean_q * (60.0 * 60.0 * 24.0 * 365.0)

    quantities = {
        "RoadLocal_Area": area_local_road,
        "RoadZnLocal": gen_zn_local_road,
        "RoadCuLocal": gen_cu_local_road,
        "RoadSH_Area": area_sh_road,
        "RoadZnSH": gen_zn_sh_road,
        "RoadCuSH": gen_cu_sh_road,
        "Urb_Area": area_urb,
        "UrbZn": gen_zn_urb,
        "UrbCu": gen_cu_urb
    }

    acc_results = accumulate_network_loads(catch_df, quantities, volumes)

    # Unpack accumulated quantities
    output_df["cumAreaRoadLocal"] = acc_results["RoadLocal_Area"][0]
    output_df["cumLoadRoadZnLocal"] = acc_results["RoadZnLocal"][0]
    output_df["concRoadZnLocal"] = acc_results["RoadZnLocal"][1]
    output_df["cumLoadRoadCuLocal"] = acc_results["RoadCuLocal"][0]
    output_df["concRoadCuLocal"] = acc_results["RoadCuLocal"][1]

    output_df["cumAreaRoadSH"] = acc_results["RoadSH_Area"][0]
    output_df["cumLoadRoadZnSH"] = acc_results["RoadZnSH"][0]
    output_df["concRoadZnSH"] = acc_results["RoadZnSH"][1]
    output_df["cumLoadRoadCuSH"] = acc_results["RoadCuSH"][0]
    output_df["concRoadCuSH"] = acc_results["RoadCuSH"][1]

    # All roads
    output_df["genRoadZnAll"] = output_df["genRoadZnLocal"] + output_df["genRoadZnSH"]
    output_df["genRoadCuAll"] = output_df["genRoadCuLocal"] + output_df["genRoadCuSH"]
    output_df["cumRoadAreaAll"] = output_df["cumAreaRoadLocal"] + output_df["cumAreaRoadSH"]
    output_df["cumLoadRoadZnAll"] = output_df["cumLoadRoadZnLocal"] + output_df["cumLoadRoadZnSH"]
    output_df["concRoadZnAll"] = np.divide(output_df["cumLoadRoadZnAll"].values, volumes, out=np.zeros(n_cat, dtype=float), where=(volumes != 0))
    output_df["cumLoadRoadCuAll"] = output_df["cumLoadRoadCuLocal"] + output_df["cumLoadRoadCuSH"]
    output_df["concRoadCuAll"] = np.divide(output_df["cumLoadRoadCuAll"].values, volumes, out=np.zeros(n_cat, dtype=float), where=(volumes != 0))

    # Urban
    output_df["cumAreaUrb"] = acc_results["Urb_Area"][0]
    output_df["cumLoadUrbZn"] = acc_results["UrbZn"][0]
    output_df["concUrbZn"] = acc_results["UrbZn"][1]
    output_df["cumLoadUrbCu"] = acc_results["UrbCu"][0]
    output_df["concUrbCu"] = acc_results["UrbCu"][1]

    # Combined
    output_df["genZnLoadTot"] = output_df["genRoadZnAll"] + output_df["genUrbZn"]
    output_df["genCuLoadTot"] = output_df["genRoadCuAll"] + output_df["genUrbCu"]
    output_df["cumAreaTot"] = output_df["cumRoadAreaAll"] + output_df["cumAreaUrb"]
    output_df["cumZnLoadTot"] = output_df["cumLoadRoadZnAll"] + output_df["cumLoadUrbZn"]
    output_df["concZnTot"] = np.divide(output_df["cumZnLoadTot"].values, volumes, out=np.zeros(n_cat, dtype=float), where=(volumes != 0))
    output_df["cumCuLoadTot"] = output_df["cumLoadRoadCuAll"] + output_df["cumLoadUrbCu"]
    output_df["concCuTot"] = np.divide(output_df["cumCuLoadTot"].values, volumes, out=np.zeros(n_cat, dtype=float), where=(volumes != 0))

    output_df = output_df.reset_index()

    # 6. Stream Risk Classification
    if verbose:
        print("Classifying stream risks against ANZECC/MCI criteria...")
    stream_df = calculate_stream_risk(
        output_df, catch_df["BaseSub"].values, catch_df["MCI"].values, params
    )

    # 7. Coastal Risk Classification
    if verbose:
        print("Classifying coastal terminal reach risks...")
    coastal_df = calculate_coastal_risk(stream_df, catch_df, params)

    elapsed = time.time() - t0
    if verbose:
        print(f"Pipeline finished successfully in {elapsed:.2f} seconds.")

    return RSSModelResult(
        stream_results=stream_df,
        coastal_results=coastal_df,
        road_segments=ramm_updated,
        elapsed_seconds=elapsed
    )

