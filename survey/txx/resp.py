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
import uuid

import pandas as pd

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response, make_response, session
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

from survey._app import app, csrf_protect, TREATMENTS_AUTO_DSS
from survey.figure_eight import FigureEight, RowState
from core.utils.explanation import get_acceptance_probability, get_best_offer_probability
from core.utils import cents_repr
from core.models.metrics import gain, MAX_GAIN

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
from survey.utils import (
    save_result2db, save_result2file, get_output_filename, generate_completion_code, get_table, get_cookie_obj, set_cookie_obj,
    LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY, increase_worker_bonus
)


############ Consts #################################
# SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE = os.path.splitext(os.path.split(__file__)[1])[0]

LAST_MODIFIED_KEY = '_time_change'

OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, MAX_GAIN+1, 5)}

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
    result["resp_time_spent"] = round(response["time_stop"] - response["time_start"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result


class ProposerForm(FlaskForm):
    min_offer = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    other_prop = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    other_resp = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

def handle_index(treatment, template=None, messages=None):
    app.logger.debug("handle_index")
    if messages is None:
        messages = []
    if template is None:
        template = f"txx/resp.html"
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id:
        req_response = redirect(url_for(f"{treatment}.resp.done"))
        return req_response
    if request.method == "GET":
        app.logger.debug(f"handle_index: job_id:{job_id}, worker_id:{worker_id} ")
        cookie_obj['response'] = HHI_Resp_ADM()
        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id

        for message in messages:
            flash(message)
    if request.method == "POST":
        response = cookie_obj["response"]
        response["time_stop"] = time.time()
        response["min_offer"] = int(request.form["min_offer"])
        response["other_resp"] = int(request.form.get("other_resp", OTHERS_MISSING_VALUE))
        response["other_prop"] = int(request.form.get("other_prop", OTHERS_MISSING_VALUE))
        cookie_obj['response'] = response
        req_response = make_response(redirect(url_for(f"{treatment}.resp.done")))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, form=ProposerForm()))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def handle_done(treatment, template=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"txx/resp.done.html"

    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not cookie_obj.get(worker_code_key):
        job_id = cookie_obj["job_id"]
        worker_code = generate_completion_code(BASE, job_id)
        response = cookie_obj["response"]
        worker_id = cookie_obj["worker_id"]
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
        cookie_obj.clear()
    

        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj[worker_code_key] = worker_code

    req_response = make_response(render_template(template, worker_code=cookie_obj[worker_code_key]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

