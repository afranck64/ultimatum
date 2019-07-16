import csv
import datetime
import os
import string
import random
import time

import pandas as pd

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify, Response
)


from survey._app import app
from survey.db import get_db, insert, table_exists, update
from survey.admin import get_job_config
from core.utils import cents_repr
from core.models.metrics import MAX_GAIN


######

LAST_MODIFIED_KEY = 'updated'

STATUS_KEY = 'status'

WORKER_KEY = 'worker_id'

JOB_KEY = 'job_id'

PK_KEY = 'rowid'

######
def predict_weak(min_offer):
    return max(min(min_offer-10, MAX_GAIN), 0)

def predict_strong(min_offer):
    return max(min(min_offer+10, MAX_GAIN), 0)

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

def get_table(base, job_id, schema, category=None, treatment=None):
    """
    Generate a table name based on the job_id
    :param base:
    :param job_id:
    :param schema:
    :param category:
    """
    if category is None:
        res = f"{base}_{job_id}"
    else:
        res = f"{base}_{category}_{job_id}"
    if treatment:
        res = f"{treatment}_{res}"
    if schema is not None:
        res = f"{schema}__{res}"
    else:
        res = f"main__{res}"
        

    return res


def get_output_filename(base, job_id, category=None, treatment=None):
    """
    Generate a table name based on the job_id
    :param base:
    :param job_id:
    :param category:
    :param treatment:
    """

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




def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = 0
    return result

def handle_task_index(base, validate_response=None):
    # if session.get("eff", None) and session.get("worker_id", None):
    #     return redirect(url_for("eff.done"))
    app.logger.debug(f"handle_task_index: {base}")
    if request.method == "GET":
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        session[base] = True
        session["worker_id"] = worker_id
        session["job_id"] = job_id
        session["time_start"] = time.time()
    if request.method == "POST":
        response = request.form.to_dict()
        if validate_response is not None and validate_response(response):
            response["time_stop"] = time.time()
            response["time_start"] = session.get("time_start")
            session["response"] = response
            return redirect(url_for(f"tasks.{base}.done"))
        else:
            flash("Please check your fields")
    return render_template(f"tasks/{base}.html")

def value_to_numeric(value):
    f_value = float(value)
    i_value = int(value)
    if f_value == i_value:
        return i_value
    else:
        return f_value

def handle_task_done(base, response_to_result_func=None, response_to_bonus=None, numeric_fields=None, unique_fields=None):
    """
    :param base: (str)
    :param response_to_result_func: (func)
    :param response_to_bonus: (func)
    :param numeric_fields: (None| '*' | list)  if '*' all fields are converted to float
    :param unique_fields: (str|list)
    """
    app.logger.debug(f"handle_task_done: {base}")
    worker_code_key = f"{base}_worker_code"
    worker_bonus_key = f"{base}_worker_bonus"
    if response_to_result_func is None:
        response_to_result_func = response_to_result
    if not session.get(base, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if response_to_bonus is None:
        response_to_bonus = lambda args, **kwargs: 0
    if not session.get(worker_code_key, None) or (app.config["DEBUG"] and False):
        job_id = session["job_id"]
        worker_code = generate_completion_code(base, job_id)
        response = session["response"]
        if numeric_fields is not None:
            if isinstance(numeric_fields, (list, tuple)):
                for field in numeric_fields:
                    try:
                        response[field] = value_to_numeric(response[field])
                    except Exception as err:
                        app.log_exception(err)
            elif numeric_fields == "*":
                for field in response:
                    try:
                        response[field] = value_to_numeric(response[field])
                    except Exception as err:
                        app.log_exception(err)

        worker_id = session["worker_id"]
        response_result = response_to_result_func(response, job_id=job_id, worker_id=worker_id)
        worker_bonus = response_to_bonus(response)
        try:
            save_result2file(get_output_filename(base, job_id), response_result)
        except Exception as err:
            app.log_exception(err)
        try:
            #TODO: check later
            save_result2db(get_table(base, job_id=job_id, schema="result"), response_result, unique_fields=unique_fields)
            increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=worker_bonus)
        except Exception as err:
            app.log_exception(err)
        session.clear()

        session[base] = True
        session[worker_code_key] = worker_code
        session[worker_bonus_key] = worker_bonus
    return render_template("done.html", worker_code=session[worker_code_key], worker_bonus=cents_repr(session[worker_bonus_key]))


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


def get_worker_bonus(job_id, worker_id, con=None):
    """
    :param job_id:
    :param worker_id:
    :param con:
    """
    app.logger.debug(f"get_worker_bonus: job_id: {job_id}, worker_id: {worker_id}")
    if con is None:
        con = get_db("DB")
    table = _get_payment_table(job_id)
    if table_exists(con, table):
        with con:
            row = con.execute(f'select *, rowid from {table} WHERE job_id==? and worker_id==?', (job_id, worker_id)).fetchone()
            if row:
                row_dict = dict(row)
                worker_bonus = row_dict["bonus_cents"]
                return worker_bonus
            else:
                app.logger.error(f"get_worker_bonus: worker not found! job_id: {job_id}, worker_id: {worker_id}")
    return 0

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


def pay_worker_bonus(job_id, worker_id, fig8, con=None):
    """
    :param job_id:
    :param worker_id:
    :param bonus_cents:
    :param fig8:
    :param overwite:
    :param con:
    :returns True if payment was done, False otherwise
    """
    app.logger.debug("pay_worker_bonus")
    if con is None:
        con = get_db("DB")
    table = get_table("jobs", job_id=job_id, schema=None, category="payment")

    should_pay = False
    bonus_cents = 0
    new_paid_bonus_cents = 0
    if table_exists(con, table):
        with con:
            row = con.execute(f'select bonus_cents, paid_bonus_cents, rowid from {table} WHERE job_id==? and worker_id==?', (job_id, worker_id)).fetchone()
            if row:
                # TODO: PAY
                should_pay = True
                bonus_cents = row["bonus_cents"]
                new_paid_bonus_cents = row["bonus_cents"] + row["paid_bonus_cents"]
            else:
                app.logger.warning(f"pay_worker_bonus: worker not found! job_id: {job_id}, worker_id: {worker_id}")
                
    if should_pay:
        #TODO: CHECK LATER FOR PAYMENT
        app.logger.info(f"SHOULD BE PAYING: {bonus_cents} cents")
        #fig8.contributor_pay(worker_id, bonus_cents)
        fig8.contributor_notify(worker_id, f"Thank you for your participation. You just received your total bonus of {cents_repr(bonus_cents)} ^_^")
        with con:
            update(f"UPDATE {table} SET bonus_cents=?, paid_bonus_cents=? WHERE rowid=?", (0, new_paid_bonus_cents, row["rowid"]), con=con)
        return True
    else:
        #fig8.contributor_notify(worker_id, f"Thank you for your participation. You seems to have already been paid. ^_^")
        pass
    return False
############################################################
