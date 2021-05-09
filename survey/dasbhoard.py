import json
import os
import warnings
import random
import string
import csv
import time
import datetime
import io

import pandas as pd

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

from survey._app import app, csrf_protect
from survey.db import get_db, table_exists, insert, update


bp = Blueprint("dashboard", __name__)


###### helpers #####
class JobConfig(dict):
    def __init__(self, job_id, api_key, nb_rows=0, unique_worker=True, base_code="", expected_judgments=0, payment_max_cents=0):
        super().__init__()
        self["job_id"] = job_id
        self["api_key"] = api_key
        self["nb_rows"] = nb_rows
        self["unique_worker"] = unique_worker
        self["base_code"] = base_code
        self["expected_judgments"] = expected_judgments
        self["payment_max_cents"] = payment_max_cents
        self.__dict__ = self


def get_job_config(con, job_id, table="jobs"):
    """
    Return a job config or the default configuration if the job wasn't found
    :param con: (Connection)
    :param job_id:
    :param table:
    """
    _job_config = None
    if table_exists(con, table):
        with con:
            _job_config = con.execute(f"SELECT * from {table} WHERE job_id==?", (job_id,)).fetchone()
    if _job_config is None:
        job_config = JobConfig(job_id, api_key='')
    else:
        job_config = JobConfig(**_job_config)
    return job_config

def get_treaments_infos(con, treatments):
    all_infos = {}
    #treatments = ["t31", "t30"]
    for treatment in treatments:
        infos = {}
        table_survey = f"result__{treatment}_survey"
        if table_exists(con, table_survey):
            # sql_completed_surveys = f"""
            # SELECT
            #     job_id,
            #     case completion_code WHEN 'dropped' THEN
            #         "dropped"
            #     ELSE
            #         "completed"
            #     END dropped,
            #     count(*) value
            # FROM {table_survey}
            # GROUP BY job_id, completion_code='dropped'
            # """
            sql_completed_surveys = f"""
            SELECT
                job_id,
                case completion_code WHEN 'dropped' THEN
                    "dropped"
                ELSE
                    "completed"
                END,
                count(*) value
            FROM {table_survey}
            GROUP BY job_id, completion_code='dropped'
            """

            sql_completed_surveys = f"""select
                r.job_id,
                count(*) count,
                (select count(*) from {table_survey}  where job_id==r.job_id and completion_code=='dropped') dropped
            FROM {table_survey} r
            GROUP BY job_id;
            """

            res = con.execute(sql_completed_surveys).fetchall()
            app.logger.warning(f"RESULT_raw: {[list(item) for item in res]}")
            res = [{'job_id':item[0], 'count' : item[1], "dropped":item[2]} for item in res]
            app.logger.warning(f"RESULT: {res}")

            # sql_completed_surveys = f"""
            # SELECT
            #     job_id,
            #     count(*)
            # FROM {table_survey}
            # GROUP BY job_id
            # """

            # completed_surveys_raw = dict(con.execute(sql_completed_surveys).fetchall())
            infos["survey"] =res    #{str(itm):itm for itm in completed_surveys_raw}
        else:
            infos["survey"] = None
        
        table_resp = f"result__{treatment}_resp"
        if table_exists(con, table_resp):
            sql_completed_resp = f"""
            SELECT
                job_id,
                count(*)
            FROM {table_resp}
            GROUP BY job_id
            """
            completed_resp = dict(con.execute(sql_completed_resp).fetchall())
            infos["resp"] = completed_resp
        else:
            infos["resp"] = None

        table_prop = f"result__{treatment}_prop"
        if table_exists(con, table_prop):
            sql_completed_prop = f"""
            SELECT
                job_id,
                count(*)
            FROM {table_prop}
            GROUP BY job_id
            """
            completed_prop = dict(con.execute(sql_completed_prop).fetchall())
            infos["prop"] = completed_prop
        else:
            infos["prop"] = None

        all_infos[treatment] = infos
    return all_infos


def update_job(con, job_id, job_config, table="jobs"):
    if not table_exists(con, table):
        insert(pd.DataFrame(data=[job_config]), table=table, con=con)
    else:
        with con:
            check = con.execute(f"SELECT job_id from jobs where job_id==?", (job_id,)).fetchone()
            if check:
                update(
                    f"UPDATE {table} SET api_key=?, base_code=?, expected_judgments=?, payment_max_cents=?",
                    args=(job_config['api_key'], job_config['base_code'], job_config['expected_judgments'], job_config['payment_max_cents']),
                    con=con
                )
            else:
                insert(pd.DataFrame(data=[job_config]), table=table, con=con)

            
    
####################


@csrf_protect.exempt
@bp.route("/dashboard", methods=["GET", "POST"])
def index():
    app.logger.debug(f"dashboard.index")
    treatments = [treatment.lower() for treatment in reversed(app.config["TREATMENTS"])]
    infos = get_treaments_infos(get_db('DB'), treatments)
    return render_template("dashboard.html", treatments=treatments, infos=infos)

