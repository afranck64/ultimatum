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
#from survey.unit import HHI_Prop_ADM,  prop_to_prop_result, save_prop_result
from core.utils.explanation import get_acceptance_propability, get_best_offer_probability
from core.utils.preprocessing import df_to_xy
from core.utils import cents_repr
from core.models.metrics import gain

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
from survey.utils import save_result2db, save_result2file, get_output_filename, get_table, generate_completion_code, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY


############ Consts #################################
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

TUBE_RES_FILENAME = os.getenv("TUBE_RES_FILENAME", f"./data/{TREATMENT}/output/prop.csv")

SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", f"./data/{TREATMENT}/model.json")
MODEL_INFOS_FILENAME = f"./data/{TREATMENT}/model.json"

BASE_COMPLETION_CODE = os.getenv("COMPLETION_CODE", "tTkEnH5A4syJ6N4t")

REAL_MODEL = "real"
WEAK_FAKE_MODEL = "weak_fake"
STRONG_FAKE_MODEL = "strong_fake"
MODEL_INFOS_KEY = f"{TREATMENT.upper()}_MODEL_INFOS"
MODEL_KEY = f"{TREATMENT.upper()}_MODEL"
OFFER_VALUES = {str(val):cents_repr(val) for val in range(0, 201, 5)}

JUDGING_TIMEOUT_SEC = 10*60

if app.config["DEBUG"]:
    JUDGING_TIMEOUT_SEC = 10

ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

with open(MODEL_INFOS_FILENAME) as inp_f:
    MODEL_INFOS = json.load(inp_f)

bp = Blueprint(f"{TREATMENT}.{BASE}", __name__)
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
    result["ai_calls_between_times"] = ":".join(str(int(value)) for value in ai_times)
    result["ai_call_offers"] = ":".join(str(val) for val in proposal["ai_calls_offer"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["prop_worker_id"] = worker_id
    result["resp_worker_id"] = row_data["resp_worker_id"]
    for k, v in row_data.items():
        result[f"data__{k}"] = v
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
    tasks = tasks or ["cg", "crt", "eff", "hexaco", "risk"]
    con = get_db("RESULT")
    tasks_features = {
        "cg":["selfish"],
        #"crt":["*"],        #TODO: check
        "eff":["count_effort"],
        #"hexaco": ["Honesty_Humility", "Extraversion", "Agreeableness"],     #TODO: check conversion
        "risk":["cells", "time_spent_risk"]
    }
    row_features = {"Honesty_Humility":2.5, "Extraversion":2.5, "Agreeableness":2.5}
    row_features.update({})
    for name, features in tasks_features.items():
        task_table = get_table(name, job_id)
        with con:
            sql = f"SELECT {','.join(features)} FROM {task_table} WHERE worker_id=?"
            res = con.execute(sql, (resp_worker_id,)).fetchone()
            row_features.update(dict(res))
    row_features2 = dict(row_features)
    row_features2["cells"] = 32.0
    row_features2["selfish"] = 25.0
    tmp_df = pd.DataFrame(data=[row_features])
    x, _ = df_to_xy(tmp_df, select_columns=MODEL_INFOS["top_columns"])
    return x

        


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_row(con, job_id, worker_id):
    """
    Get a row and change it's state to Judging with a last modified time
    :param con: sqlite3|sqlalchemy connection
    :param job_id: job id
    :param worker_id: worker's id
    """
    table = get_table(base=BASE, job_id=job_id, treatment=TREATMENT)
    if not table_exists(con, table):
        return None
    free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==?', (RowState.JUDGEABLE,)).fetchone()
    res = None
    if free_rowid:
        free_rowid = free_rowid[PK_KEY]
        ## let's search for a rowid that hasn't been processed yetf
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid,)).fetchone())
        with con:
            con.execute(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, free_rowid))
        return res

    else:
        dep_change_time = time.time() - JUDGING_TIMEOUT_SEC
        # Let's check if the same worker is looking for a row (then give him the one he is working on back)
        free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {WORKER_KEY}==? and {LAST_MODIFIED_KEY} > ?', (RowState.JUDGING, worker_id, dep_change_time)).fetchone()
        if not free_rowid:
            ## let's search for a row that remained too long in the 'judging' state
            free_rowid = con.execute(f'select {PK_KEY} from {table} where {STATUS_KEY}==? and {LAST_MODIFIED_KEY} < ?', (RowState.JUDGING, dep_change_time)).fetchone()
    if free_rowid:
        print("FREE_ROWID: ", dict(free_rowid))
        free_rowid = free_rowid[PK_KEY]
        res = dict(con.execute(f'select {PK_KEY}, * from {table} where {PK_KEY}=?', (free_rowid, )).fetchone())
        with con:
            con.execute(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=?, {WORKER_KEY}=? where {PK_KEY}=?', (time.time(), RowState.JUDGING, worker_id, free_rowid))
    return res

def close_row(con, job_id, row_id):
    
    table = get_table(BASE, job_id, treatment=TREATMENT)
    if not table_exists(con, table):
        return
    with con:
        con.execute(f'update {table} set {LAST_MODIFIED_KEY}=?, {STATUS_KEY}=? where {PK_KEY}=? and {STATUS_KEY}=?', (time.time(), RowState.JUDGED, row_id, RowState.JUDGING))

def insert_row(job_id, resp_row, overwrite=False):
    MODEL_TYPES = [REAL_MODEL, WEAK_FAKE_MODEL, STRONG_FAKE_MODEL]
    model_type = "none"
    ai_offer = 0
    df = pd.DataFrame(data=[resp_row])
    df[STATUS_KEY] = RowState.JUDGEABLE
    df[LAST_MODIFIED_KEY] = time.time()
    df[WORKER_KEY] = None
    df["resp_worker_id"] = resp_row[WORKER_KEY]
    df["ai_offer"] = ai_offer
    df["model_type"] = model_type

    table = get_table(BASE, job_id, treatment=TREATMENT)
    con = get_db("DATA")
    insert(df, table, con=con, overwrite=overwrite, unique_fields=["resp_worker_id"])

    if app.config["FAKE_MODEL"]:
        with con:
            rowid = con.execute(f"SELECT {PK_KEY} FROM {table} where resp_worker_id=?", (resp_row[WORKER_KEY], )).fetchone()[PK_KEY]
        if rowid:
            if rowid % 4 < 2:
                model_type = MODEL_TYPES[0]
            elif rowid % 4 == 2:
                model_type = MODEL_TYPES[1]
            else:
                model_type = MODEL_TYPES[2]
    else:
        model_type = 0
    if model_type == WEAK_FAKE_MODEL:
            ai_offer = max(resp_row["min_offer"]-10, 0)
    elif model_type == STRONG_FAKE_MODEL:
            ai_offer = min(resp_row["min_offer"]+10, 200)
    else:
        features = get_features(job_id, resp_worker_id=resp_row[WORKER_KEY], treatment=TREATMENT)
        # Models predict a vector
        ai_offer = app.config[MODEL_KEY].predict(features)[0]
    with con:
        sql = f"UPDATE {table} SET ai_offer=?, model_type=? where rowid=?"
        con.execute(sql, (ai_offer, model_type, rowid))

        



def save_prop_result2db(con, proposal_result, job_id, overwrite=False):
    table = get_table(BASE, job_id, treatment=TREATMENT)
    df = pd.DataFrame(data=[proposal_result])
    insert(df, table=table, con=con, overwrite=overwrite)

def get_worker_bonus(con, job_id, worker_id):
    table = get_table(BASE, job_id, treatment=TREATMENT)
    if table_exists(con, table):
        row = con.execute(f"SELECT * from {table} WHERE worker_id=?", (worker_id,)).fetchone()
        if row:
            print("ROW: ", row)
            return gain(row["data__min_offer"], row["offer"])
    return 0

def pay_worker_bonus(con, job_id, worker_id, bonus_cents, fig8, base=None, overwrite=False):
    """
    :param con:
    :param job_id:
    :param worker_id:
    :param bonus_cents:
    :param fig8:
    :param overwite:
    :returns True if payment was done, False otherwise
    """
    df = pd.DataFrame(data=[{'job_id':job_id, 'worker_id': worker_id, 'timestamp': str(datetime.datetime.now()), 'bonus_cents': bonus_cents}])
    table = get_table(BASE, job_id, category="payment", treatment=TREATMENT)

    should_pay = False
    if table_exists(con, table):
        with con:
            row = con.execute(f'select worker_id from {table} WHERE job_id==? and worker_id==? and base==?', (job_id, worker_id, base)).fetchone()
            if not row:
                #The user wasn't paid yet
                should_pay = True
    else:
        should_pay = True
    
    if should_pay:
        fig8.contributor_pay(worker_id, bonus_cents)
        insert(df, table=table, con=con, overwrite=overwrite)
        fig8.contributor_notify(worker_id, f"Thank you for your participation. You just received your bonus of {cents_repr(bonus_cents)} ^_^")
        return True
    else:
        #fig8.contributor_notify(worker_id, f"Thank you for your participation. You seems to have already been paid. ^_^")
        pass
############################################################

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        session['proposal'] = HHI_Prop_ADM()
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        row_info = get_row(get_db("DATA"), job_id, worker_id)

        print("ROW_INFO: ", row_info)
        session["worker_id"] = worker_id
        session["job_id"] = job_id
        session["row_info"] = row_info
        
        #TODO: check if worker_id has started answering this unit
        if not row_info:
            warnings.warn(f"ERROR: The row can no longer be processed. job_id: {job_id} - worker_id: {worker_id}")

            flash(f"There are either no more rows available or you already took part on this survey. Thank you for your participation")
            if not app.config["DEBUG"]:
                return render_template("error.html")
    if request.method == "POST":
        proposal = session["proposal"]
        proposal["time_stop"] = time.time()
        offer = request.form["offer"]
        try:
            offer = int(offer)
        except ValueError:
            offer = None
        proposal["offer"] = offer
        ##TODO return redirect
        session['proposal'] = proposal
        return redirect(url_for(f"{TREATMENT}.prop.done"))

    session[BASE] = True
    prop_check_url = url_for(f"{TREATMENT}.prop.check")
    return render_template(f"{TREATMENT}/prop.html", offer_values=OFFER_VALUES, form=ProposerForm(), prop_check_url=prop_check_url)


@bp.route("/prop/check/")
def check():
    if not session.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    
    proposal = session["proposal"]
    offer = int(request.args.get("offer", 0))
    proposal["ai_calls_offer"].append(offer)

    proposal["ai_calls_time"].append(time.time())
    ai_offer = int(session["row_info"]["ai_offer"])
    acceptance_probability = get_acceptance_propability(offer, app.config[MODEL_INFOS_KEY]["pdf"])
    best_offer_probability = get_best_offer_probability(ai_offer=ai_offer, offer=offer, accuracy=MODEL_INFOS["acc"], train_err_pdf=app.config[MODEL_INFOS_KEY]["train_err_pdf"])

    #TODO: use the model predictions, data distribution to generate the ai_calls_response
    proposal["ai_calls_response"].append([acceptance_probability, best_offer_probability])
    session["proposal"] = proposal
    print("proposal: ", proposal)
    return jsonify({"offer": offer, "acceptance_probability": acceptance_probability, "best_offer_probability": best_offer_probability})
    #return "checked %s - acceptance: %s, best_offer: %s" % (offer, acceptance_probability, best_offer_probability)


@bp.route("/prop/done")
def done():
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
        print("ROW_INFO: ", row_info)
        worker_id = session["worker_id"]
        close_row(get_db("DATA"), job_id, row_info[PK_KEY])
        worker_bonus = gain(int(row_info["min_offer"]), proposal["offer"])
        prop_result = prop_to_prop_result(proposal, job_id=job_id, worker_id=worker_id, row_data=row_info)
        try:
            #save_prop_result(TUBE_RES_FILENAME, prop_result)
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=TREATMENT), prop_result)
        except Exception as err:
            app.log_exception(err)
        try:
            #save_prop_result2db(get_db("RESULT"), prop_result, job_id)
            save_result2db(table=get_table(base=BASE, job_id=job_id, treatment=TREATMENT), response_result=prop_result, unique_fields=["worker_id"])
        except Exception as err:
            app.log_exception(err)
        session.clear()

        session[BASE] = True
        session[worker_bonus_key] = cents_repr(worker_bonus)
        session[worker_code_key] = worker_code
    return render_template(f"{TREATMENT}/{BASE}.done.html", worker_code=session[worker_code_key], worker_bonus=session[worker_bonus_key])


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
                    worker_id = worker_id = worker_judgment["worker_id"]
                    worker_bonus = get_worker_bonus(con, job_id, worker_id)
                    pay_worker_bonus(con, job_id, worker_id, worker_bonus, fig8)
            except Exception as err:
                app.logger.error(f"Error: {err}")
        elif signal == "unit_complete":
            #TODO: may process the whole unit here
            pass
        app.logger.info("Started part-payments..., with signal: %s ^_^ " % signal)

@csrf_protect.exempt
@bp.route("/prop/webhook", methods=["GET", "POST"])
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

@csrf_protect.exempt
@bp.route("/prop/upload", methods=["GET", "POST"])
def upload():
    if request.method == 'POST':
        print("rrequest.data:", request.form)
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        up_file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if up_file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        job_id = request.form['job_id']
        if not job_id:
            flash('No job id')
            return redirect(request.url)
        secret = request.form.get('secret')
        if secret != app.config['ADMIN_SECRET']:
            flash('Incorrect secret, please try again!!!')
            return redirect(request.url)
        if up_file and allowed_file(up_file.filename):
            filename = secure_filename(up_file.filename)
            overwrite = bool(request.form.get('overwrite'))
            df = pd.read_csv(io.BytesIO(up_file.read()))
            df[STATUS_KEY] = RowState.JUDGEABLE
            df[LAST_MODIFIED_KEY] = time.time()
            df[WORKER_KEY] = None
            table = get_table(BASE, job_id, treatment=TREATMENT)
            # TODO should use g instead
            con = get_db("DATA")
            insert(df, table, con=con, overwrite=overwrite)
            return redirect(url_for('prop.upload',
                                    filename=filename))
    return render_template('upload.html')
