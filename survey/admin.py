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


bp = Blueprint("admin", __name__)


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
@bp.route("/admin", methods=["GET", "POST"])
def index():
    if request.method=="POST":
        job_id = request.form.get('job_id')
        api_key = request.form.get('api_key')
        secret = request.form.get('secret')
        base_code = request.form.get('base_code')
        expected_judgments = 0
        try:
            expected_judgments = int(request.form.get("expected_judgments"))
        except:
            pass
        if secret != app.config['ADMIN_SECRET']:
            flash('Incorrect secret, please try again')
            return redirect(request.url)
        job_config = JobConfig(job_id=job_id, api_key=api_key, base_code=base_code, expected_judgments=expected_judgments)
        update_job(get_db('DB'), job_id, job_config)
        flash("Job successfully configured")
    return render_template("admin.html")

