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

from survey._app import app, csrf_protect, TREATMENTS_AUTO_DSS, CODE_DIR
from survey.figure_eight import FigureEight, RowState
from core.utils.explanation import get_acceptance_probability, get_best_offer_probability
from core.utils import cents_repr
from core.models.metrics import gain, MAX_GAIN

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists, update
from survey.utils import (
    save_result2db, save_result2file, get_output_filename, generate_completion_code, get_table, get_cookie_obj, set_cookie_obj,
    LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY, increase_worker_bonus
)
from survey.globals import AI_FEEDBACK_SCALAS, AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS
from survey.txx.helpers import finalize_resp

############ Consts #################################
# SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE = os.path.splitext(os.path.split(__file__)[1])[0]

OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, MAX_GAIN+1, 5)}

OTHERS_MISSING_VALUE = -1

JUDGING_TIMEOUT_SEC = 5*60

if app.config["DEBUG"]:
    JUDGING_TIMEOUT_SEC = 10

# ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

# with open(SURVEY_INFOS_FILENAME) as inp_f:
#     MODEL_INFOS = json.load(inp_f)

SKIP_RESP_KEYS = {"status", "update", "feedback_accuracy", "feedback_alternative", "feedback_fairness"}
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
    result["min_offer_final"] = response.get("min_offer_dss", response.get("min_offer"))
    result["timestamp"] = str(datetime.datetime.now())
    #TODO: clarify this!!!
    result["resp_time_spent"] = round(response["time_stop"] - response["time_start"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result


def create_resp_data_table(treatment, ref):
    app.logger.debug(f"create_table_data - {ref}, {treatment}")
    con = get_db()
    table = get_table(BASE, None, "data", treatment=treatment)
    assert len(ref)==4, "expected references of the form <txyz>"
    required_columns = """ai_calls_acceptance_probability,ai_calls_best_offer_probability,ai_calls_count_repeated,ai_calls_offers,ai_calls_pauses,ai_nb_calls,ai_offer,feedback_accuracy,feedback_explanation,feedback_understanding,job_id,offer,offer_dss,offer_final,prop_time_spent,prop_worker_id,timestamp,worker_id""".split(",")
    if not table_exists(con, table):
        df = pd.read_csv(os.path.join(CODE_DIR, 'data', ref, 'export', f'result__{ref}_prop.csv'))
        columns = [col for col in required_columns if col in df.columns]
        df = df[columns]

        df["job_id"] = f"REF{ref.upper()}"
        df[STATUS_KEY] = RowState.JUDGEABLE
        df[WORKER_KEY] = None
        df["updated"] = 0
        with con:
            df.to_sql(table, con, index=False)
            app.logger.debug("create_table_data: table created")

def create_resp_data_auto_prop_table(treatment, ref, fixed_offer=None):
    app.logger.debug(f"create_resp_data_auto_prop_table - {ref}, {treatment}")
    con = get_db()
    table = get_table(BASE, None, "data", treatment=treatment)
    assert len(ref)==4, "expected references of the form <txyz>"
    required_columns = """ai_calls_acceptance_probability,ai_calls_best_offer_probability,ai_calls_count_repeated,ai_calls_offers,ai_calls_pauses,ai_nb_calls,ai_offer,feedback_accuracy,feedback_explanation,feedback_understanding,job_id,model_type,offer,offer_dss,offer_final,prop_time_spent,prop_worker_id,timestamp,worker_id""".split(",")
    columns_to_clear = """ai_calls_acceptance_probability,ai_calls_best_offer_probability,ai_calls_count_repeated,ai_calls_offers,ai_calls_pauses,ai_nb_calls,feedback_accuracy,feedback_explanation,feedback_understanding,job_id,prop_time_spent,prop_worker_id,timestamp,worker_id""".split(",")
    if not table_exists(con, table):
        df = pd.read_csv(os.path.join(CODE_DIR, 'data', ref, 'export', f'result__{ref}_prop.csv'))
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        columns = [col for col in required_columns if col in df.columns]

        print(df.columns)
        df = df[columns]

        df["offer_final"] = df["ai_offer"]
        df["offer"] = df["ai_offer"]
        df["offer_dss"] = df["ai_offer"]
        df[[col for col in columns_to_clear]] = None

        df["job_id"] = f"REFAUTO{ref.upper()}"
        df[STATUS_KEY] = RowState.JUDGEABLE
        df[WORKER_KEY] = None
        df["updated"] = 0
        with con:
            df.to_sql(table, con, index=False)
            app.logger.debug("create_table_data: table created")

def get_row_ignore_job(con, job_id, worker_id, treatment):
    """
    Get a row and change it's state to Judging with a last modified time
    :param con: sqlite3|sqlalchemy connection
    :param job_id: job id
    :param worker_id: worker's id
    :param treatment:
    """
    app.logger.debug("get_row")
    table = get_table(base=BASE, job_id=job_id, schema="data", treatment=treatment)
    if not table_exists(con, table):
        app.logger.warning(f"table: {table} does not exist")
        return None

    res = None
    dep_change_time = time.time() - JUDGING_TIMEOUT_SEC
    # Let's check if the same worker is looking for a row (then give him the one he is working on back)
    free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {WORKER_KEY}==? and {LAST_MODIFIED_KEY} > ?', (RowState.JUDGING, worker_id, dep_change_time)).fetchone()
    if not free_rowid:
        # let's search for a row that remained too long in the 'judging' state
        free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {LAST_MODIFIED_KEY} < ?', (RowState.JUDGING, dep_change_time)).fetchone()
    if not free_rowid:
        # Let's check for a judgeable untouched row
        free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==?', (RowState.JUDGEABLE,)).fetchone()
        if free_rowid:
            free_rowid = free_rowid[PK_KEY]
            ## let's search for a rowid that hasn't been processed yetf
            res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid,)).fetchone())
            with con:
                update(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, free_rowid), con=con)
                return res
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid,)).fetchone())
        with con:
            update(f'UPDATE {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, free_rowid), con=con)
    else:
        app.logger.warning(f"no row available! job_id: {job_id}, worker_id: {worker_id}")
    return res

def close_row(con, job_id, row_id, treatment):
    app.logger.debug("close_row")
    table = get_table(BASE, job_id=job_id, schema="data", treatment=treatment)
    if not table_exists(con, table):
        app.logger.warning(f"table missing: <{table}>")
    else:
        with con:
            update(f'UPDATE {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=? where {PK_KEY}=? and {STATUS_KEY}=?', (time.time(), RowState.JUDGED, row_id, RowState.JUDGING), con=con)
    app.logger.debug("close_row - done")

class ResponderForm(FlaskForm):
    min_offer = IntegerField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

def handle_index(treatment, template=None, messages=None, has_dss_component=False):
    app.logger.debug("handle_index")
    if messages is None:
        messages = []
    if template is None:
        template = f"txx/resp.html"
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")

    close_row(get_db(), job_id, 2, treatment)

    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id:
        req_response = redirect(url_for(f"{treatment}.resp.done"))
        return req_response
    if request.method == "GET":
        app.logger.debug(f"handle_index: job_id:{job_id}, worker_id:{worker_id} ")
        cookie_obj['response'] = HHI_Resp_ADM()
        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["auto_finalize"] = request.args.get("auto_finalize")

        for message in messages:
            flash(message)
    if request.method == "POST":
        response = cookie_obj["response"]
        response["time_stop"] = time.time()
        response["min_offer"] = int(request.form["min_offer"])
        cookie_obj['response'] = response
        if has_dss_component:
            req_response = make_response(redirect(url_for(f"{treatment}.resp.index_dss", **request.args)))
        else:
            req_response = make_response(redirect(url_for(f"{treatment}.resp.done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, form=ResponderForm()))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def handle_index_dss(treatment, template=None, messages=None, dss_only=False):
    app.logger.debug("handle_index_dss")
    if messages is None:
        messages = []
    if template is None:
        template = f"txx/resp_dss.html"
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
        if dss_only:
            # for treatments T2x
            cookie_obj['response'] = HHI_Resp_ADM()
            cookie_obj["worker_id"] = worker_id
            cookie_obj["job_id"] = job_id

        else:
            cookie_obj["response"]["time_start_dss"] = time.time()

        for message in messages:
            flash(message)
    if request.method == "POST":
        response = cookie_obj["response"]
        if dss_only:
            response["time_stop"] = time.time()
            response["min_offer"] = int(request.form["min_offer"])
        response["time_stop_dss"] = time.time()
        response["min_offer_dss"] = int(request.form["min_offer"])
        cookie_obj['response'] = response
        req_response = make_response(redirect(url_for(f"{treatment}.resp.feedback", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, form=ResponderForm(), scalas=AI_FEEDBACK_SCALAS, accuracy_scalas=AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def handle_feedback(treatment, template=None, messages=None):
    app.logger.debug("handle_index_dss")
    cookie_obj = get_cookie_obj(BASE)
    if messages is None:
        messages = []
    if template is None:
        template = f"txx/resp_dss_feedback.html"
    if request.method == "POST":
        response = cookie_obj["response"]
        response["feedback_alternative"] = request.form["feedback_alternative"]
        response["feedback_fairness"] = request.form["feedback_fairness"]
        response["feedback_accuracy"] = request.form["feedback_accuracy"]
        cookie_obj['response'] = response
        req_response =  make_response(redirect(url_for(f"{treatment}.resp.done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, scalas=AI_FEEDBACK_SCALAS, accuracy_scalas=AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS, form=FlaskForm()))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response 

def handle_done(treatment, template=None, no_features=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"txx/resp.done.html"

    if no_features is None:
        completion_code_base = BASE
    else:
        # survey should not require tasks
        completion_code_base = BASE + "NF"
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not cookie_obj.get(worker_code_key):
        job_id = cookie_obj["job_id"]
        worker_code = generate_completion_code(completion_code_base, job_id)
        response = cookie_obj["response"]
        response["completion_code"] = worker_code
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

        auto_finalize = cookie_obj.get("auto_finalize", request.args.get("auto_finalize"))
        if auto_finalize and no_features:# and base=="hexaco":
            #NOTE: there is an import here ^_^
            finalize_resp(job_id, worker_id, treatment)

    req_response = make_response(render_template(template, worker_code=cookie_obj[worker_code_key]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def handle_done_no_prop(treatment, template=None, no_features=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"txx/resp.done.html"
    if no_features is None:
        completion_code_base = BASE
    else:
        # survey should not require tasks
        completion_code_base = BASE + "NF"

    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not cookie_obj.get(worker_code_key):
        job_id = cookie_obj["job_id"]
        worker_code = generate_completion_code(completion_code_base, job_id)
        response = cookie_obj["response"]
        response["completion_code"] = worker_code
        worker_id = cookie_obj["worker_id"]
        resp_result = resp_to_resp_result(response, job_id=job_id, worker_id=worker_id)
        try:
            #save_resp_result(TUBE_RES_FILENAME, resp_result)
            save_result2file(get_output_filename(BASE, job_id, treatment=treatment), resp_result)
        except Exception as err:
            app.log_exception(err)
        
        bonus_cents = 0
        row_id = None
        prop_row = {}
        try:
            prop_row = get_row_ignore_job(get_db(), job_id, worker_id, treatment)
            offer = prop_row.get("offer_final", prop_row["offer"])
            row_id = prop_row.get(PK_KEY)
            if offer >= response.get("min_offer_final", response["min_offer"]):
                bonus_cents = MAX_GAIN - offer
            else:
                bonus_cents = 0
        except Exception as err:
            app.log_exception(err)
        try:
            #save_resp_result2db(get_db("RESULT"), resp_result, job_id)
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=resp_result, unique_fields=["worker_id"])
            increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=bonus_cents)
            close_row(get_db(), job_id, row_id, treatment)

            prop_result = {k:v for k,v in resp_result.items() if k not in SKIP_RESP_KEYS}
            prop_result = {k: v if "feedback" not in k else v for k, v in prop_result.items()}
            prop_result["resp_worker_id"] = worker_id
            prop_result["worker_id"] = prop_row["prop_worker_id"]
            prop_result.update(prop_row)
            save_result2db(table=get_table(base="prop", job_id=job_id, schema="result", treatment=treatment), response_result=prop_result, unique_fields=["worker_id"])
        except Exception as err:
            app.log_exception(err)
        cookie_obj.clear()
        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj[worker_code_key] = worker_code

    req_response = make_response(render_template(template, worker_code=cookie_obj[worker_code_key]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

