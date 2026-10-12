"""
Risk classification module for the NIWA RSS Model.
Calculates stream and coastal CCU, Contaminant Strength (CS),
Receiving Environment Sensitivity (RES), and final Risk Scores/Tiers.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Dict
from .config import RSSParameters


def calculate_stream_risk(
    output_df: pd.DataFrame,
    base_sub: np.ndarray,
    mci: np.ndarray,
    params: RSSParameters
) -> pd.DataFrame:
    """
    Compute stream receiving sensitivity (RES), CCU, and risk tier ratings.
    """
    df = output_df.copy()
    n = len(df)

    # 1. Receiving Environment Sensitivity (RES) score based on substrate and MCI
    hard_soft = np.where(base_sub > params.Substrate, 1, 0)
    res_score = np.zeros(n, dtype=np.int8)

    # Hard bed
    res_score = np.where((hard_soft == 1) & (mci >= params.HardEx), 3, res_score)
    res_score = np.where((hard_soft == 1) & (mci < params.HardEx) & (mci > params.HardPF), 2, res_score)
    res_score = np.where((hard_soft == 1) & (mci <= params.HardPF), 1, res_score)

    # Soft bed
    res_score = np.where((hard_soft == 0) & (mci >= params.SoftEx), 3, res_score)
    res_score = np.where((hard_soft == 0) & (mci < params.SoftEx) & (mci > params.SoftPF), 2, res_score)
    res_score = np.where((hard_soft == 0) & (mci <= params.SoftPF), 1, res_score)

    def ccu_score(zn_conc: np.ndarray, cu_conc: np.ndarray) -> np.ndarray:
        ccu = (zn_conc / params.ZnANZECC) + (cu_conc / params.CuANZECC)
        score = np.zeros(n, dtype=np.int8)
        score[ccu >= params.StreamUpperCCU] = 5
        score[(ccu < params.StreamUpperCCU) & (ccu >= params.StreamLowerCCU)] = 1
        score[ccu < params.StreamLowerCCU] = 0
        return score

    scenarios = [
        ("Local Roads", "concRoadZnLocal", "concRoadCuLocal", "cumAreaRoadLocal"),
        ("State Highways", "concRoadZnSH", "concRoadCuSH", "cumAreaRoadSH"),
        ("All Roads", "concRoadZnAll", "concRoadCuAll", "cumRoadAreaAll"),
        ("Urban", "concUrbZn", "concUrbCu", "cumAreaUrb"),
        ("Combined", "concZnTot", "concCuTot", "cumAreaTot"),
    ]

    for label, zn_col, cu_col, area_col in scenarios:
        cs = ccu_score(df[zn_col].values, df[cu_col].values)
        cum_area = df[area_col].values

        risk = res_score * cs
        risk[cum_area == 0] = -1

        risk_text = np.full(n, "Lowest", dtype=object)
        risk_text[risk == -1] = "No upstream sources"
        risk_text[risk == 0] = "Lowest"
        risk_text[risk == 1] = "Lower"
        risk_text[risk == 2] = "Medium"
        risk_text[risk == 3] = "Higher"
        risk_text[risk >= 5] = "Highest"

        df[f"Risk Score _ {label}"] = risk
        df[f"Risk Level _ {label}"] = risk_text

    return df


def calculate_coastal_risk(
    output_df: pd.DataFrame,
    catch_df: pd.DataFrame,
    params: RSSParameters
) -> pd.DataFrame:
    """
    Compute coastal terminal reach sediment concentration, CCU, and risk tier ratings.
    """
    # Filter to non-inland coastal reaches
    estuary_df = catch_df[catch_df["Estuary"] != "Inland"].copy()
    est_len = len(estuary_df)

    load_cols = [
        "cumLoadRoadZnLocal", "cumLoadRoadCuLocal", "cumLoadRoadZnSH", "cumLoadRoadCuSH",
        "cumLoadRoadZnAll", "cumLoadRoadCuAll", "cumLoadUrbZn", "cumLoadUrbCu",
        "cumZnLoadTot", "cumCuLoadTot", "cumAreaRoadLocal", "cumAreaRoadSH",
        "cumRoadAreaAll", "cumAreaUrb", "cumAreaTot"
    ]
    estuary_df = estuary_df.set_index("nzsegment").join(output_df.set_index("nzsegment")[load_cols], how="left")

    est_trap_eff = estuary_df["EstTrapEff"].values
    cum_sed_load = estuary_df["cumSedLoad"].values

    coast_res = np.zeros(est_len, dtype=np.int8)
    coast_res[est_trap_eff > params.TrapLow] = 3
    coast_res[est_trap_eff > params.TrapHigh] = 5

    def divide_safe(num, den):
        return np.divide(num, den, out=np.zeros(len(num), dtype=float), where=(den != 0))

    scenarios = [
        ("Local Roads", "cumLoadRoadZnLocal", "cumLoadRoadCuLocal", "cumAreaRoadLocal"),
        ("State Highways", "cumLoadRoadZnSH", "cumLoadRoadCuSH", "cumAreaRoadSH"),
        ("All Roads", "cumLoadRoadZnAll", "cumLoadRoadCuAll", "cumRoadAreaAll"),
        ("Urban", "cumLoadUrbZn", "cumLoadUrbCu", "cumAreaUrb"),
        ("Combined", "cumZnLoadTot", "cumCuLoadTot", "cumAreaTot"),
    ]

    for label, zn_col, cu_col, area_col in scenarios:
        zn_load = estuary_df[zn_col].values
        cu_load = estuary_df[cu_col].values
        cum_area = estuary_df[area_col].values

        conc_zn = divide_safe(zn_load, cum_sed_load)
        conc_cu = divide_safe(cu_load, cum_sed_load)

        estuary_df[f"concZn{label}"] = conc_zn
        estuary_df[f"concCU{label}"] = conc_cu

        coast_ccu = (conc_zn / params.ZnTEL) + (conc_cu / params.CuTEL)
        coast_ccu_score = np.ones(est_len, dtype=np.int8)
        coast_ccu_score[coast_ccu > params.CoastLowerCCU] = 3
        coast_ccu_score[coast_ccu > params.CoastUpperCCU] = 5

        risk = coast_res * coast_ccu_score
        risk[cum_area == 0] = -1

        risk_text = np.full(est_len, "Lowest", dtype=object)
        risk_text[(risk > 0) & (risk < 9)] = "Lower"
        risk_text[risk == -1] = "No upstream sources"
        risk_text[risk == 0] = "Lowest"
        risk_text[risk == 9] = "Medium"
        risk_text[risk == 15] = "Higher"
        risk_text[risk > 15] = "Highest"

        estuary_df[f"Risk Score _ {label}"] = risk
        estuary_df[f"Risk Level _ {label}"] = risk_text

    return estuary_df.reset_index()

