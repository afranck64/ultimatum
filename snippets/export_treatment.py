import os
import sys
import sqlite3

import pandas as pd


sys.path.append(os.path.abspath(".."))

from survey._app import CODE_DIR, app
from survey.db import get_db

import argparse


def get_parser():
    parser = argparse.ArgumentParser(description='Generate statistics for a given treatment')
    parser.add_argument('--output_dir', help='Output directory to save csv files')
    parser.add_argument('--db', type=argparse.FileType('r'),
                        help='Path to the sqlite database file')
    parser.add_argument('treatment', help='treatment to export')
    return parser


def get_con(db):
    con = sqlite3.connect(
        db,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    con.row_factory = sqlite3.Row
    return con

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
    

def mask_workers_ids(df):
    for col in df.columns:
        if "worker_id" in col:
            df[col] = df[col].apply(lambda x: x[:5] + "#####" + x[10:] if x else None, 0)
    return df

EXCLUDED_JOB_IDS = ('na', 'demo', 'check', 'test_auto', 'test')
def export(treatment, con, output_dir, overwrite_all=None):
    os.makedirs(output_dir, exist_ok=True)
    tasks_tables = get_tasks_tables()
    tasks_jobs_ids = get_tasks_jobs_ids(treatment, con)
    for table in get_tables(treatment):
        try:
            if table in tasks_tables:
                sql = f"select * from {table} where job_id in {tuple(tasks_jobs_ids)} and job_id not in {EXCLUDED_JOB_IDS}"
            else:
                sql = f"select * from {table} where job_id not in {EXCLUDED_JOB_IDS}"
            df = pd.read_sql(sql, con)
            #fix for some imported table
            if table == f"result__{treatment}_prop" and "worker_id" not in df.columns:
                df["worker_id"] = df["prop_worker_id"]
            df_masked_worker_ids = mask_workers_ids(df)
            output_file = os.path.join(output_dir, table + ".csv")
            if df_masked_worker_ids.shape[0] > 0:
                if overwrite_all or not os.path.exists(output_file):
                    df_masked_worker_ids.to_csv(output_file, index=False)
                    print(f"Successfully exported table {table}")
                else:
                    ans_overwrite = None
                    while ans_overwrite == None:
                        ans_overwrite = input(f"The file to {table} already exsits. Overwrite? [y]es, [a]ll, [n]o, [c]ancel : ")
                        if ans_overwrite in ("y", "Y", "a", "A"):
                            df_masked_worker_ids.to_csv(output_file, index=False)
                            if ans_overwrite in ("a", "A"):
                                overwrite_all = True
                            print(f"Successfully exported table {table}")
                        elif ans_overwrite in ("c", "C"):
                            print("Export cancelled")
                            return
                        elif ans_overwrite not in ("n", "N"):
                            ans_overwrite = None
                        else:
                            print(f"Skipped table {table}")

            else:
                print(f"Skipped table {table}")
        except Exception as err:
            print(f"Could not export table {table} - {err}")



def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.db is None:
        with app.app_context():
            db = app.config["DATABASE"]
    else:
        db = args.db
    con = get_con(db)
    
    treatment = args.treatment

    if args.output_dir is None:
        output_dir = get_output_dir(treatment)
    else:
        output_dir = args.output_dir

    export(treatment, con, output_dir)


if __name__ == "__main__":
    main()