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

import numpy as np
import pandas as pd

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response, make_response
)
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
from survey.utils import (save_result2db, save_result2file, get_output_filename, get_table, predict_weak, predict_strong,
    generate_completion_code, increase_worker_bonus, get_cookie_obj, set_cookie_obj, get_secret_key_hash,
    LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY)
from survey.globals import AI_FEEDBACK_SCALAS, AI_FEEDBACK_ACCURACY_PROPOSER_SCALAS
#from survey.tasks import MAX_BONUS as TASKS_FEATURES


############ Consts #################################
# TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

# TUBE_RES_FILENAME = os.getenv("TUBE_RES_FILENAME", f"./data/{TREATMENT}/output/prop.csv")

# SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", f"./data/{TREATMENT}/model.json")
# MODEL_INFOS_FILENAME = f"./data/{TREATMENT}/model.json"

# BASE_COMPLETION_CODE = os.getenv("COMPLETION_CODE", "tTkEnH5A4syJ6N4t")

REAL_MODEL = "real"
WEAK_FAKE_MODEL = "weak_fake"
STRONG_FAKE_MODEL = "strong_fake"
AI_COOKIE_KEY = f"{BASE}_ai"
OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, MAX_GAIN+1, 5)}

JUDGING_TIMEOUT_SEC = 10*60

if app.config.get("TESTING"):
    JUDGING_TIMEOUT_SEC = 10

ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

######################################################



############# HELPERS   ###########################

class HHI_Prop_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["offer"] = None
        self["time_start"] = time.time()
        self["time_stop"] = None
        self["ai_calls_count_repeated"] = 0
        self["ai_calls_offer"] = []
        self["ai_calls_time"] = []
        self["ai_calls_response"] = []
        self["ai_calls_acceptance_probability"] = []
        self["ai_calls_best_offer_probability"] = []
        self.__dict__ = self


def prop_to_prop_result(proposal, job_id=None, worker_id=None, row_data=None):
    """
    :returns: {
        timestamp: server time when genererting the result
        offer: final proposer offer
        time_spent: whole time spent for the proposal
        ai_nb_calls: number of calls of the ADM system
        ai_call_min_offer: min offer checked on the ADM
        ai_call_max_offer: max offer checked on the ADM
        ai_mean_time: mean time between consecutive calls on to the ADM
        ai_call_offers: ":" separated values
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        data__*: base unit data
    }
    """
    if row_data is None:
        row_data = {}
    result = {}
    result["timestamp"] = str(datetime.datetime.now())
    result["offer"] = proposal["offer"]
    result["offer_dss"] = proposal.get("offer_dss") #Disabled/None for T00
    result["offer_final"] = proposal.get("offer_dss", proposal["offer"])
    result["prop_time_spent"] = round(proposal["time_stop"] - proposal["time_start"])
    ai_nb_calls = len(proposal["ai_calls_offer"])
    result["ai_nb_calls"] = ai_nb_calls
    result["ai_calls_count_repeated"] = proposal["ai_calls_count_repeated"]
    result["completion_code"] = proposal["completion_code"]

    ## Feedback
    result["feedback_understanding"] = proposal.get("feedback_understanding")
    result["feedback_alternative"] = proposal.get("feedback_alternative")
    result["feedback_explanation"] = proposal.get("feedback_explanation")
    result["feedback_accuracy"] = proposal.get("feedback_accuracy")


    # if ai_nb_calls > 0:
    #     result["ai_call_min_offer"] = min(proposal["ai_calls_offer"])
    #     result["ai_call_max_offer"] = max(proposal["ai_calls_offer"])
    # else:
    #     result["ai_call_min_offer"] = None
    #     result["ai_call_max_offer"] = None
    ai_times = []
    #    pass
    if ai_nb_calls == 1:
        ai_times = [proposal["ai_calls_time"][0] - proposal["time_start"]]
        pass
    elif ai_nb_calls >= 2:
        ai_times = []
        ai_times.append(proposal["ai_calls_time"][0] - proposal["time_start"])
        for idx in range(1, ai_nb_calls):
            ai_times.append(proposal["ai_calls_time"][idx] - proposal["ai_calls_time"][idx-1])
        #result["ai_mean_time"] = sum(ai_times) / ai_nb_calls
    result["ai_calls_pauses"] = ":".join(str(int(value)) for value in ai_times)
    result["ai_calls_offers"] = ":".join(str(val) for val in proposal["ai_calls_offer"])
    result["ai_calls_acceptance_probability"] = ":".join(str(val) for val in proposal["ai_calls_acceptance_probability"])
    result["ai_calls_best_offer_probability"] = ":".join(str(val) for val in proposal["ai_calls_best_offer_probability"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["prop_worker_id"] = worker_id
    result["resp_worker_id"] = row_data["resp_worker_id"]
    result["min_offer"] = row_data["min_offer"]
    result["model_type"] = row_data["model_type"]
    result["resp_rowid"] = row_data["rowid"]
    discard_row_data_fields = {"job_id", "worker_id", "job_id", "min_offer", "resp_worker_id", PK_KEY, "status", "time_start", "time_stop", "timestamp", "updated", "worker_id"}
    for k, v in row_data.items():
        #result[f"data__{k}"] = v
        if k not in discard_row_data_fields:
            result[k] = v
    return result

def create_prop_data_table(treatment, ref):
    app.logger.debug(f"create_table_data - {ref}, {treatment}")
    con = get_db()
    table_data = get_table(BASE, None, "data", treatment=treatment)
    table_resp = get_table("resp", None, "result", treatment=treatment)
    assert len(ref)==4, "expected references of the form <txyz>"
    job_id = f"REF{ref.upper()}"
    if not table_exists(con, table_data):
        df_resp = None
        try:
            # normaly, we expect an exported data-table to be available with all required features
            df = pd.read_csv(os.path.join(CODE_DIR, 'data', ref, 'export', f'data__{ref}_prop.csv'))

            df[STATUS_KEY] = RowState.JUDGEABLE
            df[WORKER_KEY] = None
            df["updated"] = 0
            df["job_id"] = f"REF{ref.upper()}"
            with con:
                df.to_sql(table_data, con, index=False)
                app.logger.debug("create_table_data: table created")
            
            df_resp = pd.read_csv(os.path.join(CODE_DIR, 'data', ref, 'export', f'result__{ref}_resp.csv'))
            df["job_id"] = f"REF{ref.upper()}"
        except Exception as err:
            app.logger.warn(f"silenced-error: {err}")
            # otherwise, we work with the resp. table, which means the model does/should not expect any features.
            df = pd.read_csv(os.path.join(CODE_DIR, 'data', ref, 'export', f'result__{ref}_resp.csv'))
            df["job_id"] = f"REF{ref.upper()}"


            for idx in range(len(df)):
                resp_row = df.iloc[idx]
                resp_row = dict(**resp_row)
                insert_row(job_id, resp_row, treatment)
            app.logger.debug("create_table_data: table created")

            df_resp = df
        df_resp.to_sql(table_resp, con, index=False, if_exists='replace')
        app.logger.debug("resp-table-cloned: table created")
        
            


def get_features(job_id, resp_worker_id, treatment, tasks=None, tasks_features=None):
    """
    :returns: (numpy.array) features
    :returns: (dict) features_rows untransformed
    """
    app.logger.debug("get_features")
    MODEL_INFOS_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL_INFOS"
    if tasks is None:
        tasks = app.config["TASKS"]
    con = get_db("RESULT")

    if tasks_features is None:
        tasks_features = app.config["TASKS_FEATURES"]

    row_features = dict()
    for task_name, features in tasks_features.items():
        if task_name in tasks:
            task_table = get_table(task_name, job_id=job_id, schema="result", is_task=True)
            if table_exists(con, task_table):
                with con:
                    sql = f"SELECT {','.join(features)} FROM {task_table} WHERE worker_id=?"
                    res = con.execute(sql, (resp_worker_id,)).fetchone()
                    # task tables are shared. when using a REF, there the table may exists but without valid rows
                    if res is not None:
                        row_features.update(dict(res))
    resp_features = {
        "resp": ["resp_time_spent"]
    }
    for name, features in resp_features.items():
        table = get_table(name, job_id=job_id, treatment=treatment, schema="result", is_task=False)

        if table_exists(con, table):
            with con:
                sql = f"SELECT {','.join(features)} FROM {table} WHERE worker_id=?"
                res = con.execute(sql, (resp_worker_id,)).fetchone()
                # task tables are shared. when using a REF, there the table may exists but without valid rows
                if res is not None:
                    row_features.update(dict(res))
    tmp_df = pd.DataFrame(data=[row_features])
    
    
    REF_MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    dss_available = bool(app.config.get(REF_MODEL_KEY))
    if dss_available:
        x, _ = df_to_xy(tmp_df, select_columns=app.config[MODEL_INFOS_KEY]["top_columns"])
    else:
        x = None
    app.logger.debug("get_features - done")
    return x, row_features



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



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


def get_row(con, job_id, worker_id, treatment, ignore_job=False):
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
    free_rowid = con.execute(f'select {PK_KEY} from {table} where job_id=? and {STATUS_KEY}==?', (job_id, RowState.JUDGEABLE,)).fetchone()
    res = None
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        ## let's search for a rowid that hasn't been processed yetf
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where job_id=? and {PK_KEY}=?', (job_id, free_rowid,)).fetchone())
        with con:
            update(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where job_id=? and {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, job_id, free_rowid), con=con)
            return res
    else:
        dep_change_time = time.time() - JUDGING_TIMEOUT_SEC
        # Let's check if the same worker is looking for a row (then give him the one he is working on back)
        free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {WORKER_KEY}==? and {LAST_MODIFIED_KEY} > ? and job_id=?', (RowState.JUDGING, worker_id, dep_change_time, job_id)).fetchone()
        if not free_rowid:
            ## let's search for a row that remained too long in the 'judging' state
            free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {LAST_MODIFIED_KEY} < ? and job_id=?', (RowState.JUDGING, dep_change_time, job_id)).fetchone()
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=? and job_id=?', (free_rowid, job_id)).fetchone())
        with con:
            update(f'UPDATE {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=? and job_id=?', (time.time(), RowState.JUDGING, worker_id, free_rowid, job_id), con=con)
    else:
        app.logger.warning(f"no row available! job_id: {job_id}, worker_id: {worker_id}")
    return res

def close_row(con, job_id, row_id, treatment, ignore_job=None):
    app.logger.debug("close_row")
    table = get_table(BASE, job_id=job_id, schema="data", treatment=treatment)
    if not table_exists(con, table):
        app.logger.warning(f"table missing: <{table}>")
    else:
        with con:
            if ignore_job:
                update(f'UPDATE {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=? where {PK_KEY}=? and {STATUS_KEY}=?', (time.time(), RowState.JUDGED, row_id, RowState.JUDGING), con=con)
            else:
                update(f'UPDATE {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=? where {PK_KEY}=? and {STATUS_KEY}=? and job_id=?', (time.time(), RowState.JUDGED, row_id, RowState.JUDGING, job_id), con=con)
    app.logger.debug("close_row - done")


def close_row_ignore_job(con, job_id, row_id, treatment):
    return close_row(con, job_id, row_id, treatment, ignore_job=True)

def process_insert_row(job_id, resp_row, treatment, overwrite=False):
    """
    Insert a new row for the proposer assuming no model is available
    """
    app.logger.debug("process_insert_row")
    resp_row = dict(resp_row)
    _, features_dict = get_features(job_id, resp_worker_id=resp_row[WORKER_KEY], treatment=treatment)
    resp_row = dict(resp_row)
    resp_row.update(features_dict)
    df = pd.DataFrame(data=[resp_row])
    df[STATUS_KEY] = RowState.JUDGEABLE
    df[LAST_MODIFIED_KEY] = time.time()
    df[WORKER_KEY] = None
    df["resp_worker_id"] = resp_row[WORKER_KEY]

    table = get_table(BASE, job_id=job_id, schema="data", treatment=treatment)
    con = get_db("DATA")
    insert(df, table, con=con, overwrite=overwrite, unique_fields=["resp_worker_id"])

    app.logger.debug("process_insert_row - done")

def process_insert_row_dss(job_id, resp_row, treatment, overwrite=False):
    """
    Insert a new row for the proposer with the ai predicted min_offer
    """
    app.logger.debug("process_insert_row_dss")
    ENABLED_FAKE_MODEL_KEY = f"{treatment.upper()}_FAKE_MODEL"
    MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    FAKE_MODEL_TYPES = [WEAK_FAKE_MODEL, STRONG_FAKE_MODEL]
    model_type = None
    ai_offer = 0
    features, features_dict = get_features(job_id, resp_worker_id=resp_row[WORKER_KEY], treatment=treatment)
    resp_row = dict(resp_row)
    resp_row.update(features_dict)
    df = pd.DataFrame(data=[resp_row])
    df[STATUS_KEY] = RowState.JUDGEABLE
    df[LAST_MODIFIED_KEY] = time.time()
    df[WORKER_KEY] = None
    df["resp_worker_id"] = resp_row[WORKER_KEY]
    df["ai_offer"] = ai_offer
    df["model_type"] = model_type


    table = get_table(BASE, job_id=job_id, schema="data", treatment=treatment)
    con = get_db("DATA")
    insert(df, table, con=con, overwrite=overwrite, unique_fields=["resp_worker_id"])

    with con:
        rowid = con.execute(f"SELECT {PK_KEY} FROM {table} where resp_worker_id=?", (resp_row[WORKER_KEY], )).fetchone()[PK_KEY]

    # if true, fake models should be used for this treatment
    if app.config[ENABLED_FAKE_MODEL_KEY]:
        if rowid is not None:
            model_type = FAKE_MODEL_TYPES[rowid % len(FAKE_MODEL_TYPES)]
        else:
            model_type = REAL_MODEL
    else:
        model_type = REAL_MODEL
    if model_type == WEAK_FAKE_MODEL:
            ai_offer = predict_weak(resp_row["min_offer"])
    elif model_type == STRONG_FAKE_MODEL:
            ai_offer = predict_strong(resp_row["min_offer"])
    else:
        # Models predict a vector
        ai_offer = app.config[MODEL_KEY].predict(features)[0]
    ai_offer = int(ai_offer)
    with con:
        update(sql=f"UPDATE {table} SET ai_offer=?, model_type=? where rowid=?", args=(ai_offer, model_type, rowid), con=con)
    app.logger.debug("process_insert_row_dss - done MODEL_TYPE: " + str(rowid % len(FAKE_MODEL_TYPES)) + "  " + str(rowid))


def insert_row(job_id, resp_row, treatment, overwrite=False):
    MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    dss_available = bool(app.config.get(MODEL_KEY))
    discarded_items = {
        "completion_code", "feedback_accuracy", "feedback_understanding", "feedback_explanation",
        "time_start", "time_start_dss", "time_stop", "time_stop_dss", "timestamp", "feedback_fairness", "feedback_alternative"}
    resp_row = {k:v for k,v in resp_row.items() if k not in discarded_items}
    if dss_available:
        process_insert_row_dss(job_id, resp_row, treatment, overwrite)
    else:
        process_insert_row(job_id, resp_row, treatment, overwrite)


def save_prop_result2db(con, proposal_result, job_id, overwrite=False, treatment=None):
    table = get_table(BASE, job_id=job_id, schema="result", treatment=treatment)
    df = pd.DataFrame(data=[proposal_result])
    insert(df, table=table, con=con, overwrite=overwrite)

############################################################

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

def handle_index(treatment, template=None, proposal_class=None, messages=None, dss_available=None, get_row_func=None):
    app.logger.debug("handle_index")
    if messages is None:
        messages = []
    if proposal_class is None:
        proposal_class = HHI_Prop_ADM
    if dss_available is None:
        MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
        dss_available = bool(app.config.get(MODEL_KEY))
    if template is None:
        template = f"txx/prop.html"
    if get_row_func is None:
        get_row_func = get_row
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id :
        req_response =  make_response(redirect(url_for(f"{treatment}.prop.done", **request.args)))
        return req_response

    if request.method == "GET":
        cookie_obj['proposal'] = proposal_class()
        app.logger.debug(f"handle_index: job_id:{job_id}, worker_id:{worker_id} ")
        row_info = get_row_func(get_db("DATA"), job_id, worker_id, treatment=treatment)

        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["row_info"] = row_info
        
        #TODO: check if worker_id has started answering this unit
        if not row_info:
            warnings.warn(f"ERROR: The row can no longer be processed. job_id: {job_id} - worker_id: {worker_id}")

            flash(f"There are either no more rows available or you already took part on this survey. Thank you for your participation")
            return render_template("error.html")
        for message in messages:
            flash(message)
    if request.method == "POST":
        proposal = cookie_obj["proposal"]
        proposal["time_stop"] = time.time()
        offer = request.form["offer"]
        try:
            offer = int(offer)
        except ValueError as err:
            app.logger.warning(f"Conversion error: {err}")
            offer = None
        proposal["offer"] = offer
        cookie_obj['proposal'] = proposal
        if dss_available:
            req_response =  make_response(redirect(url_for(f"{treatment}.prop.index_dss", **request.args)))
        else:
            req_response =  make_response(redirect(url_for(f"{treatment}.prop.done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    prop_check_url = url_for(f"{treatment}.prop.check")
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, form=ProposerForm(), prop_check_url=prop_check_url, max_gain=MAX_GAIN))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response


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
        #TODO: check if worker_id has started answering this unit
        proposal = cookie_obj["proposal"]
        proposal["time_start_dss"] = time.time()
        if not row_info:
            warnings.warn(f"ERROR: The row can no longer be processed. job_id: {job_id} - worker_id: {worker_id}")

            flash(f"There are either no more rows available or you already took part on this survey. Thank you for your participation")
            return render_template("error.html")
        for message in messages:
            flash(message)
    if request.method == "POST":
        proposal = cookie_obj["proposal"]
        proposal["time_stop_dss"] = time.time()
        offer_dss = request.form["offer_dss"]
        try:
            offer_dss = int(offer_dss)
        except ValueError as err:
            app.logger.warning(f"Conversion error: {err}")
            offer_dss = None
        proposal["offer_dss"] = offer_dss
        cookie_obj['proposal'] = proposal
        req_response =  make_response(redirect(url_for(f"{treatment}.prop.feedback", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response

    cookie_obj[BASE] = True
    prop_check_url = url_for(f"{treatment}.prop.check")
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, form=ProposerForm(), prop_check_url=prop_check_url, max_gain=MAX_GAIN))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def handle_check(treatment):
    app.logger.debug("handle_check")
    MODEL_INFOS_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL_INFOS"
    cookie_obj = get_cookie_obj(BASE)
    if not cookie_obj.get(BASE):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    ai_cookie_obj = get_cookie_obj(AI_COOKIE_KEY)
    if not ai_cookie_obj.get(BASE):
        # Use another cookie to reduce chances of growing over the cookie limit
        ai_cookie_obj[BASE] = True
        ai_proposal = {"ai_calls_best_offer_probability":[], "ai_calls_acceptance_probability":[], "ai_calls_offer":[], "ai_calls_time":[] , "ai_calls_count_repeated":0}
        ai_cookie_obj["row_info"] = {"ai_offer": cookie_obj["row_info"]["ai_offer"]}
        ai_cookie_obj["ai_proposal"] = ai_proposal
    ai_proposal = ai_cookie_obj["ai_proposal"]
    offer = int(request.args.get("offer", 0))
    ai_offer = int(ai_cookie_obj["row_info"]["ai_offer"])
    model_infos = app.config[MODEL_INFOS_KEY]
    acceptance_probability = get_acceptance_probability(ai_offer=ai_offer, offer=offer, accuracy=model_infos["acc"], train_err_pdf=model_infos["train_err_pdf"], train_pdf=model_infos["pdf"])
    best_offer_probability = get_best_offer_probability(ai_offer=ai_offer, offer=offer, accuracy=model_infos["acc"], train_err_pdf=model_infos["train_err_pdf"])

    ai_proposal["ai_calls_count_repeated"] += 1
    if offer not in ai_proposal["ai_calls_offer"]:
        ai_proposal["ai_calls_offer"].append(offer)
        ai_proposal["ai_calls_time"].append(time.time())
        ai_proposal["ai_calls_best_offer_probability"].append(round(best_offer_probability, 4))
        ai_proposal["ai_calls_acceptance_probability"].append(round(acceptance_probability, 4))
    ai_cookie_obj["ai_proposal"] = ai_proposal
    
    resp_data = {"offer": offer, "acceptance_probability": acceptance_probability, "best_offer_probability": best_offer_probability}
    if request.args.get("secret_key_hash") == get_secret_key_hash():
        resp_data["ai_offer"] = ai_offer
    req_response = make_response(jsonify(resp_data))
    set_cookie_obj(req_response, AI_COOKIE_KEY, ai_cookie_obj)
    return req_response

def handle_feedback(treatment, template=None, messages=None, alternative_affirmation=None):
    app.logger.debug("handle_index_dss")
    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    if messages is None:
        messages = []
    if template is None:
        template = f"txx/prop_dss_feedback.html"
    if request.method == "POST":
        proposal = cookie_obj["proposal"]
        # for some treatment there is no alternative feedback
        proposal["feedback_alternative"] = request.form.get("feedback_alternative")
        proposal["feedback_understanding"] = request.form["feedback_understanding"]
        proposal["feedback_explanation"] = request.form["feedback_explanation"]
        proposal["feedback_accuracy"] = request.form["feedback_accuracy"]
        req_response =  make_response(redirect(url_for(f"{treatment}.prop.done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response
    req_response = make_response(render_template(template, offer_values=OFFER_VALUES, scalas=AI_FEEDBACK_SCALAS, accuracy_scalas=AI_FEEDBACK_ACCURACY_PROPOSER_SCALAS, alternative_affirmation=alternative_affirmation))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response 

def handle_done(treatment, template=None, response_to_result_func=None, ignore_job=None):
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
        close_row(get_db("DATA"), job_id, row_info[PK_KEY], treatment=treatment, ignore_job=ignore_job)
        # worker_bonus = gain(int(row_info["min_offer"]), proposal["offer"])
        prop_result = response_to_result_func(proposal, job_id=job_id, worker_id=worker_id, row_data=row_info)
        try:
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=treatment), prop_result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=prop_result, unique_fields=["worker_id"])
            # increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=0, con=get_db("DB"))
        except Exception as err:
            app.log_exception(err)
        auto_finalize = request.args.get("auto_finalize")
        if auto_finalize:
            # url = url_for(f"{treatment}.webhook", job_id=job_id, worker_id=worker_id, auto_finalize=auto_finalize)
            # client = app.test_client()
            # client.get(url)
            finalize_round(job_id, prop_worker_id=worker_id, treatment=treatment)

        cookie_obj.clear()

        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        # cookie_obj[worker_bonus_key] = cents_repr(worker_bonus)
        cookie_obj[worker_code_key] = worker_code
    req_response = make_response(render_template(template, worker_code=cookie_obj[worker_code_key]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

def is_fake_worker(worker_id):
    return worker_id is None or "#" in worker_id

def finalize_round(job_id, prop_worker_id, treatment):
    app.logger.debug("finalize_round")
    # TODO: At this point, all features have been gathered
    resp_worker_id = "na"
    con = get_db("RESULT")
    resp_bonus = 0
    prop_bonus = 0
    offer, min_offer = 0, 0
    with con:
        table = get_table(BASE, job_id, schema="result", treatment=treatment)
        try:
            # min_offer_final was introduce late, so it may be missing on some tables...
            # in case of absence, a fallback to min_offer is perfectly fine.
            res = con.execute(f"SELECT offer_final as offer, min_offer_final as min_offer, resp_worker_id from {table} WHERE prop_worker_id=?", (prop_worker_id,)).fetchone()
        except Exception as err:
            app.logger.warn(f"{err}")
            res = con.execute(f"SELECT offer_final as offer, min_offer, resp_worker_id from {table} WHERE prop_worker_id=?", (prop_worker_id,)).fetchone()
    offer, min_offer = res["offer"], res["min_offer"]
    resp_worker_id = res["resp_worker_id"]
    offer = max(min(offer, MAX_GAIN), 0)
    min_offer = max(min(min_offer, MAX_GAIN), 0)

    if offer >= min_offer:
        resp_bonus += offer
        prop_bonus += (MAX_GAIN - offer)
    assert (resp_bonus+prop_bonus)==0 or (resp_bonus + prop_bonus)== MAX_GAIN
    con2 = get_db("DB")
    with con2:
        if not is_fake_worker(resp_worker_id):
            increase_worker_bonus(job_id, resp_worker_id, resp_bonus, con2)
        if not is_fake_worker(prop_worker_id):
            increase_worker_bonus(job_id, prop_worker_id, prop_bonus, con2)
