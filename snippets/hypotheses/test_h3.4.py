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


sys.path.append(os.path.abspath(".."))

from survey._app import CODE_DIR, app
from core.models.metrics import gain_mean, rejection_ratio, gain
from utils import get_con_and_dfs, get_all_con_and_dfs, generate_stat_sentence
import metrics
STATS_FUNCTIONS = {}




# overwritten by a command line flag. If true, percentage will be generated instead of frequency
USE_PERCENTAGE = None

USE_LABELS = None

SELECTION = None


ALL_CONS, ALL_DFS = get_all_con_and_dfs()



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



RESPONDERS = {
    # "t00": "t00",
    "t10a": "t10a",
    "t10b": "t10a",
    "t11a": "t10a",
    "t11b": "t11a",
    "t11c": "t11a",
    # "t20": "t20a",
    # "t20a": "t20a",
}


PROPOSERS = {
    # "t00": "t00",
    "t10a": "t10a",
    "t11a": "t11a",
    "t12a": "t11a",
    "t13a": "t11a",
    # "t20a": "t10a",
}



def mark_for_stats(label=None):
    def _mark_for_stats(function, label=label):
        if label is None:
            label = function.__name__[4:]
        STATS_FUNCTIONS[label] = function
        return function
    return _mark_for_stats

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


def _get_feedback_accuracy_stat(name, labels, treatment, con, dfs=None, use_percentage=None, use_labels=None, transformer=None):
    if SELECTION is None:
        sql = f"""
            select * from (
                select {name}, worker_id from result__{treatment}_resp
                union
                select {name}, worker_id from result__{treatment}_prop
                
            )
        """
    else:
        sql = f"""
            select * from (
                select {name}, worker_id from result__{treatment}_{SELECTION}
            )
        """
    if use_percentage is None:
        use_percentage = USE_PERCENTAGE
    if use_labels is None:
        use_labels = USE_LABELS
    try:
        df = pd.read_sql(sql, con)
    except Exception as err:
        df = pd.DataFrame(columns=[name])
    data = df[name].values
    result = {}
    for item in data:
        result[item] = result.get(item, 0) + 1

    result = {k:(result[k] if k in result else 0) for k in labels}

    if transformer is not None:
        result = transformer(result, data)
    if use_percentage:
        new_result = {}
        for k, v in result.items():
            if isinstance(v, (int, float)):
                new_result[k] = f"{round(result[k])} ({round(100 * result[k]/(len(data) or 1), 2)})"
            else:
                new_result[k] = v
        # result = {k: f"{round(result[k])} ({round(100 * result[k]/(len(data) or 1), 2)})" for k in result}
        result = new_result

    if use_labels:
        label_result = {}
        for k, l in labels.items():
            label_result[l] = result.get(k)
        result = label_result
    
    if (data==None).sum()==data.shape[0]:
        for k in result:
            result[k] = "n/a"
    return result



AI_FEEDBACK_ACCURACY_SCALAS_REV = {
    "ai_much_worse": 1,
    "ai_worse": 2,
    "ai_sligthly_worse": 3,
    "ai_equal_to_proposer": 4,
    "ai_slighly_better": 5,
    "ai_better": 6,
    "ai_much_better": 7,
}

def transformer_acc(tmp, data):
    res = {}
    print(tmp)
    for k, v in tmp.items():
        if "better" in k:
            res["ai_better"]  = res.get("ai_better", 0) + v
        elif "worse" in k:
            res["worse"]  = res.get("worse", 0) + v
        elif "equal" in k:
            res["equal"]  = res.get("equal", 0) + v
        else:
            res[k]  = res.get(k, 0) + v
    data = [AI_FEEDBACK_ACCURACY_SCALAS_REV[v] for v in data]
    res["mean"] = f"{round((np.mean(data)), 2)}"
    res["std"] = f"{round((np.std(data)), 2)}"
    return res

@mark_for_stats()
def get_feedback_accuracy(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if not use_labels:
        return _get_feedback_accuracy_stat("feedback_accuracy", AI_FEEDBACK_ACCURACY_SCALAS, treatment, con, dfs, use_percentage, use_labels, None)
    else:
        return _get_feedback_accuracy_stat("feedback_accuracy", AI_FEEDBACK_ACCURACY_SCALAS, treatment, con, dfs, use_percentage, use_labels)



@mark_for_stats()
def get_info_accuracy(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    if treatment in ("t13a", "t13"):
        ref = "t12a"
    elif treatment in ("t11a", "t11b"):
        ref = "t10b"
    else:
        ref = treatment

    df_prop, df_resp = get_prop_resp(treatment)
    df_prop_ref, df_resp_ref = get_prop_resp(ref)

    if SELECTION == "prop":
        values = df_prop["feedback_accuracy"]
        values_ref = df_prop_ref["feedback_accuracy"]
    else:
        values = df_resp["feedback_fairness"]
        values_ref = df_resp_ref["feedback_fairness"]

    # feedback_fairness

    values_ref = values_ref.apply(lambda x: AI_FEEDBACK_ACCURACY_SCALAS_REV.get(x, x))
    values = values.apply(lambda x: AI_FEEDBACK_ACCURACY_SCALAS_REV.get(x, x))

    
    # print("DIFF: ", values, values_ref)
    # resp_values = metrics.get_data(metrics.get_rel_min_offer_df(df_resp))
    # resp_ref_values = metrics.get_data(metrics.get_rel_min_offer_df(df_resp_ref))

    values 

    print("MEDIAN: ", values.median(), values_ref.median())
    dof = 0
    diff = 0
    table, res = rp.crosstab(pd.Series(values), pd.Series(values_ref), test='g-test')
    s, p, r = res.results.values
    # s = res.results[2]
    # p = res.results[3]
    # r = res.results[9]
    # diff = res.results[0] 
    # dof = res.results[1]
    # s = res.results[2]
    # p = res.results[3]
    # r = res.results[9]

    tmp_res = None
    tmp_res = stats.mannwhitneyu(values, values_ref, use_continuity=False)
    # tmp_res = stats.ranksums(values, values_ref)
    print("TMP values: ", tmp_res)
    
    print("Conclusion: ", generate_stat_sentence(np.mean(values_ref), np.std(values_ref), np.mean(values), np.std(values), s, p, dof, diff=diff, label1="t12.dss",  label2=treatment+".dss"))


    print("Table:", table)        
    print("Res:", res)

    res = {
        "rel. min_offer T12": metrics.get_mean(values_ref),
        "rel. min_offer T13": metrics.get_mean(values),

        # "rejection_ratio": rejection_ratio(df_prop)
        }
    test_label = f"(ttest independent) H0: equal"
    res = {k: (f"{v:.3f}" if pd.notnull(v) and v!= int(v) else v) for k,v in res.items()}
    res["min_offer" + test_label] = f"{s:.3f} (p: {p:.3f}, r: {r:.3f})"
    return res


def transformer_alt(tmp, data):
    res = {}
    values = []
    coefs = []
    for k, v in tmp.items():
        if k in (1, 2, 3):
            res["disagree"]  = res.get("disagree", 0) + v
        elif k in (4, ):
            res["neutral"]  = res.get("neutral", 0) + v
        elif k in (5, 6, 7):
            res["agree"]  = res.get("agree", 0) + v
        else:
            res[k]  = res.get(k, 0) + v
        values.append(v*k)
        coefs.append(k)
    data = [{"disagree"}]
    res["mean"] = f"{round((np.mean(data)), 2)}"
    res["std"] = f"{round((np.std(data)), 2)}"
    #res["cronbach alpha"] = cronbach_alpha(data)
    return res


# @mark_for_stats()
# def get_feedback_alternative(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if not use_labels:
#         return _get_feedback_accuracy_stat("feedback_alternative", AI_FEEDBACK_SCALAS, treatment, con, dfs, use_percentage, use_labels, transformer=transformer_alt)
#     else:
#         return _get_feedback_accuracy_stat("feedback_alternative", AI_FEEDBACK_SCALAS, treatment, con, dfs, use_percentage, use_labels)


# @mark_for_stats()
# def get_feedback_fairness(treatment, con, dfs=None, use_percentage=None, use_labels=None):
#     if not use_labels:
#         return _get_feedback_accuracy_stat("feedback_fairness", AI_FEEDBACK_SCALAS, treatment, con, dfs, use_percentage, use_labels, transformer=transformer_alt)
#     else:
#         return _get_feedback_accuracy_stat("feedback_fairness", AI_FEEDBACK_SCALAS, treatment, con, dfs, use_percentage, use_labels)



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
        con, dfs = get_con_and_dfs(treatment)
        demographics = generate_stats(treatment, con, dfs)
        for k, v in demographics.items():
            lst = results.get(k, [])
            lst.append(v)
            results[k] = lst

    # if args.use_latex:
    #     print(pd.DataFrame(lst_stats, index=treatments).T.to_latex())
    # else:
    #     print(pd.DataFrame(lst_stats, index=treatments).T)
    print("\n\n")
    print(len(results))
    for k, items in results.items():
        columns = None
        if items and isinstance(items[0], (tuple, list, set, dict)):
            columns = list(items[0])
        df = pd.DataFrame(items, index=treatments, columns=columns)
        print(k)
        if args.use_latex:
            print(df.to_latex())
        else:
            print(df)



if __name__ == "__main__":
    main()