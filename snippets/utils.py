import os
import sys
import sqlite3

import pandas as pd


sys.path.append(os.path.abspath(".."))

from survey._app import CODE_DIR, app
from survey.db import get_db

import argparse

db = ":memory:"

TREATMENTS = ["t00", "t10a", "t10b", "t11a", "t11b", "t11c", "t12", "t12a", "t13", "t13a", "t20", "t20a"]

def get_output_dir(treatment, code_dir=None):
    if code_dir is None:
        code_dir = CODE_DIR
    return os.path.join(CODE_DIR, "data", treatment.lower(), "export")


def get_tables(treatment):
    tables = [
        f"data__{treatment}_prop",
        "result__cc",
        "result__cpc",
        "result__exp",
        "result__ras",
        "result__risk",
        "main__txx",
        f"result__{treatment}_resp",
        f"result__{treatment}_prop",
        f"result__{treatment}_survey",

    ]
    return tables

FEEDBACK_COLUMNS_T10_FEEDBACK = ["feedback_accuracy", "feedback_explanation", "feedback_explanation"]
def get_con_and_dfs(treatment, db=None):
    if db is None:
        db = ":memory:"
    con = sqlite3.connect(
        db,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    con.row_factory = sqlite3.Row
    dfs = {}
    output_dir = get_output_dir(treatment)
    for table in get_tables(treatment):
        try:
            csv_file = os.path.join(output_dir, table + ".csv")
            df = pd.read_csv(csv_file)

            # try to fix t10:
            if treatment == "t10" and table == "result__t10_prop":
                try:
                    output_dir_feedback = get_output_dir(f"{treatment}_feedback")
                    csv_file_feedback = os.path.join(output_dir_feedback, f"result__{treatment}_feedback_prop" + ".csv")
                    df_feedback = pd.read_csv(csv_file_feedback)
                    df_feedback = df_feedback[FEEDBACK_COLUMNS_T10_FEEDBACK + ["worker_id"]].set_index("worker_id")

                    df = df.set_index("worker_id")
                    for col in FEEDBACK_COLUMNS_T10_FEEDBACK:
                        df[col] = df_feedback[col]
                except Exception as err:
                    pass
            df.to_sql(table, con, index=False)
            dfs[table] = df
        except Exception as err:
            if table == "main__txx":
                df = pd.DataFrame([], columns=["worker_id", "assignment_id", "worker_code", "job_id"])
                df.to_sql(table, con, index=False)
            # print("err: ", err)
            pass
    return con, dfs

def get_all_con_and_dfs():
    all_cons = {}
    all_dfs = {}
    for treatment in TREATMENTS:
        con, dfs = get_con_and_dfs(treatment)
        all_cons[treatment] = con
        all_dfs.update(dfs)
    # print(list(all_dfs.keys()))
    return all_cons, all_dfs


def generate_stat_sentence(mean1, std1, mean2, std2, s, p, dof, diff=None, label1="REF1", label2="REF2", alpha=0.05,):
    if p < alpha:
        sentence = f"There was a significant difference in the scores for {label1} (M={mean1:.2f}, SD={std1:.2f}) and {label2} (M={mean2:.2f}, SD={std2:.2f}) conditions; t({dof:.0f})={s}, p={p:.3f}. Diff={diff}"
    else:
        sentence = f"There was not a significant difference in the scores for {label1} (M={mean1:.2f}, SD={std1:.2f}) and {label2} (M={mean2:.2f}, SD={std2:.2f}) conditions; t({dof:.0f})={s}, p={p:.3f}. Diff={diff}"
    return sentence

def generate_cat_stat_sentence(mean1, std1, mean2, std2, s, p, dof, diff=None, label1="REF1", label2="REF2", alpha=0.05,):
    if p < alpha:
        sentence = f"There was a significant difference in the scores for {label1} (M={mean1:.2f}, SD={std1:.2f}) and {label2} (M={mean2:.2f}, SD={std2:.2f}) conditions; t({dof:.0f})={s}, p={p:.3f}. Diff={diff or (mean1 - mean2):.3f}"
    else:
        sentence = f"There was not a significant difference in the scores for {label1} (M={mean1:.2f}, SD={std1:.2f}) and {label2} (M={mean2:.2f}, SD={std2:.2f}) conditions; t({dof:.0f})={s}, p={p:.3f}. Diff={diff or (mean1 - mean2):.3f}"
    return sentence