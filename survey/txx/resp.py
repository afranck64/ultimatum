import json
import os
import warnings
import random
import string
import csv
import time
import datetime
import io
import hashlib

import pandas as pd

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify, Response
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

from survey._app import app, csrf_protect
from survey.figure_eight import FigureEight, RowState
from core.utils.explanation import get_acceptance_probability, get_best_offer_probability
from core.utils import cents_repr
from core.models.metrics import gain

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
from .prop import insert_row
from survey.utils import save_result2db, save_result2file, get_output_filename, generate_completion_code, get_table, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY, increase_worker_bonus, save_worker_id


############ Consts #################################
# SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE = os.path.splitext(os.path.split(__file__)[1])[0]

LAST_MODIFIED_KEY = '_time_change'

OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, 201, 5)}

OTHERS_MISSING_VALUE = -1

JUDGING_TIMEOUT_SEC = 5*60

if app.config["DEBUG"]:
    JUDGING_TIMEOUT_SEC = 10

# ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

# with open(SURVEY_INFOS_FILENAME) as inp_f:
#     MODEL_INFOS = json.load(inp_f)

######################################################



############# HELPERS   ###########################

class HHI_Resp_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["min_offer"] = None
        self["time_start"] = time.time()
        self["timestamp"] = None


class UploadForm(FlaskForm):
    job_id = StringField("Job id", validators=[DataRequired()])
    overwite = BooleanField("Overwrite")
    submit = SubmitField("Submit")


def resp_to_resp_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        time: server time when genererting the result
        min_offer: final proposer min_offer
        job_id: fig-8 job id
        worker_id: fig-8 worker id
    }
    """
    result = dict(response)
    result["timestamp"] = str(datetime.datetime.now())
    #TODO: clarify this!!!
    result["time_spent_prop"] = response["time_stop"] - response["time_start"]
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result


class ProposerForm(FlaskForm):
    min_offer = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    other_prop = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    other_resp = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

def handle_index(treatment, template=None):
    app.logger.debug("handle_index")
    if template is None:
        template = f"txx/resp.html"
    if request.method == "GET":
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        app.logger.debug(f"handle_index: job_id:{job_id}, worker_id:{worker_id} ")
        session['response'] = HHI_Resp_ADM()
        session["worker_id"] = worker_id
        session["job_id"] = job_id

    if request.method == "POST":
        response = session["response"]
        response["time_stop"] = time.time()
        response["min_offer"] = int(request.form["min_offer"])
        response["other_resp"] = int(request.form.get("other_resp", OTHERS_MISSING_VALUE))
        response["other_prop"] = int(request.form.get("other_prop", OTHERS_MISSING_VALUE))
        session['response'] = response
        return redirect(url_for(f"{treatment}.resp.done"))

    session[BASE] = True
    return render_template(template, offer_values=OFFER_VALUES, form=ProposerForm())

def handle_done(treatment, template=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"txx/resp.done.html"

    worker_code_key = f"{BASE}__worker_code"
    if not session.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not session.get(worker_code_key) or app.config["DEBUG"]:
        job_id = session["job_id"]
        worker_code = generate_completion_code(BASE, job_id)
        response = session["response"]
        worker_id = session["worker_id"]
        resp_result = resp_to_resp_result(response, job_id=job_id, worker_id=worker_id)
        try:
            #save_resp_result(TUBE_RES_FILENAME, resp_result)
            save_result2file(get_output_filename(BASE, job_id, treatment=treatment), resp_result)
        except Exception as err:
            app.log_exception(err)
        try:
            #save_resp_result2db(get_db("RESULT"), resp_result, job_id)
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=resp_result, unique_fields=["worker_id"])
            increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=0)
        except Exception as err:
            app.log_exception(err)
        session.clear()
    

        session[BASE] = True
        session[worker_code_key] = worker_code

        save_worker_id(job_id=job_id, worker_id=worker_id)
    return render_template(template, worker_code=session[worker_code_key])


def finalize_resp(job_id, worker_id, treatment):
    app.logger.debug("finalize_resp")
    table = get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment)
    con = get_db("RESULT")
    with con:
        res = con.execute(f"SELECT * from {table} where job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
        if res:
            resp_result = dict(res)
            insert_row(job_id, resp_result, treatment)
        else:
            app.logger.warnings(f"finalize_resp: worker_id {worker_id} not found - job_id: {job_id}")