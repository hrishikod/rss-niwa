"""
Topological accumulation module for the NIWA RSS Model.
Propagates loads and areas downstream across REC 2.4 reaches using node dictionaries.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


def accumulate_network_loads(
    catch_df: pd.DataFrame,
    quantities: Dict[str, np.ndarray],
    volumes: np.ndarray
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Accumulate multiple load/area quantities downstream in a single topological traversal.
    
    Args:
        catch_df: Catchment DataFrame sorted ascending by 'Hydseq'.
        quantities: Dictionary of quantity_name -> 1D numpy array of values per reach.
        volumes: 1D numpy array of annual flow volumes (m3/yr) for concentration calculation.
        
    Returns:
        results: Dictionary of quantity_name -> (cumulative_total, instream_concentration).
    """
    n_reaches = len(catch_df)
    from_nodes = catch_df["FNODE"].values
    to_nodes = catch_df["TNODE"].values

    # Pre-allocate output arrays
    results = {}
    cum_arrays = {name: np.zeros(n_reaches, dtype=float) for name in quantities}

    # Initialize node accumulation dictionaries
    # Unique node list
    all_nodes = np.unique(np.concatenate([from_nodes, to_nodes]))
    node_maps = {name: dict.fromkeys(all_nodes, 0.0) for name in quantities}

    # Single pass over topologically sorted reaches
    for reach in range(n_reaches):
        u_node = from_nodes[reach]
        v_node = to_nodes[reach]

        for name, val_array in quantities.items():
            upstream_val = node_maps[name][u_node]
            reach_val = upstream_val + val_array[reach]
            cum_arrays[name][reach] = reach_val
            node_maps[name][v_node] += reach_val

    # Calculate in-stream concentrations where applicable
    for name, cum_arr in cum_arrays.items():
        conc_arr = np.divide(cum_arr, volumes, out=np.zeros(n_reaches, dtype=float), where=(volumes != 0))
        results[name] = (cum_arr, conc_arr)

    return results

