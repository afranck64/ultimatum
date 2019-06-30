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
from survey.db import get_db, insert
from survey.admin import get_job_config


######

LAST_MODIFIED_KEY = 'updated'

STATUS_KEY = 'status'

WORKER_KEY = 'worker_id'

JOB_KEY = 'job_id'

PK_KEY = 'rowid'

######


def generate_completion_code(base, job_id):
    """
    :param base:
    :param job_id:
    """
    job_config = get_job_config(get_db("DB"), job_id)
    base_completion_code = job_config["base_code"]
    part1 = f"{base}:"
    part2 = base_completion_code
    part3 = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    return "".join([part1, part2, part3])

def get_table(base, job_id, category=None, treatment=None):
    """
    Generate a table name based on the job_id
    :param base:
    :param job_id:
    :param category:
    """
    if category is None:
        res = f"{base}__{job_id}"
    else:
        res = f"{base}__{category}__{job_id}"
    if treatment:
        res = f"{treatment}__{res}"
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
    return result

def handle_task_index(base):
    # if session.get("eff", None) and session.get("worker_id", None):
    #     return redirect(url_for("eff.done"))
    if request.method == "GET":
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        session[base] = True
        session["worker_id"] = worker_id
        session["job_id"] = job_id
        session["time_start"] = time.time()
    if request.method == "POST":
        response = request.form.to_dict()
        response["time_stop"] = time.time()
        response["time_start"] = session.get("time_start")
        session["response"] = response
        
        print("REDIRECT")
        return redirect(url_for(f"tasks.{base}.done"))
    return render_template(f"tasks/{base}.html")

def value_to_numeric(value):
    f_value = float(value)
    i_value = int(value)
    if f_value == i_value:
        return i_value
    else:
        return f_value

def handle_task_done(base, response2result_func=None, numeric_fields=None, unique_fields=None):
    """
    :param base: (str)
    :param response2result_func: (func)
    :param numeric_fields: (None| '*' | list)  if '*' all fields are converted to float
    :param unique_fields: (str|list)
    """
    if response2result_func is None:
        response2result_func = response_to_result

    if not session.get(base, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not session.get("worker_code") or (app.config["DEBUG"] and False):
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
        response_result = response2result_func(response, job_id=job_id, worker_id=worker_id)
        try:
            save_result2file(get_output_filename(base, job_id), response_result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(base, response_result, job_id, unique_fields=unique_fields)
        except Exception as err:
            app.log_exception(err)
        session.clear()
    

        session[base] = True
        session[f"{base}worker_code"] = worker_code
    return render_template("done.html", worker_code=session[f"{base}worker_code"])