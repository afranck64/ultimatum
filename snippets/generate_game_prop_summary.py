import os
import sys
import argparse
import numbers

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.stats.api as sms

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
    parser.add_argument('--transpose', help='Transpose the output', action='store_true')
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
    "t10a": "t10a",
    "t11a": "t11a",
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
    if "offer_dss" not in df_prop.columns:
        df_prop["offer_dss"] = df_prop["offer"]
        df_prop["offer_final"] = df_prop["offer"]
    if "min_offer_dss" not in df_resp.columns:
        df_resp["min_offer_dss"] = df_resp["min_offer"]
        df_resp["min_offer_final"] = df_resp["min_offer"]
    size = min(df_prop.shape[0], df_resp.shape[0])
    df_prop = df_prop.head(size)
    df_resp = df_resp.head(size)
    return df_prop, df_resp

def _get_prop_vs_prop_dss_score(treatment, con, dfs=None, use_percentage=None, use_labels=None, metric=None, as_percentage=None, metric_is_ratio=None, alternative=None):
    df_prop, df_resp = get_prop_resp(treatment)

    prop_values = metric(df_resp["min_offer"], df_prop["offer"])
    prop_value = metrics.get_mean(prop_values)

    prop_dss_values = metric(df_resp["min_offer"], df_prop["offer_dss"])
    prop_dss_value = metrics.get_mean(prop_dss_values)

    auto_dss_values = metric(df_resp["min_offer"], df_prop["ai_offer"])
    auto_dss_value = metrics.get_mean(auto_dss_values)

    if metric_is_ratio:
        n = prop_dss_values.shape[0]
        #z_ratio = sms.proportions_ztest(usage_ratio * n, n, pnull, alternative='larger')
        s, p = 0, 0
    else:
        assert prop_dss_values.shape[0] == prop_dss_values.shape[0]
        s, p =  stats.wilcoxon(prop_values, prop_dss_values, alternative=alternative or 'greater')
    #return {"stat": f"{round(s, 3)}", "p": f"{round(p, 3)}"}

    if as_percentage:
        res = {
            "Proposer": f'{100 * prop_value:.2f} %',
            "Proposer + DSS": f'{100 * prop_dss_value:.2f} %',
            "Auto DSS": f'{100 * auto_dss_value:.2f} %',
            "prop:dss - prop": f'{100 * (prop_dss_value - prop_value):.2f} %',
        }
    else:
        res = {
            "Proposer": f'{prop_value:.2f}',
            "Proposer + DSS": f'{prop_dss_value:.2f}',
            "Auto DSS": f'{auto_dss_value:.2f}',
            "prop:dss - prop": f'{(prop_dss_value - prop_value):.2f} %',
        }

    #res["stat"] = f"{s, 3)}", "p": f"{round(p, 3)}"
    res["$H_0$: equal, H_a: greater"] = f"{s:.3f} ({p:.3f})"
    print("RES: ", res)
    return res

def rejection_ratio_helper(min_offer, offer):
    res = (offer < min_offer)
    res = res.astype(np.float)
    return res

@mark_for_stats()
def get_rejection_ratio(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    # rejection_ratio_lambda = lambda min_offer, offer: (offer >= min_offer) * 1
    return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=rejection_ratio_helper, as_percentage=True)


@mark_for_stats()
def get_prop_summary(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_prop.columns] = df_prop

    df_prop_t00, _ = get_prop_resp("t00")
    resp_stat = stats.ttest_rel(df_prop["offer"], df_prop["offer_final"])

    print("REF to t00", stats.ttest_ind(get_prop_resp("t00")[0]["offer"], df_prop["offer_final"]))
    resp_stat_t00 = stats.ttest_ind(df_prop["offer_final"], df_prop_t00["offer"])

    resp_wc_stat = stats.wilcoxon(df_prop["offer"], df_prop["offer_final"])

    #cm = sms.CompareMeans(sms.DescrStatsW(df_prop["offer"]), sms.DescrStatsW(df_prop["offer_final"]))
    cm = sms.CompareMeans.from_data(df_prop["offer"], df_prop["offer_final"])


    print(treatment, "CHECK: ", cm.tconfint_diff(usevar="unequal"))
    res = {
        "n": df_prop["offer"].shape[0],
        "mean (initial)": metrics.get_mean(df_prop["offer"]),
        "mean": metrics.get_mean(df_prop["offer_final"]),
        "median": df_prop["offer_final"].median(),
        "mode": df_prop["offer_final"].mode()[0],
        "standard deviation": metrics.get_std(df_prop["offer"]),
        "standard deviation": metrics.get_std(df_prop["offer_final"]),

        # "rejection_ratio": rejection_ratio(df_prop)
        "stat": resp_stat[0],
        "p-value": resp_stat[1],
        "stat-t00": resp_stat_t00[0],
        "p-value-t00": resp_stat_t00[1],
        "stat-wc": resp_wc_stat[0],
        "p-value-wc": resp_wc_stat[1],
        }
    return {k: (f"{v:.3f}" if pd.notnull(v) and v!= int(v) else v) for k,v in res.items()}


@mark_for_stats()
def get_prop_system_usage(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_prop.columns] = df_prop
    
    n = df_prop.shape[0]

    usage_ratio = metrics.get_mean(metrics.get_dss_usage(df_prop))
    unique_calls = metrics.get_mean(metrics.get_dss_average_unique_calls(df_prop))

    pnull = 0
    phat = usage_ratio
    
    z_ratio = sms.proportions_ztest(usage_ratio * n, n, pnull, alternative='larger')
    # z_calls = sms.proportions_ztest()
    res = {
        "usage_ratio": f"{100*usage_ratio:.2f} %",
        "mean unique-calls": unique_calls,
        "z-score-usage_ratio": f"{z_ratio[0]:.3f} ({z_ratio[1]:.3f})",
        #"z-score- mean unique-calls": 0
    }

    return {k: (f"{v:.3f}" if  isinstance(v, numbers.Number) and v!= int(v) else v) for k,v in res.items()}
# @mark_for_stats()
# def get_rel_responder_gain2(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if SELECTION != "resp":
#         return
#     df_prop, df_resp = get_prop_resp(treatment)
#     df_prop[df_resp.columns] = df_resp
#     resp_gain = metrics.get_mean(metrics.gain_responder(df_prop["min_offer"], df_prop["offer"]))
#     resp_gain_dss = metrics.get_mean(metrics.gain_responder(df_prop["min_offer_dss"], df_prop["offer_final"]))
#     resp_gain_2 = metrics.get_mean(metrics.get_rel_gain_responder(df_prop["min_offer"], df_prop["min_offer_dss"], df_prop["offer"]))
#     resp_gain_dss_2 = metrics.get_mean(metrics.get_rel_gain_responder(df_prop["min_offer"], df_prop["min_offer_dss"], df_prop["offer_final"]))
#     return {
#         "resp_gain: ": resp_gain,
#         "resp_gain_dss: ": resp_gain_dss,
#         "rel_gain: vs proposer": resp_gain_2,
#         "rel_gain: vs proposer + DSS": resp_gain_dss_2,
#         # "rejection_ratio": rejection_ratio(df_prop)
#         }


#@mark_for_stats()
# def get_ttest_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if SELECTION != "prop":
#         return
#     df_prop, df_resp = get_prop_resp(treatment)
#     x = gain(df_prop["offer"], df_resp["min_offer"])
#     y = gain(df_prop["offer_dss"], df_resp["min_offer"])
#     s, p = stats.ttest_rel(x, y, axis=0)
#     return {"stat": f"{round(s, 3)}", "p": f"{round(p, 3)}"}

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

# @mark_for_stats()
# def get_wilcoxon_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if SELECTION != "prop":
#         return
#     df_prop, df_resp = get_prop_resp(treatment)
#     x = gain(df_prop["offer"], df_resp["min_offer"])
#     y = gain(df_prop["offer_dss"], df_resp["min_offer"])
#     s, p =  stats.wilcoxon(x, y)
#     return {"stat": f"{round(s, 3)}", "p": f"{round(p, 3)}"}


@mark_for_stats()
def get_wilcoxon_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    x = gain(df_prop["offer"], df_resp["min_offer"])
    y = gain(df_prop["offer_dss"], df_resp["min_offer"])
    s, p =  stats.wilcoxon(x, y, alternative='greater')
    # return {"stat": f"{round(s, 3)}", "p": f"{round(p, 3)}"}
    return {"$H_0$: equal, H_a: greater": f"{s:.3f} ({p:.3f})"}



@mark_for_stats()
def get_mean_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "prop":
        return
    return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=gain, as_percentage=False, alternative="less" )


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

        if (args.transpose):
            df = df.T
        print(k)
        if args.use_latex:
            print(df.T.to_latex())
        else:
            print(df.T)
    print("DONE")


if __name__ == "__main__":
    main()