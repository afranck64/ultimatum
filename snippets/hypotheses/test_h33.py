import os
import sys
import argparse
import numbers

import numpy as np
import pandas as pd
import researchpy as rp
from scipy import stats
import statsmodels.stats.api as sms
import statsmodels.sandbox.stats.runs as sms2


sys.path.extend([os.path.join(os.path.split(__file__)[0], parent) for parent in ["..", "../.."]])

from survey._app import CODE_DIR, app
from core.models.metrics import gain_mean, rejection_ratio, gain
from utils import get_con_and_dfs, get_all_con_and_dfs, generate_stat_sentence
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
    # "t00": "t00",
    "t10a": "t10a",
    # "t10b": "t10a",
    "t11a": "t10a",
    # "t11b": "t11a",
    # "t11c": "t11a",
    # "t20": "t20a",
    # "t20a": "t20a",
}


PROPOSERS = {
    # "t00": "t00",
    # "t10a": "t10a",
    # "t11a": "t11a",
    "t12a": "t11a",
    "t13a": "t11a",
    # "t20a": "t10a",
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

    # in most cases, all data are taken from the df_prop dataframe, so resp data are overriden according to teh setup.
    df_prop["min_offer"] = df_resp["min_offer"]
    df_prop["min_offer_dss"] = df_resp["min_offer"]
    df_prop["min_offer_final"] = df_resp["min_offer_final"]
    return df_prop, df_resp

def _get_prop_vs_prop_dss_score(treatment, con, dfs=None, use_percentage=None, use_labels=None, metric=None, as_percentage=None, is_categorical=None, alternative=None):
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop_ref, df_resp_ref = get_prop_resp("t12a")
    prop_values = metric(df_resp["min_offer"], df_prop["offer"])
    prop_value = metrics.get_mean(prop_values)

    prop_dss_values = metric(df_resp["min_offer"], df_prop["offer_dss"])
    prop_dss_value = metrics.get_mean(prop_dss_values)


    prop_values_ref = metric(df_resp_ref["min_offer"], df_prop_ref["offer_dss"])
    prop_value_ref = metrics.get_mean(prop_values_ref)

    # auto_dss_values = metric(df_resp["min_offer"], df_prop["ai_offer"])
    # auto_dss_value = metrics.get_mean(auto_dss_values)

    dof = 0
    diff = None
    if is_categorical:
        table, res = rp.crosstab(pd.Series(prop_values_ref), pd.Series(prop_dss_values), test='chi-square')
        s, p, r = res.results.values
        
        test_label = f"(pearson chi2)"
        
        test_label = f"chi2"
        print("Conclusion: ", generate_cat_stat_sentence(np.mean(resp_dss_values), np.std(resp_dss_values), np.mean(auto_dss_values), np.std(auto_dss_values), s, p, dof, diff=diff, label1=treatment+".dss", label2="t20.dss"))
    else:
        table, res = rp.ttest(pd.Series(prop_values_ref), pd.Series(prop_dss_values), paired=False)
        s = res.results[2]
        if alternative=="greater":
            p = res.results[4]
        elif alternative == "less":
            p = res.results[5]
        elif alternative in (None, 'two-sided'):
            p = res.results[3]
        r = res.results[9]
        
        diff = res.results[0] 
        dof = res.results[1]
        print("Conclusion: ", generate_stat_sentence(np.mean(resp_dss_values), np.std(resp_dss_values), np.mean(auto_dss_values), np.std(auto_dss_values), s, p, dof, diff=diff, label1=treatment+".dss", label2="t20.dss"))

        
        test_label = f"(ttest independent) H0: {'equal' if alternative in {None, 'two-sided'} else alternative}"
    print("RESUME: ", res)
    if as_percentage:
        res = {
            "Proposer + DSS": f'{100 * prop_dss_value:.2f} %',
            "T10": f'{100 * prop_value_ref:.2f} %',
        }
    else:
        res = {
            "Proposer + DSS": f'{prop_dss_value:.2f}',
            "T10": f'{prop_value_ref:.2f}',
        }
    if is_categorical:
        res[test_label] = f"{s:.3f} (p: {p:.3f}, phi: {r:.3f})"
    else:
        res[test_label] = f"{s:.3f} (p: {p:.3f}, r: {r:.3f})"
    return res

# @mark_for_stats()
# def get_rejection_ratio(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     rejection_ratio_lambda = lambda min_offer, offer: (offer < min_offer) * 1
#     return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=rejection_ratio_lambda, as_percentage=True, is_categorical=True, alternative='less')

# @mark_for_stats()
# def get_mean_proposer_gain(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if SELECTION != "prop":
#         return
#     return _get_prop_vs_prop_dss_score(treatment, con, dfs, use_percentage, use_labels, metric=gain, as_percentage=False,)

@mark_for_stats()
def get_responder_min_offer(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "resp":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_resp.columns] = df_resp

    _, df_resp_ref = get_prop_resp("t12a")
    resp_values = df_resp["min_offer_final"]
    resp_ref_values = df_resp_ref["min_offer_final"]

    #print("MEANS: ", np.mean(resp_ref_values), metrics.get_mean(resp_ref_values))
    table, res = rp.ttest(pd.Series(resp_values), pd.Series(resp_ref_values), paired=False)
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]
    diff = res.results[0] 
    dof = res.results[1]
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]
    
    print("Conclusion: ", generate_stat_sentence(np.mean(resp_ref_values), np.std(resp_ref_values), np.mean(resp_values), np.std(resp_values), s, p, dof, diff=diff, label1="t12.dss",  label2=treatment+".dss"))


    print("Table:", table)        
    print("Res:", res)

    res = {
        "min_offer T12": metrics.get_mean(resp_ref_values),
        "min_offer T13": metrics.get_mean(resp_values),

        # "rejection_ratio": rejection_ratio(df_prop)
        }
    test_label = f"(ttest independent) H0: equal"
    res = {k: (f"{v:.3f}" if pd.notnull(v) and v!= int(v) else v) for k,v in res.items()}
    res["min_offer" + test_label] = f"{s:.3f} (p: {p:.3f}, r: {r:.3f})"
    return res


@mark_for_stats()
def get_rel_responder_min_offer(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "resp":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_resp.columns] = df_resp

    _, df_resp_ref = get_prop_resp("t12a")
    resp_values = metrics.get_data(metrics.get_rel_min_offer_df(df_resp))
    resp_ref_values = metrics.get_data(metrics.get_rel_min_offer_df(df_resp_ref))

    table, res = rp.ttest(pd.Series(resp_values), pd.Series(resp_ref_values), paired=False)
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]
    diff = res.results[0] 
    dof = res.results[1]
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]

    tmp_res = stats.mannwhitneyu(resp_values, resp_ref_values)
    print("TMP values: ", tmp_res)
    
    print("Conclusion: ", generate_stat_sentence(np.mean(resp_ref_values), np.std(resp_ref_values), np.mean(resp_values), np.std(resp_values), s, p, dof, diff=diff, label1="t12.dss",  label2=treatment+".dss"))


    print("Table:", table)        
    print("Res:", res)

    res = {
        "rel. min_offer T12": metrics.get_mean(resp_ref_values),
        "rel. min_offer T13": metrics.get_mean(resp_values),

        # "rejection_ratio": rejection_ratio(df_prop)
        }
    test_label = f"(ttest independent) H0: equal"
    res = {k: (f"{v:.3f}" if pd.notnull(v) and v!= int(v) else v) for k,v in res.items()}
    res["min_offer" + test_label] = f"{s:.3f} (p: {p:.3f}, r: {r:.3f})"
    return res


@mark_for_stats()
def get_rel_responder_abs_df(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if SELECTION != "resp":
        return
    df_prop, df_resp = get_prop_resp(treatment)
    df_prop[df_resp.columns] = df_resp

    df_prop_full, df_resp_ref = get_prop_resp("t12a")
    resp_values = metrics.get_data(metrics.get_rel_responder_abs_df(df_prop))
    resp_ref_values = metrics.get_data(metrics.get_rel_responder_abs_df(df_prop_full))

    table, res = rp.ttest(pd.Series(resp_values), pd.Series(resp_ref_values), paired=False)
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]
    diff = res.results[0] 
    dof = res.results[1]
    s = res.results[2]
    p = res.results[3]
    r = res.results[9]

    
    print("Conclusion: ", generate_stat_sentence(np.mean(resp_ref_values), np.std(resp_ref_values), np.mean(resp_values), np.std(resp_values), s, p, dof, diff=diff, label1="t12.dss",  label2=treatment+".dss"))


    print("Table:", table)        
    print("Res:", res)

    res = {
        "rel. min_offer T12": metrics.get_mean(resp_ref_values),
        "rel. min_offer T13": metrics.get_mean(resp_values),

        # "rejection_ratio": rejection_ratio(df_prop)
        }
    test_label = f"(ttest independent) H0: equal"
    res = {k: (f"{v:.3f}" if pd.notnull(v) and v!= int(v) else v) for k,v in res.items()}
    res["min_offer" + test_label] = f"{s:.3f} (p: {p:.3f}, r: {r:.3f})"


    print()

    return res

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