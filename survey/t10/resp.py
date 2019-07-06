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
#from survey.unit import HHI_Resp_ADM,  resp_to_resp_result, save_resp_result
from notebooks.utils.explanation import get_acceptance_propability, get_best_offer_probability
from notebooks.utils import cents_repr
from notebooks.models.metrics import gain

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
#from survey.hhi_prop_adm import insert_row, as get_prop_table
from .prop import insert_row
from survey.utils import save_result2db, save_result2file, get_output_filename, generate_completion_code, get_table, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY


############ Consts #################################
SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

LAST_MODIFIED_KEY = '_time_change'

OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, 201, 5)}

JUDGING_TIMEOUT_SEC = 5*60

if app.config["DEBUG"]:
    JUDGING_TIMEOUT_SEC = 10

ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

with open(SURVEY_INFOS_FILENAME) as inp_f:
    MODEL_INFOS = json.load(inp_f)

bp = Blueprint(f"{TREATMENT}.resp", __name__)
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
    
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result


class ProposerForm(FlaskForm):
    min_offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

@csrf_protect.exempt
@bp.route("/resp/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        session['response'] = HHI_Resp_ADM()
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        session["worker_id"] = worker_id
        session["job_id"] = job_id

    if request.method == "POST":
        response = session["response"]
        response["time_stop"] = time.time()
        min_offer = request.form["min_offer"]
        try:
            min_offer = int(min_offer)
        except ValueError:
            min_offer = None
        response["min_offer"] = min_offer
        ##TODO return redirect
        session['response'] = response
        return redirect(url_for(f"{TREATMENT}.resp.done"))

    session[BASE] = True
    return render_template(f"{TREATMENT}/resp.html", offer_values=OFFER_VALUES, form=ProposerForm())

@bp.route("/resp/done")
def done():
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
            save_result2file(get_output_filename(BASE, job_id, treatment=TREATMENT), resp_result)
        except Exception as err:
            app.log_exception(err)
        try:
            #save_resp_result2db(get_db("RESULT"), resp_result, job_id)
            save_result2db(table=get_table(base=BASE, job_id=job_id, treatment=TREATMENT), response_result=resp_result, unique_fields=["worker_id"])
        except Exception as err:
            app.log_exception(err)
        print("RESP_DONE")
        insert_row(job_id, resp_result)
        session.clear()
    

        session[BASE] = True
        session[worker_code_key] = worker_code
    return render_template(f"{TREATMENT}/resp.done.html", worker_code=session[worker_code_key])


def _process_judgments(signal, payload, job_id, job_config):
    """
    :param signal: (str)
    :param payload: (dict)
    :param job_id: (int|str)
    :param job_config: (JobConfig)
    """
    with app.app_context():
        app.logger.info(f"Started part-payments..., with signal: {signal}")
        if signal == "new_judgements":
            try:
                judgments_count = payload['judgments_count']
                fig8 = FigureEight(job_id, job_config["api_key"])
                con = get_db("RESULT")
                for idx in range(judgments_count):
                    worker_judgment = payload['results']['judgments'][idx]
                    #TODO: Not paying any bonus yet
                    #TODO: may compute the next level here
                    # worker_id = worker_id = worker_judgment["worker_id"]
                    # worker_bonus = get_worker_bonus(con, job_id, worker_id)
                    #pay_worker_bonus(con, job_id, worker_id, worker_bonus, fig8)
            except Exception as err:
                app.logger.error(f"Error: {err}")
        elif signal == "unit_complete":
            #TODO: may process the whole unit here
            pass
        app.logger.info("Started part-payments..., with signal: %s ^_^ " % signal)

@csrf_protect.exempt
@bp.route("/resp/webhook", methods=["GET", "POST"])
def webhook():
    form = request.form.to_dict()
    signal = form['signal']
    if signal in {'unit_complete', 'new_judgements'}:
        app.logger.info(f"SIGNAL: {signal}")
        payload_raw = form['payload']
        signature = form['signature']
        payload = json.loads(payload_raw)
        job_id = payload['job_id']
        
        job_config = get_job_config(get_db("DB"), job_id)
        payload_ext = payload_raw + job_config["api_key"]
        verif_signature = hashlib.sha1(payload_ext.encode()).hexdigest()
        if signature == verif_signature:
            args = (signal, job_id, job_config, payload)
            app.config["THREADS_POOL"].starmap_async(_process_judgments, [args])
    return Response(status=200)
