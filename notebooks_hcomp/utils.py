
from core.models.metrics import cross_compute, avg_gain_ratio, gain_mean, rejection_ratio, loss_sum, MAX_GAIN

def get_infos(min_offer, offer, metrics=None, do_cross_compute=False):
    if metrics is None:
        metrics = [avg_gain_ratio, gain_mean, rejection_ratio, loss_sum]
    #df = pd.DataFrame()
    size1, size2 = len(min_offer), len(offer)
    if size1 != size2:
        print("WARNING: different shapes!!!", size1, size2)
        min_size = min(size1, size2)
        min_offer = min_offer[:min_size]
        offer = offer[:min_size]
    infos = dict()
    for idx, metric in enumerate(metrics):
        if do_cross_compute:
            infos[metric.__name__] = cross_compute(min_offer, offer, metric)
        else:
            infos[metric.__name__] = metric(min_offer, offer)

    return infos


import os
import sys
module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

import pandas as pd
import numpy as np




def get_dfs_full_prop():
    dfs = {}
    dfs_full = {}

    result_df = pd.DataFrame(index=range(105))
    index=["Proposer", "Proposer + DSS"]
    stats = pd.DataFrame(index=index)

    #TREATMENTS = {"t00", "t10a", "t10b", "t11a", "t11b", "t11c"}
    TREATMENTS_MAPPING = {
        "t00": "T0.P",
        "t10a": "TAI.Pu",
        "t10b": "TAI.Pn",
        "t11a": "TXAI.Pu",
        "t11b": "TXAI.Pi",
        "t11c": "TXAI.Pua",
        
    }
    TREATMENTS = TREATMENTS_MAPPING.values()

    for treatment, new_treatment in TREATMENTS_MAPPING.items():

        # Read and sanitize the data
        df_full = pd.read_csv(f"../data/{treatment}/export/result__{treatment}_prop.csv")
        dfs_full[new_treatment] = df_full
        
    return dfs_full


def get_dfs_full_resp():
    TREATMENT = "hcomp.txx.resp"

    export_folder = f"../data/output/diagrams/{TREATMENT}"
    os.makedirs(export_folder, exist_ok=True)

    dfs = {}
    dfs_full = {}

    result_df = pd.DataFrame(index=range(105))
    stats = pd.DataFrame(index=["min_offer", "min_offer_final"])

    TREATMENTS = {"t00", "t10a", "t11a", "t12", "t13", "t20"}
    TREATMENTS_MAPPING = {
        "t00": "T0.R",
    #     "t10a": "TAI.R",
    #     "t10b": "TAI.R",
        "t12": "TAI.R",
        "t13": "TXAI.R",
        "t20": "TAIAuto.R",
        
    }
    TREATMENTS = sorted(TREATMENTS_MAPPING.values())

    for treatment, new_treatment in TREATMENTS_MAPPING.items():

        # Read and sanitize the data
        df = pd.read_csv(f"../data/{treatment}/export/result__{treatment}_resp.csv")
        df_full = df.copy()
        # drop_cols = ["worker_id", "resp_worker_id", "prop_worker_id", "updated", "status", "job_id", "status", "timestamp", "rowid", "offer_dss", "offer", "offer_final", "completion_code"]
        drop_cols = ["worker_id", "resp_worker_id", "prop_worker_id", "updated", "status", "job_id", "status", "timestamp", "rowid", "offer_dss", "offer", "offer_final", "completion_code", "prop_time_spent"]
        df = df[[col for col in df.columns if col not in drop_cols]]
        if "min_offer_final" not in df_full:
            df_full["min_offer_final"] = df_full["min_offer"]
        
        treatment = new_treatment
        dfs[treatment] = df
        dfs_full[treatment] = df_full
        result_df[treatment+"."+"min_offer"] = df_full["min_offer"]
        result_df[treatment+"."+"min_offer_final"] = df_full["min_offer_final"]
        stats[treatment] = [df_full["min_offer"].mean(), df_full["min_offer_final"].mean()]
        
    return dfs_full
    #cols = [col for col in df.columns if col != "min_offer"] + ["min_offer"]
