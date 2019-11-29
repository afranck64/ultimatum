import json
import os
import time
import datetime

from flask import (
    Blueprint
)
import pandas as pd

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response, make_response
)
import warnings
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

#from survey.unit import HHI_Prop_ADM,  prop_to_prop_result, save_prop_result
from core.utils.explanation import get_acceptance_probability, get_best_offer_probability
from core.utils.preprocessing import df_to_xy
from core.utils import cents_repr
from core.models.metrics import gain, MAX_GAIN

from survey._app import app, csrf_protect, TREATMENTS_MODEL_REFS, CODE_DIR
from survey.figure_eight import FigureEight, RowState
from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists, update
from survey.txx.prop import JUDGING_TIMEOUT_SEC, HHI_Prop_ADM, OFFER_VALUES, ProposerForm, prop_to_prop_result, AI_COOKIE_KEY, AI_FEEDBACK_SCALAS, AI_FEEDBACK_ACCURACY_SCALAS
from survey.utils import (save_result2db, save_result2file, get_output_filename, get_table, predict_weak, predict_strong,
    generate_completion_code, increase_worker_bonus, get_cookie_obj, set_cookie_obj, get_secret_key_hash,
    LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY)
############ Consts #################################
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

MODEL_INFOS_KEY = f"{TREATMENT.upper()}_MODEL_INFOS"
MODEL_KEY = f"{TREATMENT.upper()}_MODEL"

PROP_FILENAME = os.path.join(CODE_DIR, "data", "t10", "data__t10_prop.csv")

df_prop = pd.read_csv(PROP_FILENAME)

bp = Blueprint(f"{TREATMENT}.{BASE}", __name__)


######################################################


def get_row(con, job_id, worker_id, treatment, full=True):
    """
    Get a row and change it's state to Judging with a last modified time
    :param con: sqlite3|sqlalchemy connection
    :param job_id: job id
    :param worker_id: worker's id
    :param treatment:
    """
    app.logger.debug("get_row - feedback")
    res = None
    try:
        res = dict(df_prop[df_prop["worker_id"]==worker_id].iloc[0])
        if not full:
            res = {k:v for k,v in res.items() if k in {"worker_id", "min_offer", "ai_offer"}}
        res = dict(res)
    except:
        pass
    return res


def handle_index_dss(treatment, template=None, proposal_class=None, messages=None):
    app.logger.debug("handle_index_dss")
    if messages is None:
        messages = []
    if proposal_class is None:
        proposal_class = HHI_Prop_ADM
    if template is None:
        template = f"txx/prop_dss.html"
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    row_info = cookie_obj.get("row_info")
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id :
        req_response =  make_response(redirect(url_for(f"{treatment}.prop.done", **request.args)))
        return req_response

    if request.method == "GET":
        app.logger.debug(f"handle_index_dss: job_id:{job_id}, worker_id:{worker_id} ")
        row_info = get_row(get_db("DATA"), job_id, worker_id, treatment=treatment, full=False)

        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["row_info"] = row_info

        proposal = proposal_class()
        proposal["time_start"] = time.time()
        proposal["time_start_dss"] = time.time()
        cookie_obj['proposal'] = proposal_class()
        if not row_info:
            warnings.warn(f"ERROR: The row can no longer be processed. job_id: {job_id} - worker_id: {worker_id}")

            flash(f"There are either no more rows available or you already took part on this survey. Thank you for your participation")
            return render_template("error.html")
        for message in messages:
            flash(message)
    if request.method == "POST":
        proposal = cookie_obj["proposal"]
        proposal["feedback_understanding"] = request.form["feedback_understanding"]
        proposal["feedback_explanation"] = request.form["feedback_explanation"]
        proposal["feedback_accuracy"] = request.form["feedback_accuracy"]
        proposal["time_stop"] = time.time()
        proposal["time_stop_stop"] = time.time()
        offer_dss = request.form["offer_dss"]
        try:
            offer_dss = int(offer_dss)
        except ValueError as err:
            app.logger.warning(f"Conversion error: {err}")
            offer_dss = None
        proposal["offer_dss"] = offer_dss
        cookie_obj['proposal'] = proposal
        req_response =  make_response(redirect(url_for(f"{treatment}.prop.done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    prop_check_url = url_for(f"{treatment}.prop.check")
    req_response = make_response(
        render_template(
            template, offer_values=OFFER_VALUES, scalas=AI_FEEDBACK_SCALAS, accuracy_scalas=AI_FEEDBACK_ACCURACY_SCALAS, form=ProposerForm(), prop_check_url=prop_check_url, max_gain=MAX_GAIN
        )
    )
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response



def handle_done(treatment, template=None, response_to_result_func=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"txx/{BASE}.done.html"
    if response_to_result_func is None:
        response_to_result_func = prop_to_prop_result
    worker_code_key = f"{BASE}_worker_code"
    worker_bonus_key = f"{BASE}_worker_bonus"
    cookie_obj = get_cookie_obj(BASE)
    ai_cookie_obj = get_cookie_obj(AI_COOKIE_KEY)
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not (cookie_obj.get("worker_code")):
        job_id = cookie_obj["job_id"]
        worker_code = generate_completion_code(base=BASE, job_id=job_id)
        proposal = cookie_obj["proposal"]
        proposal["completion_code"] = worker_code
        proposal.update(ai_cookie_obj.get("ai_proposal", {}))
        row_info = cookie_obj["row_info"]
        worker_id = cookie_obj["worker_id"]
        row_info = get_row(get_db(), job_id, worker_id, TREATMENT)
        offer = proposal["offer_dss"]

        min_offer = row_info["min_offer"]
        worker_bonus = 0
        if offer >= min_offer:
            worker_bonus = 5
        prop_result = response_to_result_func(proposal, job_id=job_id, worker_id=worker_id, row_data=row_info)
        prop_result["worker_bonus"] = worker_bonus
        try:
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=treatment), prop_result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=prop_result, unique_fields=["worker_id"])
            #increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=worker_bonus, con=get_db("DB"))
        except Exception as err:
            app.log_exception(err)
        cookie_obj.clear()

        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj[worker_bonus_key] = cents_repr(worker_bonus)
        cookie_obj[worker_code_key] = worker_code
    req_response = make_response(render_template(template, worker_code=cookie_obj[worker_code_key]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response


############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    #NOTE: for the feedback we skip the proposer without dss
    return redirect(url_for(f"{TREATMENT}.prop.index_dss", **request.args))


@bp.route("/prop_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [
        """You have been assigned the role of a PROPOSER. As a PROPOSER, you will make an offer to the RESPONDER. You have the option to use an AI Recommendation System (AI System) to help you decide which offer to make. The system was trained using prior interactions of comparable bargaining situations.""",
        """To use the AI System, simply select a test offer and submit it to the system. The system will tell you its estimates on:
1. The probability that your offer will be accepted by your specific RESPONDER.
2. The probability that your offer is the minimal offer accepted by your specific RESPONDER.

You can use the system as often as you want."""
    ]
    return handle_index_dss(TREATMENT, messages=messages)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    