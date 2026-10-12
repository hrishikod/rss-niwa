"""
Emissions module for the NIWA RSS Model.
Calculates road and urban surface contaminant generation (Zinc and Copper in g/yr or kg/yr).
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from .config import RSSParameters


def calculate_road_emissions(
    ramm_df: pd.DataFrame,
    slope_dict: Dict[int, int],
    drain_dict: Dict[int, int],
    params: RSSParameters,
    road_lrf_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate vehicle kilometres travelled (VKT), level of service (LOS),
    and road-generated Zn/Cu loads per road segment.
    
    Returns:
        ramm_df: Updated road segment DataFrame with emissions and capacity.
        road_by_subcatchment: Aggregated loads grouped by (nzsegment).
    """
    df = ramm_df.copy()

    # Map slope and drainage class from subcatchment dictionaries if not present
    if "SlopeClass" not in df.columns:
        df["SlopeClass"] = df["nzsegment"].map(slope_dict).fillna(1).astype(int)
    if "DrainClass" not in df.columns:
        df["DrainClass"] = df["nzsegment"].map(drain_dict).fillna(1).astype(int)

    # Treatment LRFs
    if road_lrf_df is not None:
        head_dict = {
            "LRF for Zn from SH": "ZnLRFSH",
            "LRF for Zn from local": "ZnLRFloc",
            "LRF for Cu from SH": "CuLRFSH",
            "LRF for Cu from local": "CuLRFloc"
        }
        merge_cols = ["MergeID", "LRF for Zn from SH", "LRF for Zn from local", "LRF for Cu from SH", "LRF for Cu from local"]
        df = df.reset_index().merge(road_lrf_df[merge_cols], on="MergeID", how="left").set_index("Concat_ID")
        df = df.rename(columns=head_dict)
    else:
        df["ZnLRFSH"] = 0.0
        df["ZnLRFloc"] = 0.0
        df["CuLRFSH"] = 0.0
        df["CuLRFloc"] = 0.0

    segLU = df["UrbanCode"].values  # 1 = built-up, 2 = green, 0 = rural
    drain = df["DrainClass"].values
    SH = df["SH"].values
    segLen = df["Length"].values
    aadt = df["AADT_VPD"].values
    hvyFrac = df["HvyFrac"].values
    width = df["Width"].values
    slope = df["SlopeClass"].values

    def lrf_replace(lrf_arr):
        res = lrf_arr.copy()
        res = np.where((segLU == 1) & (res == 0), params.Catchpit, res)
        res = np.where((segLU == 2) & (res == 0), params.Catchpit, res)
        res = np.where((segLU == 0) & (drain == 2) & (res == 0), params.InfilGood, res)
        res = np.where((segLU == 0) & (drain == 1) & (res == 0), params.InfilPoor, res)
        return res

    zn_lrf_sh = lrf_replace(df["ZnLRFSH"].fillna(0).values)
    zn_lrf_loc = lrf_replace(df["ZnLRFloc"].fillna(0).values)
    cu_lrf_sh = lrf_replace(df["CuLRFSH"].fillna(0).values)
    cu_lrf_loc = lrf_replace(df["CuLRFloc"].fillna(0).values)

    zn_lrf_road = zn_lrf_sh * SH + zn_lrf_loc * (1 - SH)
    cu_lrf_road = cu_lrf_sh * SH + cu_lrf_loc * (1 - SH)

    # Road areas
    roadArea = width * segLen
    roadAreaUrb = np.where((segLU == 1) | (segLU == 2), roadArea, 0.0)

    # Trafficable width
    n = len(df)
    trafWidth = np.zeros(n, dtype=float)
    np.copyto(trafWidth, width + params.TWF0, where=(width <= 3))
    np.copyto(trafWidth, width + params.TWF3, where=((width > 3) & (width <= 4)))
    np.copyto(trafWidth, width + params.TWF4, where=((width > 4) & (width <= 5)))
    np.copyto(trafWidth, width + params.TWF5, where=((width > 5) & (width <= 6)))
    np.copyto(trafWidth, width + params.TWF6, where=((width > 6) & (width <= 7)))
    np.copyto(trafWidth, width + params.TWF7, where=((width > 7) & (width <= 8)))
    np.copyto(trafWidth, width + params.TWF8, where=(width > 8))

    # Truck factor
    truckFactor = np.ones(n, dtype=float)
    np.copyto(truckFactor, 1.0 / (1.0 + hvyFrac * (params.HvyFlat - 1.0)), where=(slope == 1))
    np.copyto(truckFactor, 1.0 / (1.0 + hvyFrac * (params.HvyRolling - 1.0)), where=(slope == 2))
    np.copyto(truckFactor, 1.0 / (1.0 + hvyFrac * (params.HvySteep - 1.0)), where=(slope == 3))

    capacity = params.CapFac * params.DD * trafWidth * truckFactor * 10.0
    los = np.divide(aadt, capacity, out=np.zeros(n, dtype=float), where=(capacity != 0))

    losClass = np.ones(n, dtype=np.int8)
    losClass[los >= 0.7] = 3
    losClass[(los < 0.7) & (los >= 0.35)] = 2
    losClass[los < 0.35] = 1

    znVEF = np.where(losClass == 3, params.ZnVEF3, np.where(losClass == 2, params.ZnVEF2, params.ZnVEF1))
    cuVEF = np.where(losClass == 3, params.CuVEF3, np.where(losClass == 2, params.CuVEF2, params.CuVEF1))

    vkt = (aadt * segLen) / 1000.0  # Daily vehicle km

    # Metal loads in g/year
    roadZn = (1.0 - zn_lrf_road) * znVEF * vkt * 365.0 / 1000.0
    roadCu = (1.0 - cu_lrf_road) * cuVEF * vkt * 365.0 / 1000.0

    df["roadZn"] = roadZn
    df["roadCu"] = roadCu
    df["roadArea"] = roadArea
    df["roadAreaUrb"] = roadAreaUrb
    df["Capacity"] = capacity

    # Aggregate by subcatchment and road type (Local vs State Highway)
    grouped = df.groupby(["nzsegment", "SH"])[["roadArea", "roadAreaUrb", "roadZn", "roadCu"]].sum().reset_index()

    local_df = grouped[grouped["SH"] == 0].set_index("nzsegment")[["roadArea", "roadAreaUrb", "roadZn", "roadCu"]].rename(
        columns={"roadZn": "genRoadZnLocal", "roadCu": "genRoadCuLocal", "roadArea": "areaRoadLocal", "roadAreaUrb": "areaRoadUrbLocal"}
    )
    sh_df = grouped[grouped["SH"] == 1].set_index("nzsegment")[["roadArea", "roadAreaUrb", "roadZn", "roadCu"]].rename(
        columns={"roadZn": "genRoadZnSH", "roadCu": "genRoadCuSH", "roadArea": "areaRoadSH", "roadAreaUrb": "areaRoadUrbSH"}
    )

    combined_roads = local_df.join(sh_df, how="outer").fillna(0.0)
    return df, combined_roads


def calculate_urban_emissions(
    catch_df: pd.DataFrame,
    road_subcatchment_df: pd.DataFrame,
    params: RSSParameters,
    urban_lrf_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Calculate generated urban Zn and Cu contaminant loads per subcatchment.
    """
    df = catch_df.copy()
    if urban_lrf_df is not None:
        sw_head_dict = {
            "LRF Zn Residential": "ZnLRFRes",
            "LRF Zn Commercial and Industrial": "ZnLRFIC",
            "LRF Cu Residential": "CuLRFRes",
            "LRF Cu Commercial and Industrial": "CuLRFIC",
            "Source Control": "sControl"
        }
        cols = ["nzsegment", "LRF Zn Residential", "LRF Zn Commercial and Industrial", "LRF Cu Residential", "LRF Cu Commercial and Industrial"]
        if "Source Control" in urban_lrf_df.columns:
            cols.append("Source Control")
        df = df.merge(urban_lrf_df[cols], on="nzsegment", how="left").rename(columns=sw_head_dict)
        if "sControl" not in df.columns:
            df["sControl"] = 0
    else:
        df["ZnLRFRes"] = 0.0
        df["ZnLRFIC"] = 0.0
        df["CuLRFRes"] = 0.0
        df["CuLRFIC"] = 0.0
        df["sControl"] = 0

    df["ZnLRFRes"] = df["ZnLRFRes"].fillna(0.0).replace({0.0: params.ZnLRFResP})
    df["ZnLRFIC"] = df["ZnLRFIC"].fillna(0.0).replace({0.0: params.ZnLRFICP})
    df["CuLRFRes"] = df["CuLRFRes"].fillna(0.0).replace({0.0: params.CuLRFResP})
    df["CuLRFIC"] = df["CuLRFIC"].fillna(0.0).replace({0.0: params.CuLRFICP})

    catch_area = df["CATAREA"].values
    frac_urb = df["FracUrbBuilt"].values
    frac_res = df["fracBuiltRes"].values
    frac_ic = df["fracBuiltIC"].values
    s_control = df["sControl"].values

    # Get urban road area from the aggregated road dataframe
    road_area_urb = np.zeros(len(df), dtype=float)
    if "areaRoadUrbLocal" in road_subcatchment_df.columns and "areaRoadUrbSH" in road_subcatchment_df.columns:
        tot_urb_road = (road_subcatchment_df["areaRoadUrbLocal"] + road_subcatchment_df["areaRoadUrbSH"]).to_dict()
        road_area_urb = df["nzsegment"].map(tot_urb_road).fillna(0.0).values

    built_area = np.maximum(catch_area * frac_urb - road_area_urb, 0.0)
    res_imp_area = frac_res * built_area * params.ImpResFrac
    ic_imp_area = frac_ic * built_area * params.ImpICFrac

    zn_res_yield = np.where(s_control == 1, params.ZnYieldResSC, params.ZnYieldRes)
    zn_ic_yield = np.where(s_control == 1, params.ZnYieldICSC, params.ZnYieldIC)
    cu_res_yield = np.where(s_control == 1, params.CuYieldResSC, params.CuYieldRes)
    cu_ic_yield = np.where(s_control == 1, params.CuYieldICSC, params.CuYieldIC)

    gen_zn_res = res_imp_area * zn_res_yield * (1.0 - df["ZnLRFRes"].values)
    gen_zn_ic = ic_imp_area * zn_ic_yield * (1.0 - df["ZnLRFIC"].values)
    gen_urb_zn = gen_zn_res + gen_zn_ic

    gen_cu_res = res_imp_area * cu_res_yield * (1.0 - df["CuLRFRes"].values)
    gen_cu_ic = ic_imp_area * cu_ic_yield * (1.0 - df["CuLRFIC"].values)
    gen_urb_cu = gen_cu_res + gen_cu_ic

    res_df = pd.DataFrame({
        "nzsegment": df["nzsegment"].values,
        "builtArea": built_area,
        "resImpArea": res_imp_area,
        "ICImpArea": ic_imp_area,
        "genUrbZn": gen_urb_zn,
        "genUrbCu": gen_urb_cu
    }).set_index("nzsegment")

    return res_df

