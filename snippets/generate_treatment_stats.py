import os
import sys
import sqlite3

import pandas as pd


sys.path.append(os.path.abspath(".."))

from survey._app import CODE_DIR, app
from survey.db import get_db

import argparse

db = ":memory:"

STATS_FUNCTIONS = {}

def mark_for_stats(function, label=None):
    if label is None:
        label = function.__name__[4:]
    STATS_FUNCTIONS[label] = function
    return function

def get_parser():
    parser = argparse.ArgumentParser(description='Generate statistics for a given treatment')
    parser.add_argument('--output_dir', help='Output directory to save csv files')
    parser.add_argument('treatment', help='treatment to export')
    return parser


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

FEEDBACK_COLUMNS = ["feedback_accuracy", "feedback_explanation", "feedback_explanation"]
def get_con(treatment, db=None):
    if db is None:
        db = ":memory:"
    con = sqlite3.connect(
        db,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    con.row_factory = sqlite3.Row

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
                    df_feedback = df_feedback[FEEDBACK_COLUMNS + ["worker_id"]].set_index("worker_id")

                    df = df.set_index("worker_id")
                    for col in FEEDBACK_COLUMNS:
                        df[col] = df_feedback[col]
                except Exception as err:
            df.to_sql(table, con)
        except Exception as err:
            print("err: ", err)
            pass
    return con

def get_tasks_tables():
    return {
        "result__cc",
        "result__cpc",
        "result__exp",
        "result__ras",
        "result__risk"
    }

def get_tasks_jobs_ids(treatment, con):
    resp_table = f"result__{treatment}_resp"
    try:
        df = pd.read_sql(f"select distinct job_id from {resp_table}", con)
        jobs_ids = list(df["job_id"])
    except:
        jobs_ids = []
    return jobs_ids

@mark_for_stats
def get_nb_participants(treatment, con):
    sql = f"""
        select count (distinct(worker_id)) as nb_participants from (
            select worker_id , job_id from result__{treatment}_prop where job_id!="na"
            union
            select worker_id , job_id from result__{treatment}_resp where job_id!="na"
            union
            select worker_id , job_id from main__txx where job_id!="na"
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats
def get_nb_rejected_participants(treatment, con):
    sql = f"""

        select count (distinct(worker_id)) as nb_rejected_participants from (
            select worker_id ,job_id from main__txx where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code == "dropped"
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats
def get_nb_games_with_demographics(treatment, con):
    sql = f"""
        select count(*) as nb_games_with_demographics from (
            select resp_worker_id, prop_worker_id, job_id from result__{treatment}_prop where job_id!="na"
            
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and resp_worker_id in (select worker_id from main__txx where worker_code != "dropped")
        and prop_worker_id in (select worker_id from main__txx where worker_code != "dropped")
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats
def get_nb_responders(treatment, con):
    sql = f"""
        select count (distinct(worker_id)) as nb_responders from (
            select worker_id , job_id from result__{treatment}_resp where job_id!="na"
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats
def get_nb_responders_with_demographics(treatment, con):
    sql = f"""
        select count (distinct(worker_id)) as nb_responders_with_demographics from (
            select worker_id ,job_id from result__{treatment}_resp where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code != "dropped"
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats
def get_nb_proposers(treatment, con):
    sql = f"""
        select count (distinct(worker_id)) as nb_proposers from (
            select worker_id , job_id from result__{treatment}_prop where job_id!="na"
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats
def get_nb_proposers_with_demographics(treatment, con):
    sql = f"""
        select count (distinct(worker_id)) as nb_proposers_with_demographics from (
            select worker_id ,job_id from result__{treatment}_prop where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code != "dropped"
    """
    return con.execute(sql).fetchone()[0]


def generate_stats(treatment, con):
    stats = {label:function(treatment, con) for label, function in STATS_FUNCTIONS.items()}
    return pd.Series(stats)


def main():
    parser = get_parser()
    args = parser.parse_args()
    
    treatment = args.treatment

    con = get_con(treatment)

    stats = generate_stats(treatment, con)
    print(stats)


if __name__ == "__main__":
    main()