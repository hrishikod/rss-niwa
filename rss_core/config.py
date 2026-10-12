"""
Configuration and model parameters for the NIWA RSS Model.
Allows loading from Parameters/ModelParameters.xlsx or providing a custom dictionary.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os
import pandas as pd


@dataclass
class RSSParameters:
    # Road parameters
    Catchpit: float = 0.1
    InfilGood: float = 0.7
    InfilPoor: float = 0.3
    TWF0: float = 0.60
    TWF3: float = 0.60
    TWF4: float = 0.65
    TWF5: float = 0.73
    TWF6: float = 0.82
    TWF7: float = 0.91
    TWF8: float = 1.00
    HvyFlat: float = 2.0
    HvyRolling: float = 5.0
    HvySteep: float = 10.0
    CapFac: float = 2800.0
    DD: float = 1.0
    ZnVEF1: float = 0.28
    ZnVEF2: float = 0.28
    ZnVEF3: float = 0.62
    CuVEF1: float = 0.047
    CuVEF2: float = 0.047
    CuVEF3: float = 0.095

    # Urban parameters
    ZnYieldRes: float = 0.31
    ZnYieldResSC: float = 0.14
    ZnYieldIC: float = 0.71
    ZnYieldICSC: float = 0.19
    CuYieldRes: float = 0.016
    CuYieldResSC: float = 0.015
    CuYieldIC: float = 0.036
    CuYieldICSC: float = 0.026
    ZnLRFResP: float = 0.0
    ZnLRFICP: float = 0.0
    CuLRFResP: float = 0.0
    CuLRFICP: float = 0.0
    ImpResFrac: float = 0.2
    ImpICFrac: float = 0.8

    # Stream parameters
    CuANZECC: float = 0.001
    ZnANZECC: float = 0.0024
    StreamLowerCCU: float = 1.0
    StreamUpperCCU: float = 2.367
    Substrate: float = 2.5
    HardEx: float = 120.0
    HardPF: float = 100.0
    SoftEx: float = 100.0
    SoftPF: float = 85.0

    # Coastal parameters
    ZnTEL: float = 124.0
    CuTEL: float = 18.7
    CoastLowerCCU: float = 1.0
    CoastUpperCCU: float = 4.1
    TrapHigh: float = 0.7
    TrapLow: float = 0.3

    @classmethod
    def from_excel(cls, excel_path: str = "Parameters/ModelParameters.xlsx", mode: str = "Default") -> "RSSParameters":
        """Load parameters from ModelParameters.xlsx, selecting 'Default' or 'User defined' column."""
        if not os.path.isfile(excel_path):
            return cls()

        def get_dict(sheet_name: str) -> Dict[str, float]:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            df = df.set_index("Name")
            col = mode if mode in df.columns else "Default"
            return df[col].to_dict()

        road_p = get_dict("RoadParameters")
        urban_p = get_dict("UrbanParameters")
        stream_p = get_dict("StreamParameters")
        coast_p = get_dict("CoastalParameters")

        all_params = {**road_p, **urban_p, **stream_p, **coast_p}
        # Remap parameter naming differences if any
        if "ZnLRFRes" in all_params:
            all_params["ZnLRFResP"] = all_params.pop("ZnLRFRes")
        if "ZnLRFIC" in all_params:
            all_params["ZnLRFICP"] = all_params.pop("ZnLRFIC")
        if "CuLRFRes" in all_params:
            all_params["CuLRFResP"] = all_params.pop("CuLRFRes")
        if "CuLRFIC" in all_params:
            all_params["CuLRFICP"] = all_params.pop("CuLRFIC")
        if "ImpRES" in all_params:
            all_params["ImpResFrac"] = all_params.pop("ImpRES")
        if "ImpIC" in all_params:
            all_params["ImpICFrac"] = all_params.pop("ImpIC")

        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in all_params.items() if k in valid_fields and pd.notna(v)}
        return cls(**filtered)

    @classmethod
    def from_dict(cls, param_dict: Dict[str, Any]) -> "RSSParameters":
        """Instantiate with custom overrides from a dictionary."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in param_dict.items() if k in valid_fields}
        return cls(**filtered)

