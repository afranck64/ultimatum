import csv
import datetime
import os
import string
import random
import time
import json

import pandas as pd

import click
from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response, make_response, session
)
from flask.cli import with_appcontext
from werkzeug.contrib.securecookie import SecureCookie


from survey._app import app, MAXIMUM_CONTROL_MISTAKES
from survey.db import get_db, insert, table_exists, update
from survey.admin import get_job_config
from survey.mturk import MTurk
from core.utils import cents_repr
from core.models.metrics import MAX_GAIN


######

LAST_MODIFIED_KEY = 'updated'

STATUS_KEY = 'status'

WORKER_KEY = 'worker_id'

JOB_KEY = 'job_id'

PK_KEY = 'rowid'

WORKER_CODE_DROPPED = "dropped"

ALL_COOKIES_KEY = "all_cookies"

FAKE_MODEL_OFFSET_RATIO = 0.05

# treatment using available data overwrite the job ids to be prefix + treatment
REF_JOB_ID_PREFIX = "REF"
######
def get_latest_treatment():
    """
    Returns the highest enabled treatment
    """
    treatment = None
    for _treatment in app.config["TREATMENTS"][::-1]:
        if app.config[_treatment]:
            treatment = _treatment.lower()
            break
    if treatment is None:
        raise ValueError("No selectable treatment detected. ")
    return treatment

def get_secret_key_hash():
    return str(hash(app.config["SECRET_KEY"]))

def predict_weak(min_offer):
    return max(min(min_offer-MAX_GAIN*FAKE_MODEL_OFFSET_RATIO, MAX_GAIN), 0)

def predict_strong(min_offer):
    return max(min(min_offer+MAX_GAIN*FAKE_MODEL_OFFSET_RATIO, MAX_GAIN), 0)

def generate_completion_code(base, job_id):
    """
    :param base:
    :param job_id:
    """
    app.logger.debug("generate_completion_code")
    job_config = get_job_config(get_db("DB"), job_id)
    base_completion_code = job_config["base_code"]
    part1 = f"{base}:"
    part2 = base_completion_code
    part3 = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    return "".join([part1, part2, part3])

def get_table(base, job_id, schema, category=None, treatment=None, is_task=False):
    """
    Generate a table name
    :param base:
    :param job_id: has been deprecated internally, just kept to maintain api compatibility
    :param schema:
    :param category:
    :param is_task: (bool) if True, get a table for a feature task, without 'task' instead of job_id
    """
    # if is_task:
    #     job_id = "task"
    # if category is None:
    #     res = f"{base}_{job_id}"
    # else:
    #     res = f"{base}_{category}_{job_id}"
    if category is None:
        res = f"{base}"
    else:
        res = f"{base}_{category}"
    if treatment:
        res = f"{treatment}_{res}"
    if schema is not None:
        res = f"{schema}__{res}"
    else:
        res = f"main__{res}"
        

    return res

def get_masked_worker_id(worker_id):
    if worker_id is None:
        return worker_id
    else:
        return worker_id[:5] + "#####" + worker_id[10:]
        
def is_worker_available(worker_id, table):
    """
    Returns True if <table> exist and contains a column "worker_id" which has the value <worker_id>
    """
    con = get_db()
    sql = f"SELECT * FROM {table} WHERE {WORKER_KEY}=?"
    try:
        res = con.execute(sql, [worker_id]).fetchone()
        if res is None:
            return False
        else:
            return True
    except Exception as err:
        pass
    return False

def save_worker_id(job_id, worker_id, worker_code, assignment_id, base=None):
    """
    Save the given information in a general table
    :param job_id:
    :param worker_id:
    :param worker_code:
    :assignment_id:
    """
    app.logger.debug(f"save_worker_id: job_id: {job_id}, worker_id: {worker_id}")
    if base is None:
        base = "txx"
    table_all = get_table("txx", "all", schema=None)
    
    try:
        insert(pd.DataFrame(data=[{"job_id": job_id, "worker_id": worker_id, "worker_code":worker_code, "assignment_id":assignment_id}]), table=table_all, unique_fields=["worker_id"])
    except Exception as err:
        app.log_exception(err)

def get_output_filename(base, job_id, category=None, treatment=None, is_task=False):
    """
    Generate a table name
    :param base:
    :param job_id: has been deprecated internally, just kept to maintain api compatibility
    :param category:
    :param treatment:
    :param is_task: (bool) if True, get a table for a feature task, without 'task' instead of job_id
    """
    if is_task:
        job_id = "task"
    if category is None:
        basename = f"{base}__{job_id}"
    else:
        basename = f"{base}__{category}__{job_id}"
    if treatment:
        basename = f"{treatment}__{basename}"

    return os.path.join(app.config["OUTPUT_DIR"], f"{basename}.csv")


def save_result2file(filename, response_result, overwrite=False):
    """
    :param filename: (str)
    :param response_result: (dict)
    :param overwite: (bool)
    """
    file_exists = os.path.exists(filename)
    os.makedirs(os.path.split(filename)[0], exist_ok=True)
    open_mode = "w" if overwrite else "a"
    with open(filename, open_mode) as out_f:

        writer = csv.writer(out_f)
        if not file_exists:
            writer.writerow(response_result.keys())
        writer.writerow(response_result.values())

def save_result2db(table, response_result, overwrite=False, unique_fields=None):
    """
    :param table: (str)
    :param response_result: (dict)
    :param overwrite: (bool)
    :param unique_fields: (str|list)
    """
    df = pd.DataFrame(data=[response_result])
    insert(df, table=table, con=get_db("RESULT"), overwrite=overwrite, unique_fields=unique_fields)


def has_worker_submitted(con, job_id, worker_id, treatment=None):
    """
    Return True if the worker's submission was found
    """
    base = "prop"
    table_data = get_table(base, job_id=job_id, schema="data", treatment=treatment)
    if table_exists(con, table_data):
        sql_data = f"select * from {table_data} where (job_id=? or job_id like '{REF_JOB_ID_PREFIX}%') and (resp_worker_id=?)"
        res = con.execute(sql_data, (job_id, worker_id)).fetchone()
        if res:
            return True


    table_result = get_table(base, job_id=job_id, schema="result", treatment=treatment)
    if table_exists(con, table_result):
        sql_result = f"select * from {table_result} where (job_id=? or job_id like '{REF_JOB_ID_PREFIX}%') and (prop_worker_id=? or resp_worker_id=?)"
        res = con.execute(sql_result, (job_id, worker_id, worker_id)).fetchone()
        if res:
            return True
    
    return False


def set_to_cookie(req_response, cookie, key, value):
    cookie_data = request.cookies.get(cookie, None)
    if cookie_data is None:
        cookie_obj = SecureCookie(secret_key=app.config["SECRET_KEY"])
    else:
        cookie_obj = SecureCookie.unserialize(cookie_data, app.config["SECRET_KEY"])
    cookie_obj[key] = value
    all_cookies = session.get(ALL_COOKIES_KEY, [])
    if cookie not in all_cookies:
        all_cookies.append(cookie)
    session[ALL_COOKIES_KEY] = all_cookies
    req_response.set_cookie(cookie, cookie_obj.serialize())

def get_from_cookie(cookie, key):
    cookie_data = request.cookies.get(cookie, None)
    if cookie_data is None:
        cookie_obj = SecureCookie(secret_key=app.config["SECRET_KEY"])
    else:
        cookie_obj = SecureCookie.unserialize(cookie_data, app.config["SECRET_KEY"])
    print("Getting cookie data: ", dict(cookie_obj))
    return cookie_obj.get(key)

def get_cookie_obj(cookie):
    cookie_data = request.cookies.get(cookie, None)
    if cookie_data is None:
        cookie_obj = SecureCookie(secret_key=app.config["SECRET_KEY"])
    else:
        cookie_obj = SecureCookie.unserialize(cookie_data, app.config["SECRET_KEY"])
    return cookie_obj

def set_cookie_obj(req_response, cookie, cookie_obj):
    req_response.set_cookie(cookie, cookie_obj.serialize(), httponly=True)

def approve_and_reject_assignments(job_id, treatment):
    base = "survey"
    table_assignment = get_table("txx", "DEPRECATED_JOB_ID_PARAMETER", schema=None)
    table_survey = get_table(base, "DEPRECATED_JOB_ID_PARAMETER", schema="result", treatment=treatment)
    # sql = f"""
    #     select a.job_id as job_id, a.assignment_id as assignment_id, a.worker_id as worker_id, s.worker_code as worker_code
    #     from {table_assignment} as a left join {table_survey} as s on a.worker_id=s.worker_id
    #     where {table_assignment}.job_id like ?"""
    sql = f"select * from {table_assignment} where {table_assignment}.job_id like ?"
    with get_db() as con:
        df = pd.read_sql(sql, con=get_db(), params=(job_id,))
    api = MTurk(job_id, sandbox=app.config["MTURK_SANDBOX"])
    payment_count = 0
    validation_count = 0
    rejection_count = 0
    for idx in range(df.shape[0]):
        row = df.iloc[idx].to_dict()
        print("ROW: ", row)
        worker_id = row["worker_id"]
        assignment_id = row["assignment_id"]
        print("worker_id", worker_id, type(worker_id), "assignment_id", assignment_id, type(assignment_id))
        success = True
        with get_db("DB") as con:
            if row["worker_code"] != WORKER_CODE_DROPPED and has_worker_submitted(con, job_id, worker_id, treatment):
                    success &= api.approve_assignment(row["assignment_id"], "Thank you for your work.")
                    validation_count += success
                    if success:
                        success &= pay_worker_bonus(job_id, worker_id, api=api, con=con, assignment_id=assignment_id)
                        payment_count += success
                
            else:   #if row["worker_code"] == WORKER_CODE_DROPPED:
                success &= api.reject_assignment(row["assignment_id"], f"You exceeded the number of {MAXIMUM_CONTROL_MISTAKES} mistakes on the control questions.")
                rejection_count += success
            
    app.logger.info(f"validations: {validation_count}, rejections: {rejection_count}, payments: {payment_count}, rows: {df.shape[0]}")

def pay_bonus_assignments(job_id):
    table = get_table("txx", "all", schema=None)
    df = pd.read_sql(f"select * from {table}", get_db("result"))
    df = df[df["job_id"] == job_id]
    api = MTurk(job_id, sandbox=app.config["MTURK_SANDBOX"])

    con = get_db("DB")
    payment_count = 0
    for idx in range(df.shape[0]):
        row = df.iloc[idx]
        worker_id = row["worker_id"]
        assignment_id = row["assignment_id"]
        success = True
        if row["worker_code"] != WORKER_CODE_DROPPED:
            success &= pay_worker_bonus(job_id, worker_id, api=api, con=con, assignment_id=assignment_id)
            payment_count += success
    app.logger.info(f"payments: {payment_count}, rows: {df.shape[0]}")
    
        




def value_to_numeric(value):
    f_value = float(value)
    i_value = int(value)
    if f_value == i_value:
        return i_value
    else:
        return f_value


def _get_payment_table(job_id):
    return get_table("jobs", job_id=job_id, schema=None, category="payment")

def increase_worker_bonus(job_id, worker_id, bonus_cents, con=None):
    """
    :param job_id:
    :param worker_id:
    :param bonus_cents: (int)
    :param con:
    """
    app.logger.debug(f"increase_worker_bonus - job_id: {job_id}, worker_id: {worker_id}, bonus_cents: {bonus_cents}")
    if con is None:
        con = get_db("DB")
    row_data = {'job_id':job_id, 'worker_id': worker_id, 'timestamp': str(datetime.datetime.now()), 'bonus_cents': bonus_cents, 'paid_bonus_cents': 0}
    table = _get_payment_table(job_id)
    worker_row_exists = False
    if table_exists(con, table):
        with con:
            row = con.execute(f'select *, rowid from {table} WHERE job_id==? and worker_id==?', (job_id, worker_id)).fetchone()
            if row:
                worker_row_exists = True
                row_data["bonus_cents"] += row["bonus_cents"]
                row_data["paid_bonus_cents"] += row["paid_bonus_cents"]
                update(f"UPDATE {table} SET bonus_cents=?, paid_bonus_cents=? WHERE rowid=?", (row_data["bonus_cents"], row_data["paid_bonus_cents"], row["rowid"]), con=con)
            
    if not worker_row_exists:
        app.logger.debug(f"increase_worker_bonus: {job_id}, {worker_id}, {bonus_cents}")
        df = pd.DataFrame(data=[row_data])
        insert(df, table, con, unique_fields=["worker_id"])
    con.commit()



def _get_worker_bonus_row(job_id, worker_id, con=None):
    """
    :param job_id:
    :param worker_id:
    :param con:
    """
    app.logger.debug(f"_get_worker_bonus_row: job_id: {job_id}, worker_id: {worker_id}")
    if con is None:
        con = get_db("DB")
    table = _get_payment_table(job_id)
    if table_exists(con, table):
        with con:
            row = con.execute(f'select *, rowid from {table} WHERE job_id==? and worker_id==?', (job_id, worker_id)).fetchone()
            if row:
                row_dict = dict(row)
                return row_dict
            else:
                app.logger.error(f"_get_worker_bonus_row: worker not found! job_id: {job_id}, worker_id: {worker_id}")
    return None

def get_worker_bonus(job_id, worker_id, con=None):
    """
    :param job_id:
    :param worker_id:
    :param con:
    """
    bonus_row = _get_worker_bonus_row(job_id, worker_id, con)
    if bonus_row is None:
        return 0
    return bonus_row["bonus_cents"]

def get_worker_paid_bonus(job_id, worker_id, con=None):
    """
    :param job_id:
    :param worker_id:
    :param con:
    """
    bonus_row = _get_worker_bonus_row(job_id, worker_id, con)
    if bonus_row is None:
        return 0
    return bonus_row["paid_bonus_cents"]

def get_total_worker_bonus(job_id, worker_id, con=None):
    """
    :param job_id:
    :param worker_id:
    :param con:
    """
    bonus_row = _get_worker_bonus_row(job_id, worker_id, con)
    if bonus_row is None:
        return 0
    return bonus_row["bonus_cents"] + bonus_row["paid_bonus_cents"]

def get_resp_worker_id(base, job_id, prop_worker_id, treatment=None):
    """
    :param base:
    :param job_id:
    :param prop_worker_id:
    :param treament:
    """
    con = get_db("RESULT")
    with con:
        table = get_table(base, job_id=job_id, schema="result", treatment=treatment)
        res = con.execute(f"SELECT resp_worker_id from {table} WHERE prop_worker_id=?", (prop_worker_id,)).fetchone()
    resp_worker_id = res["resp_worker_id"]
    return resp_worker_id


def pay_worker_bonus(job_id, worker_id, api, con=None, assignment_id=None, send_notification=False):
    """
    :param job_id:
    :param worker_id:
    :param bonus_cents:
    :param api:
    :param overwite:
    :param con:
    :param assignment_id:
    :returns True if payment was done, False otherwise
    """
    app.logger.debug("pay_worker_bonus")
    if con is None:
        con = get_db("DB")
    table = get_table("jobs", job_id=job_id, schema=None, category="payment")
    job_config = get_job_config(con, job_id)

    should_pay = False
    bonus_cents = 0
    new_paid_bonus_cents = 0
    if table_exists(con, table):
        with con:
            row = con.execute(f'select bonus_cents, paid_bonus_cents, rowid from {table} WHERE job_id==? and worker_id==?', (job_id, worker_id)).fetchone()
            if row:
                bonus_cents = row["bonus_cents"]
                should_pay = bonus_cents > 0
                new_paid_bonus_cents = row["bonus_cents"] + row["paid_bonus_cents"]
            else:
                app.logger.warning(f"pay_worker_bonus: worker not found! job_id: {job_id}, worker_id: {worker_id}")
                
    if should_pay:
        #TODO: CHECK LATER FOR PAYMENT
        app.logger.info(f"SHOULD BE PAYING: {bonus_cents} cents")
        if job_config["payment_max_cents"] > 0 and job_config["payment_max_cents"] > bonus_cents:
            app.logger.warning(f"Attempted payment over max allowed payment to worker {worker_id} on job {job_id}")
            return False
        success = api.contributor_pay(worker_id, bonus_cents, assignment_id)
        if not success:
            app.logger.info(f"Impossible to pay: {bonus_cents} cents to contributor {worker_id}")
            return False
        else:
            with con:
                update(f"UPDATE {table} SET bonus_cents=?, paid_bonus_cents=? WHERE rowid=?", (0, new_paid_bonus_cents, row["rowid"]), con=con)
        if send_notification:
            api.contributor_notify(worker_id, f"Thank you for your participation. You just received your total bonus of {cents_repr(bonus_cents)} ^_^")
        return True
    else:
        if send_notification:
            api.contributor_notify(worker_id, f"Thank you for your participation. Either you have already been paid or your bonus amount to 0.0 USD. ^_^")
    return False


from boto.mturk.question import ExternalQuestion
from survey.mturk import get_mturk_client
def create_hit(treatment, max_assignment=12, frame_height=800, reward=0.5, sandbox=True):
    url = f"https://tube.ddns.net/ultimatum/survey/{treatment}/?adapter=mturk" # <-- this is my website
    mturk = get_mturk_client(sandbox)
    frame_height = 800 # the height of the iframe holding the external hit

    qualificationRequirements =  [
        {
            "QualificationTypeId": "000000000000000000L0",
            "Comparator": "GreaterThanOrEqualTo",
            "IntegerValues": [
                80
            ],
            "RequiredToPreview": False,
            "ActionsGuarded": "Accept"
        },
        {
            "QualificationTypeId": "00000000000000000071",
            "Comparator": "EqualTo",
            "LocaleValues": [
                {
                    "Country": "US"
                }
            ],
            "RequiredToPreview": False,
            "ActionsGuarded": "Accept"
        },
    ]
    if sandbox:
        qualificationRequirements = []

    question = ExternalQuestion(url, frame_height=frame_height)
    new_hit = mturk.create_hit(
        Title='The Ultimatum Bargaining Experiment',
        Description='Take part on an intresting experiment about human behaviour',
        Keywords='survey, bargaining, experiment',
        Reward='0.5',
        MaxAssignments=max_assignment,
        LifetimeInSeconds=7*24*3600,
        AssignmentDurationInSeconds=60*30,
        AutoApprovalDelayInSeconds=6*24*3600,
        Question=question.get_as_xml(),   # <--- this does the trick
        QualificationRequirements=qualificationRequirements,
    )
    click.echo(f"New hit created: {new_hit}")
    return new_hit

############################################################ CLI #

@click.command('approve_and_reject_assignments')
@with_appcontext
def _approve_and_reject_assignments():
    job_id = input("job_id: ")
    treatment = input("treatment: ").lower()
    approve_and_reject_assignments(job_id, treatment)
    click.echo("Approved results and paid bonus")
app.cli.add_command(_approve_and_reject_assignments)

@click.command('pay_bonus_assignments')
@with_appcontext
def _pay_bonus_assignments_command():
    job_id = input("job_id: ")
    pay_bonus_assignments(job_id)
    click.echo("Paid bonus ")

app.cli.add_command(_pay_bonus_assignments_command)

@click.command('add_assignments')
@with_appcontext
def _add_assignments():
    job_id = input("job_id: ")
    nb_assignments = int(input("number new assignments: "))
    api = MTurk(job_id, sandbox=app.config["MTURK_SANDBOX"])
    api.create_additional_assignments(nb_assignments)
app.cli.add_command(_add_assignments)

@click.command('create_hit')
@with_appcontext
def _create_hit():
    sandbox=app.config["MTURK_SANDBOX"]
    click.echo(f"is_sandbox? {sandbox}")
    treatment = input("treatment: ").lower()
    max_assignments = int(input("max_assignments: "))
    create_hit(treatment, max_assignment=max_assignments, sandbox=sandbox)


app.cli.add_command(_create_hit)