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

#from survey.unit import HHI_Prop_ADM,  prop_to_prop_result, save_prop_result
from core.utils.explanation import get_acceptance_probability, get_best_offer_probability
from core.utils.preprocessing import df_to_xy
from core.utils import cents_repr
from core.models.metrics import gain, MAX_GAIN

from survey._app import app, csrf_protect
from survey.figure_eight import FigureEight, RowState
from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists, update
from survey.utils import (save_result2db, save_result2file, get_output_filename, get_table, predict_weak, predict_strong,
    generate_completion_code, increase_worker_bonus, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY)


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

OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, 201, 5)}

JUDGING_TIMEOUT_SEC = 10*60

if app.config["DEBUG"]:
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
        self["ai_calls_offer"] = []
        self["ai_calls_time"] = []
        self["ai_calls_response"] = []
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
    result["time_spent_prop"] = proposal["time_stop"] - proposal["time_start"]
    ai_nb_calls = len(proposal["ai_calls_offer"])
    result["ai_nb_calls"] = ai_nb_calls
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
    result["ai_call_offers"] = ":".join(str(val) for val in proposal["ai_calls_offer"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["prop_worker_id"] = worker_id
    result["resp_worker_id"] = row_data["resp_worker_id"]
    result["min_offer"] = row_data["min_offer"]
    result["model_type"] = row_data["model_type"]
    discard_row_data_fields = {"job_id", "worker_id", "job_id", "min_offer", "resp_worker_id", "row_id", "status", "time_start", "time_stop", "timestamp", "updated", "worker_id"}
    for k, v in row_data.items():
        #result[f"data__{k}"] = v
        if k not in discard_row_data_fields:
            result[k] = v
    #print("RESULT_ROW: ", result)
    return result


# def save_prop_result(filename, proposal_result):
#     if "job_id" in proposal_result:
#         folder, fname = os.path.split(filename)
#         filename = os.path.join(folder, f"{proposal_result['job_id']}__{fname}")
#     file_exists = os.path.exists(filename)
#     os.makedirs(os.path.split(filename)[0], exist_ok=True)
#     with open(filename, "a") as out_f:

#         writer = csv.writer(out_f)
#         if not file_exists:
#             writer.writerow(proposal_result.keys())
#         writer.writerow(proposal_result.values())

# def generate_completion_code(job_id):
#     job_config = get_job_config(get_db("DB"), job_id)
#     base_completion_code = job_config["base_code"]
#     part1 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
#     part2 = base_completion_code
#     part3 = "-PROP"
#     return "".join([part1, part2, part3])



def get_features(job_id, resp_worker_id, treatment, tasks=None):
    """
    :returns: (numpy.array) features
    :returns: (dict) features_rows untransformed
    """
    app.logger.debug("get_features")
    MODEL_INFOS_KEY = f"{treatment.upper()}_MODEL_INFOS"
    tasks = tasks or ["cg", "crt", "eff", "hexaco", "risk"]
    con = get_db("RESULT")
    tasks_features = {
        "cg":["selfish"],
        #"crt":["*"],        #TODO: check
        "eff":["count_effort"],
        "hexaco": ["Honesty_Humility", "Extraversion", "Agreeableness"],     #TODO: check conversion
        "risk":["cells", "time_spent_risk"]
    }
    #row_features = {"Honesty_Humility":2.5, "Extraversion":2.5, "Agreeableness":2.5}
    row_features = dict()
    for name, features in tasks_features.items():
        task_table = get_table(name, job_id=job_id, schema="result", is_task=True)
        with con:
            sql = f"SELECT {','.join(features)} FROM {task_table} WHERE worker_id=?"
            res = con.execute(sql, (resp_worker_id,)).fetchone()
            row_features.update(dict(res))
    resp_features = {
        "resp": ["time_spent_prop"]
    }
    for name, features in resp_features.items():
        table = get_table(name, job_id=job_id, treatment=treatment, schema="result", is_task=False)
        with con:
            sql = f"SELECT {','.join(features)} FROM {table} WHERE worker_id=?"
            res = con.execute(sql, (resp_worker_id,)).fetchone()
            row_features.update(dict(res))
    tmp_df = pd.DataFrame(data=[row_features])
    x, _ = df_to_xy(tmp_df, select_columns=app.config[MODEL_INFOS_KEY]["top_columns"])
    app.logger.debug("get_features - done")
    return x, row_features

        


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_row(con, job_id, worker_id, treatment):
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
        return None
    free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==?', (RowState.JUDGEABLE,)).fetchone()
    res = None
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        ## let's search for a rowid that hasn't been processed yetf
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid,)).fetchone())
        with con:
            update(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, free_rowid), con=con)
            return res
    else:
        dep_change_time = time.time() - JUDGING_TIMEOUT_SEC
        # Let's check if the same worker is looking for a row (then give him the one he is working on back)
        free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {WORKER_KEY}==? and {LAST_MODIFIED_KEY} > ?', (RowState.JUDGING, worker_id, dep_change_time)).fetchone()
        if not free_rowid:
            ## let's search for a row that remained too long in the 'judging' state
            free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {LAST_MODIFIED_KEY} < ?', (RowState.JUDGING, dep_change_time)).fetchone()
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid, )).fetchone())
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

def insert_row(job_id, resp_row, treatment, overwrite=False):
    app.logger.debug("insert_row")
    MODEL_KEY = f"{treatment.upper()}_MODEL"
    MODEL_TYPES = [REAL_MODEL, WEAK_FAKE_MODEL, STRONG_FAKE_MODEL]
    model_type = "none"
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

    if app.config["FAKE_MODEL"]:
        with con:
            rowid = con.execute(f"SELECT {PK_KEY} FROM {table} where resp_worker_id=?", (resp_row[WORKER_KEY], )).fetchone()[PK_KEY]
        if rowid:
            if rowid % 3 == 0:
                model_type = MODEL_TYPES[0]
            elif rowid % 3 == 1:
                model_type = MODEL_TYPES[1]
            else:
                model_type = MODEL_TYPES[2]
    else:
        model_type = 0
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
    app.logger.debug("insert_row - done")



def save_prop_result2db(con, proposal_result, job_id, overwrite=False, treatment=None):
    table = get_table(BASE, job_id=job_id, schema="result", treatment=treatment)
    df = pd.DataFrame(data=[proposal_result])
    insert(df, table=table, con=con, overwrite=overwrite)

############################################################

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

def handle_index(treatment, template=None, proposal_class=None, messages=None):
    app.logger.debug("handle_index")
    if proposal_class is None:
        proposal_class = HHI_Prop_ADM
    if template is None:
        template = f"{treatment}/prop.html"
    if request.method == "GET":
        session['proposal'] = proposal_class()
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        app.logger.debug(f"handle_index: job_id:{job_id}, worker_id:{worker_id} ")
        row_info = get_row(get_db("DATA"), job_id, worker_id, treatment=treatment)

        session["worker_id"] = worker_id
        session["job_id"] = job_id
        session["row_info"] = row_info
        
        #TODO: check if worker_id has started answering this unit
        if not row_info:
            warnings.warn(f"ERROR: The row can no longer be processed. job_id: {job_id} - worker_id: {worker_id}")

            flash(f"There are either no more rows available or you already took part on this survey. Thank you for your participation")
            return render_template("error.html")
            if not app.config["DEBUG"]:
                if app.config.get("TESTING"):
                    return render_template("error.html")
        for message in messages:
            flash(message)
    if request.method == "POST":
        proposal = session["proposal"]
        proposal["time_stop"] = time.time()
        offer = request.form["offer"]
        try:
            offer = int(offer)
        except ValueError:
            offer = None
        proposal["offer"] = offer
        session['proposal'] = proposal
        return redirect(url_for(f"{treatment}.prop.done", **request.args))

    session[BASE] = True
    prop_check_url = url_for(f"{treatment}.prop.check")
    return render_template(template, offer_values=OFFER_VALUES, form=ProposerForm(), prop_check_url=prop_check_url)


def handle_check(treatment):
    app.logger.debug("handle_check")
    MODEL_INFOS_KEY = f"{treatment.upper()}_MODEL_INFOS"
    if not session.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    
    proposal = session["proposal"]
    offer = int(request.args.get("offer", 0))
    proposal["ai_calls_offer"].append(offer)

    proposal["ai_calls_time"].append(time.time())
    ai_offer = int(session["row_info"]["ai_offer"])
    acceptance_probability = get_acceptance_probability(offer, app.config[MODEL_INFOS_KEY]["pdf"])
    best_offer_probability = get_best_offer_probability(ai_offer=ai_offer, offer=offer, accuracy=app.config[MODEL_INFOS_KEY]["acc"], train_err_pdf=app.config[MODEL_INFOS_KEY]["train_err_pdf"])

    #TODO: use the model predictions, data distribution to generate the ai_calls_response
    proposal["ai_calls_response"].append([acceptance_probability, best_offer_probability])
    session["proposal"] = proposal
    return jsonify({"offer": offer, "acceptance_probability": acceptance_probability, "best_offer_probability": best_offer_probability})
    #return "checked %s - acceptance: %s, best_offer: %s" % (offer, acceptance_probability, best_offer_probability)


def handle_done(treatment, template=None, response_to_result_func=None):
    app.logger.debug("handle_done")
    if template is None:
        template = f"{treatment}/{BASE}.done.html"
    if response_to_result_func is None:
        response_to_result_func = prop_to_prop_result
    worker_code_key = f"{BASE}_worker_code"
    worker_bonus_key = f"{BASE}_worker_bonus"
    if not session.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not (session.get("worker_bonus") and session.get("worker_code")):
        job_id = session["job_id"]
        worker_code = generate_completion_code(base=BASE, job_id=job_id)
        proposal = session["proposal"]
        row_info = session["row_info"]
        worker_id = session["worker_id"]
        close_row(get_db("DATA"), job_id, row_info[PK_KEY], treatment=treatment)
        worker_bonus = gain(int(row_info["min_offer"]), proposal["offer"])
        prop_result = response_to_result_func(proposal, job_id=job_id, worker_id=worker_id, row_data=row_info)
        try:
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=treatment), prop_result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=prop_result, unique_fields=["worker_id"])
            increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=0, con=get_db("DB"))
        except Exception as err:
            app.log_exception(err)
        session.clear()

        session[BASE] = True
        session[worker_bonus_key] = cents_repr(worker_bonus)
        session[worker_code_key] = worker_code
    return render_template(template, worker_code=session[worker_code_key], worker_bonus=session[worker_bonus_key])

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
        res = con.execute(f"SELECT offer, min_offer, resp_worker_id from {table} WHERE prop_worker_id=?", (prop_worker_id,)).fetchone()
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
        increase_worker_bonus(job_id, resp_worker_id, resp_bonus, con2)
        increase_worker_bonus(job_id, prop_worker_id, prop_bonus, con2)
