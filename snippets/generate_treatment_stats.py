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
DEMOGRAPHICS_FUNCTIONS = {}

ETHNICITIES = dict([
    ("american_indian_or_alaska_native", "American Indian or Alaska Native"),
    ("asian", "Asian"),
    ("black_or_african_american", "Black or African American"),
    ("hispanic_latino", "Hispanic/Latino"),
    ("hawaiian_or_pacific_islander", "Native Hawaiian or Pacific Islander"),
    ("white", "White/Caucasian"),
    ("other", "Other")
])

AGES = dict([
    ("1825_years", "18-25 Years"),
    ("2635_years", "26-35 Years"),
    ("3645_years", "36-45 Years"),
    ("4655_years", "46-55 Years"),
    ("5665_years", "56-65 Years"),
    ("older_than_65_years", "Older than 65 Years")
])

EDUCATIONS = dict([
    ("less_than_high_school_diploma", "Less than a high school diploma"),
    ("high_school_degree", "High school graduate"), #"High school graduate, diploma or the equivalent"),
    ("bachelor_degree", "Bachelor's degree"),
    ("master_degree", "Master's degree"),
    ("doctorate_degree", "Doctorate degree"),
    ("other", "Other")
])

GENDERS = dict([
    ("female", "Female"),
    ("male", "Male"),
    ("other", "Other")
])

INCOMES = dict([
    ("Primary source of income", "Primary source of income"),
    ("Secondary source of income", "Secondary source of income"),
    ("I earn nearly equal incomes from crowdsourced microtasks and other job(s)", "I earn nearly equal incomes"),   #"I earn nearly equal incomes from crowdsourced microtasks and other job(s)")
])


# overwritten by a command line flag. If true, percentage will be generated instead of frequency
USE_PERCENTAGE = None

USE_LABELS = None

SELECTION = None

def mark_for_stats(label=None):
    def _mark_for_stats(function, label=label):
        if label is None:
            label = function.__name__[4:]
        STATS_FUNCTIONS[label] = function
        return function
    return _mark_for_stats


def mark_for_demographics(label=None):
    def _mark_for_stats(function, label=label):
        if label is None:
            label = function.__name__[4:]
        DEMOGRAPHICS_FUNCTIONS[label] = function
        return function
    return _mark_for_stats

def get_parser():
    parser = argparse.ArgumentParser(description='Generate statistics for a given treatment')
    parser.add_argument('--use-percentage', help='Generate percentages instead of frequencies', action='store_true')
    parser.add_argument('--use-latex', help='Print results as latex table', action='store_true')
    parser.add_argument('--use-labels', help='Print results using description labels', action='store_true')
    parser.add_argument('--output-dir', help='Output directory where csv files were exported')
    parser.add_argument('--selection', help='Whether to restrict the stats to responder or proposers', choices=['prop', 'resp'])
    parser.add_argument('treatments', help='Comma separated treatments')
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
                    df_feedback = df_feedback[FEEDBACK_COLUMNS + ["worker_id"]].set_index("worker_id")

                    df = df.set_index("worker_id")
                    for col in FEEDBACK_COLUMNS:
                        df[col] = df_feedback[col]
                except Exception as err:
                    pass
            df.to_sql(table, con)
            dfs[table] = df
        except Exception as err:
            print("err: ", err)
            pass
    return con, dfs

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

@mark_for_stats()
def get_nb_participants(treatment, con, dfs=None):
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
    if SELECTION == "resp":
        sql += f""" and
            worker_id in (
                select worker_id from result__{treatment}_resp
            )
        """
    elif SELECTION == "prop":
        sql += f""" and
            worker_id in (
                select worker_id from result__{treatment}_prop
            )
        """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_rejected_participants(treatment, con, dfs=None):
    sql = f"""

        select count (distinct(worker_id)) as nb_rejected_participants from (
            select worker_id ,job_id from main__txx where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code == "dropped"
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats()
def get_nb_games_with_demographics(treatment, con, dfs=None):
    sql = f"""
        select count(*) as nb_games_with_demographics from (
            select resp_worker_id, prop_worker_id, job_id from result__{treatment}_prop where job_id!="na"
            
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and resp_worker_id in (select worker_id from main__txx where worker_code != "dropped")
        and prop_worker_id in (select worker_id from main__txx where worker_code != "dropped")
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_responders(treatment, con, dfs=None):
    sql = f"""
        select count (distinct(worker_id)) as nb_responders from (
            select worker_id , job_id from result__{treatment}_resp where job_id!="na"
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_responders_with_demographics(treatment, con, dfs=None):
    sql = f"""
        select count (distinct(worker_id)) as nb_responders_with_demographics from (
            select worker_id ,job_id from result__{treatment}_resp where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code != "dropped"
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats()
def get_nb_proposers(treatment, con, dfs=None):
    sql = f"""
        select count (distinct(worker_id)) as nb_proposers from (
            select worker_id , job_id from result__{treatment}_prop where job_id!="na"
        )
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
    """
    return con.execute(sql).fetchone()[0]


@mark_for_stats()
def get_nb_proposers_with_demographics(treatment, con, dfs=None):
    sql = f"""
        select count (distinct(worker_id)) as nb_proposers_with_demographics from (
            select worker_id ,job_id from result__{treatment}_prop where job_id!="na"
        )
        natural join main__txx
        where job_id in (select distinct job_id from result__{treatment}_resp union select distinct job_id from result__{treatment}_prop)
        and worker_code != "dropped"
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_males(treatment, con, dfs=None):
    sql = f"""
        select count (*) as nb_males
        from result__{treatment}_survey
        where gender='male'
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_females(treatment, con, dfs=None):
    sql = f"""
        select count (*) as nb_females
        from result__{treatment}_survey
        where gender='female'
    """
    return con.execute(sql).fetchone()[0]

@mark_for_stats()
def get_nb_gender_other(treatment, con, dfs=None):
    sql = f"""
        select count (*) as nb_gender_other
        from result__{treatment}_survey
        where gender='other'
    """
    return con.execute(sql).fetchone()[0]

def _get_demographic_stat(name, labels, treatment, con, dfs=None, use_percentage=None, use_labels=None):
    sql = f"""
        select * from result__{treatment}_survey
        where
            worker_id in (
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
    if use_percentage is None:
        use_percentage = USE_PERCENTAGE
    if use_labels is None:
        use_labels = USE_LABELS
    df = pd.read_sql(sql, con)
    df = df[name].values
    result = {}
    for item in df:
        result[item] = result.get(item, 0) + 1

    result = {k:(result[k] if k in result else 0) for k in labels}
    if use_percentage:
        result = {k: f"{round(result[k])} ({round(100 * result[k]/len(df), 2)})" for k in result}

    if use_labels:
        label_result = {}
        for k, l in labels.items():
            label_result[l] = result[k]
        result = label_result
    return result

@mark_for_demographics()
def get_age(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    return _get_demographic_stat("age", AGES, treatment, con, dfs, use_percentage, use_labels)

@mark_for_demographics()
def get_gender(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    return _get_demographic_stat("gender", GENDERS, treatment, con, dfs, use_percentage, use_labels)


@mark_for_demographics()
def get_ethnicity(treatment, con, dfs=None, use_percentage=None, use_labels=None):
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
    if use_percentage is None:
        use_percentage = USE_PERCENTAGE
    if use_labels is None:
        use_labels = USE_LABELS
    labels = ETHNICITIES
    df = pd.read_sql(sql, con)
    df = df['ethnicity'].apply(lambda x: tuple(x.split(':')))
    result = {}
    for items in df:
        for item in items:
            result[item] = result.get(item, 0) + 1/len(items)
    
    if use_percentage:
        result = {k:(result[k] if k in result else 0) for k in labels}
        result = {k: f"{round(result[k])} ({round(100 * result[k]/len(df), 2)})" for k in result}
    else:
        result = {k:(round(result[k]) if k in result else 0) for k in labels}

    if use_labels:
        label_result = {}
        for k, l in labels.items():
            label_result[l] = result.get(k, 0)
        result = label_result
    return result

@mark_for_demographics()
def get_eductation(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    return _get_demographic_stat("education", EDUCATIONS, treatment, con, dfs, use_percentage, use_labels)


@mark_for_demographics()
def get_income(treatment, con, dfs=None, use_percentage=None, use_labels=None):
    return _get_demographic_stat("income", INCOMES, treatment, con, dfs, use_percentage, use_labels)


def generate_stats(treatment, con, dfs):
    stats = {label:function(treatment, con, dfs) for label, function in STATS_FUNCTIONS.items()}
    return stats
    #return pd.Series(stats)


def generate_demographics(treatment, con, dfs):
    demographics = {label:function(treatment, con, dfs) for label, function in DEMOGRAPHICS_FUNCTIONS.items()}
    return demographics


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
        con, dfs = get_con_and_dfs(treatment)
        stats = generate_stats(treatment, con, dfs)
        lst_stats.append(stats)
        demographics = generate_demographics(treatment, con, dfs)
        for k, v in demographics.items():
            lst = results.get(k, [])
            lst.append(v)
            results[k] = lst

    if args.use_latex:
        print(pd.DataFrame(lst_stats, index=treatments).T.to_latex())
    else:
        print(pd.DataFrame(lst_stats, index=treatments).T)
    print("\n\n")
    for k, items in results.items():
        if args.use_latex:
            print(pd.DataFrame(items, index=treatments).T.to_latex())
        else:
            print(pd.DataFrame(items, index=treatments).T)


if __name__ == "__main__":
    main()