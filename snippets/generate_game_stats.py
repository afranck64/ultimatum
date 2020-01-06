import os
import sys
import argparse
import pandas as pd
from scipy import stats

sys.path.append(os.path.abspath(".."))

from survey._app import CODE_DIR, app
from core.models.metrics import gain_mean, rejection_ratio, gain
from utils import get_con_and_dfs, get_all_con_and_dfs
import metrics

STATS_FUNCTIONS = {}





# overwritten by a command line flag. If true, percentage will be generated instead of frequency
USE_PERCENTAGE = None

USE_LABELS = None

SELECTION = None

AI_FEEDBACK_ACCURACY_SCALAS = {
    "ai_much_worse": "AI much worse than PROPOSER",
    "ai_worse": "AI worse",
    "ai_sligthly_worse": "AI slighly worse",
    "ai_equal_to_proposer": "AI equal to PROPOSER",
    "ai_slighly_better": "AI slighly better",
    "ai_better": "AI better",
    "ai_much_better": "AI much better than the PROPOSER",
}

AI_FEEDBACK_SCALAS = {
    1: "strongly_disagree",
    2: "disagree",
    3: "slightly_disagree",
    4: "neutral",
    5: "slightly_agree",
    6: "agree",
    7: "strongly_agree"
}

def get_parser():
    parser = argparse.ArgumentParser(description='Generate statistics for a given treatment')
    parser.add_argument('--use-percentage', help='Generate percentages instead of frequencies', action='store_true')
    parser.add_argument('--use-latex', help='Print results as latex table', action='store_true')
    parser.add_argument('--use-labels', help='Print results using description labels', action='store_true')
    parser.add_argument('--output-dir', help='Output directory where csv files were exported')
    parser.add_argument('--selection', help='Whether to restrict the stats to responder or proposers', choices=['prop', 'resp'])
    parser.add_argument('treatments', help='Comma separated treatments')
    return parser


ALL_CONS, ALL_DFS = get_all_con_and_dfs()


def mark_for_stats(label=None):
    def _mark_for_stats(function, label=label):
        if label is None:
            label = function.__name__[4:]
        STATS_FUNCTIONS[label] = function
        return function
    return _mark_for_stats



def get_count_participants(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    sql = f"""
        select * from result__{treatment}_survey
        where worker_id not in (
            select worker_id from main__txx where worker_code == 'dropped'
        )
    """
    if SELECTION == "resp":
        sql = f"""
                select worker_id from result__{treatment}_resp
        """
    elif SELECTION == "prop":
        sql = f"""
                select worker_id from result__{treatment}_prop
        """
    else:
        sql = f"""
        select * from (
            select worker_id from result__{treatment}_resp
            union
            select worker_id from result__{treatment}_prop
        )
        """
    df = pd.read_sql(sql, con)
    return df.shape[0]

@mark_for_stats()
def get_count(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    sql = f"""
        select * from result__{treatment}_survey
        where worker_id in (
            select worker_id from main__txx where worker_code != 'dropped'
        )
    """
    if SELECTION == "resp":
        sql += f"""and
            worker_id in (
                select worker_id from result__{treatment}_resp
            )
        """
    elif SELECTION == "prop":
        sql += f"""and
            worker_id in (
                select worker_id from result__{treatment}_prop
            )
        """
    df = pd.read_sql(sql, con)
    count_stats = df.shape[0]
    count_all = get_count_participants(treatment, con, dfs, use_percentage, use_labels)

    return {"count": f"{count_stats} ({count_all}*)"}

RESPONDERS = {
    "t00": "t00",
    "t10a": "t10a",
    "t10b": "t10a",
    "t11a": "t11a",
    "t11b": "t11a",
    "t11c": "t11a",
    "t20": "t20a",
    "t20a": "t20a",
}


PROPOSERS = {
    "t00": "t00",
    "t12a": "t10a",
    "t13a": "t10a",
    "t20a": "t10a",
}

def get_prop_resp(treatment):
    if SELECTION == "prop":
        df_prop = ALL_DFS[f"result__{treatment}_prop"].copy()
        if treatment in {"t20", "t20a"}:
            df_prop["offer"] = df_prop["ai_offer"]
            df_prop["offer_dss"] = df_prop["ai_offer"]
            df_prop["offer_final"] = df_prop["ai_offer"]
        df_resp = ALL_DFS[f"result__{RESPONDERS[treatment]}_resp"].copy()
    elif SELECTION == "resp":
        df_resp = ALL_DFS[f"result__{treatment}_resp"].copy()
        df_prop = ALL_DFS[f"result__{PROPOSERS[treatment]}_prop"].copy()
    size = min(df_prop.shape[0], df_resp.shape[0])
    df_prop = df_prop.head(size)
    df_resp = df_resp.head(size)
    return df_prop, df_resp

def _get_prop_vs_prop_dss_score(treatment, con, dfs=None, use_percentage=None, use_labels=None, metric=None, as_percentage=None):
    df_prop, df_resp = get_prop_resp(treatment)

    if as_percentage:
        res = {
            "Proposer": f'{round(100 * metric(df_resp["min_offer"], df_prop["offer"]), 2)} %',
            "Proposer + DSS": f'{round(100 * metric(df_resp["min_offer"], df_prop["offer_dss"]), 2)} %',
            "Auto DSS": f'{round(100 * metric(df_resp["min_offer"], df_prop["ai_offer"]), 2)} %',
        }
    else:
        res = {
            "Proposer": f'{round(metric(df_resp["min_offer"], df_prop["offer"]), 2)}',
            "Proposer + DSS": f'{round(metric(df_resp["min_offer"], df_prop["offer_dss"]), 2)}',
            "Auto DSS": f'{round(metric(df_resp["min_offer"], df_prop["ai_offer"]), 2)}', 
        }

    return res

@mark_for_stats()
def get_rejection_ratio(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=rejection_ratio, as_percentage=True)

@mark_for_stats()
def get_mean_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=gain_mean, as_percentage=False)

@mark_for_stats()
def get_rel_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    return {"rel_gain": metrics.get_rel_gain_proposer(df_prop["min_offer"], df_prop["offer"], df_prop["offer_dss"])}

@mark_for_stats()
def get_woa(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    return {"woa": metrics.woa(df_prop["offer_final"], df_prop["offer"], df_prop["ai_offer"])}


@mark_for_stats()
def get_system_usage(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    return {"system_usage": f"{metrics.get_dss_usage(df_prop):.2f}"}



@mark_for_stats()
def get_rel_responder_min_offer(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "resp":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_resp.columns] = df_resp

    _, df_presp_t00 = get_prop_resp("t00")
    resp_stat = stats.ttest_rel(df_resp["min_offer"], df_resp["min_offer_dss"])

    print("REF to t00", stats.ttest_ind(get_prop_resp("t00")[0]["min_offer"], df_resp["min_offer_dss"]))
    resp_stat_t00 = stats.ttest_ind(df_resp["min_offer_dss"], df_presp_t00["min_offer"])
    return {
        "min_offer": metrics.get_mean(df_resp["min_offer"]),
        "min_offer_dss": metrics.get_mean(df_resp["min_offer_dss"]),
        # "rejection_ratio": rejection_ratio(df_prop)
        "stat": resp_stat[0],
        "p-value": resp_stat[1],
        "stat-t00": resp_stat_t00[0],
        "p-value-t00": resp_stat_t00[1],
        }

@mark_for_stats()
def get_rel_responder_gain2(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "resp":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_resp.columns] = df_resp
    resp_gain = metrics.get_mean(metrics.gain_responder(df_prop["min_offer"], df_prop["offer"]))
    resp_gain_dss = metrics.get_mean(metrics.gain_responder(df_prop["min_offer_dss"], df_prop["offer_final"]))
    resp_gain_2 = metrics.get_mean(metrics.get_rel_gain_responder(df_prop["min_offer"], df_prop["min_offer_dss"], df_prop["offer"]))
    resp_gain_dss_2 = metrics.get_mean(metrics.get_rel_gain_responder(df_prop["min_offer"], df_prop["min_offer_dss"], df_prop["offer_final"]))
    return {
        "resp_gain: ": resp_gain,
        "resp_gain_dss: ": resp_gain_dss,
        "rel_gain: vs proposer": resp_gain_2,
        "rel_gain: vs proposer + DSS": resp_gain_dss_2,
        # "rejection_ratio": rejection_ratio(df_prop)
        }


# @mark_for_stats()
# def get_ttest_rel(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     df_prop = ALL_DFS[f"result__{treatment}_prop"]
#     offers = df_prop["offer"]
#     offers_dss = df_prop["offer_dss"]
#     return stats.ttest_rel(offers, offers_dss, axis=0)

# # @mark_for_stats()
# def get_ks_2samp(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     df_prop = ALL_DFS[f"result__{treatment}_prop"]
#     offers = df_prop["offer"]
#     offers_dss = df_prop["offer_dss"]
#     s, p = stats.ks_2samp(offers, offers_dss)
#     return {"stat": s, "p": p}


# @mark_for_stats()
# def get_wilcoxon(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     df_prop = ALL_DFS[f"result__{treatment}_prop"]
#     offers = df_prop["offer"]
#     offers_dss = df_prop["offer_dss"]
#     s, p =  stats.wilcoxon(offers, offers_dss)
#     return {"stat": s, "p": p}

@mark_for_stats()
def get_wilcoxon_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    x = gain(df_prop["offer"], df_resp["min_offer"])
    y = gain(df_prop["offer_dss"], df_resp["min_offer"])
    s, p =  stats.wilcoxon(x, y)
    return {"stat": f"{round(s, 3)}", "p": f"{round(p, 3)}"}




# @mark_for_stats()
# def get_spearman(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     df_prop = ALL_DFS[f"result__{treatment}_prop"]
#     offers = df_prop["offer"]
#     offers_dss = df_prop["offer_dss"]
#     s, p =  stats.spearmanr(offers, offers_dss)
#     return {"stat": s, "p": p}



def generate_stats(treatment, con, dfs):
    stats = {label:function(treatment, con, dfs) for label, function in STATS_FUNCTIONS.items()}
    return stats


def main():
    global USE_PERCENTAGE, USE_LABELS, SELECTION
    parser = get_parser()
    args = parser.parse_args()

    treatments = args.treatments.split(",")

    USE_PERCENTAGE = args.use_percentage

    USE_LABELS = args.use_labels

    SELECTION = args.selection

    results = dict()
    lst_stats = []
    for treatment in treatments:
        if "." in treatment:
            treatment, SELECTION = treatment.split(".")
        else:
            SELECTION = args.selection
        #con, dfs = get_con_and_dfs(treatment)
        con = ALL_CONS[treatment]
        dfs = ALL_DFS
        stats = generate_stats(treatment, con, dfs)
        for k, v in stats.items():
            lst = results.get(k, [])
            lst.append(v)
            results[k] = lst

    print("\n\n")
    for k, items in results.items():
        columns = None
        if items and isinstance(items[0], (tuple, list, set, dict)):
            columns = list(items[0])
        df = pd.DataFrame(items, index=treatments, columns=columns)
        print(k)
        if args.use_latex:
            print(df.T.to_latex())
        else:
            print(df.T)
    print("DONE")


if __name__ == "__main__":
    main()