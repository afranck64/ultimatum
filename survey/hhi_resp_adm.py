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
from survey.figure_eight import FigureEight, API_KEY, JOB_ID, RowState
#from survey.unit import HHI_Resp_ADM,  hhi_resp_adm_to_resp_result, save_resp_result
from notebooks.utils.explanation import get_acceptance_propability, get_best_offer_probability
from notebooks.utils import value_repr
from notebooks.models.metrics import gain

from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
from survey.hhi_prop_adm import insert_row, get_table as get_prop_table


############ Consts #################################
TUBE_RES_FILENAME = os.environ.get("TUBE_RES_FILENAME", "./data/HH_SURVEY1/output/hhi_resp_adm.csv")

SURVEY_INFOS_FILENAME = os.environ.get("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE_COMPLETION_CODE = os.environ.get("COMPLETION_CODE", "tTkEnH5A4syJ6N4t")

LAST_CHANGE_KEY = '_time_change'

STATUS_KEY = '_status'

WORKER_KEY = '_worker'

# sqlite return 'rowid' as default 
PK_KEY = 'rowid'

OFFER_VALUES = {str(val):value_repr(val) for val in range(0, 201, 5)}

JUDGING_TIMEOUT_SEC = 5*60

if app.config["DEBUG"]:
    JUDGING_TIMEOUT_SEC = 10

ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "tsv", "xml"}

with open(SURVEY_INFOS_FILENAME) as inp_f:
    MODEL_INFOS = json.load(inp_f)

bp = Blueprint("hhi_resp_adm", __name__)
######################################################



############# HELPERS   ###########################

class HHI_Resp_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["min_offer"] = None


class UploadForm(FlaskForm):
    job_id = StringField("Job id", validators=[DataRequired()])
    overwite = BooleanField("Overwrite")
    submit = SubmitField("Submit")


def hhi_resp_adm_to_resp_result(proposal, job_id=None, worker_id=None):
    """
    :returns: {
        time: server time when genererting the result
        min_offer: final proposer min_offer
        job_id: fig-8 job id
        worker_id: fig-8 worker id
    }
    """
    result = {}
    result["time"] = str(datetime.datetime.now())
    result["min_offer"] = proposal["min_offer"]
    
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result


def save_resp_result(filename, proposal_result):
    if "job_id" in proposal_result:
        folder, fname = os.path.split(filename)
        filename = os.path.join(folder, f"{proposal_result['job_id']}__{fname}")
    file_exists = os.path.exists(filename)
    os.makedirs(os.path.split(filename)[0], exist_ok=True)
    with open(filename, "a") as out_f:

        writer = csv.writer(out_f)
        if not file_exists:
            writer.writerow(proposal_result.keys())
        writer.writerow(proposal_result.values())

def generate_completion_code():

    part1 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    part2 = BASE_COMPLETION_CODE
    part3 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return "".join([part1, part2, part3])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_table(job_id, category=None):
    """
    Generate a table name based on the job_id
    :param job_id:
    :param category:
    """
    if category is None:
        return f"hhi_resp_adm__{job_id}"
    else:
        return f"hhi_resp_adm__{category}__{job_id}"


def save_resp_result2db(con, proposal_result, job_id, overwrite=False):
    table = get_table(job_id)
    df = pd.DataFrame(data=[proposal_result])
    insert(df, table=table, con=con, overwrite=overwrite)

class ProposerForm(FlaskForm):
    min_offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")


@bp.route("/hhi_resp_adm/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        session['proposal'] = HHI_Resp_ADM()
        worker_id = request.args.get("worker_id", "")
        job_id = request.args.get("job_id", "")
        session["worker_id"] = worker_id
        session["job_id"] = job_id

    if request.method == "POST":
        proposal = session["proposal"]
        proposal["time_stop"] = time.time()
        min_offer = request.form["min_offer"]
        try:
            min_offer = int(min_offer)
        except ValueError:
            min_offer = None
        proposal["min_offer"] = min_offer
        ##TODO return redirect
        session['proposal'] = proposal
        return redirect(url_for("hhi_resp_adm.done"))

    session["hhi_resp_adm"] = True
    return render_template("hhi_resp_adm.html", offer_values=OFFER_VALUES, form=ProposerForm())

@bp.route("/hhi_resp_adm/done")
def done():
    if not session.get("hhi_resp_adm", None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if not session.get("worker_code"):
        worker_code = session.get('worker_code', '')
        worker_code = generate_completion_code()
        proposal = session["proposal"]
        job_id = session["job_id"]
        worker_id = session["worker_id"]
        resp_result = hhi_resp_adm_to_resp_result(proposal, job_id=job_id, worker_id=worker_id)
        try:
            save_resp_result(TUBE_RES_FILENAME, resp_result)
        except Exception as err:
            app.logger.error(f"{err}")
        try:
            save_resp_result2db(get_db("RESULT"), resp_result, job_id)
        except Exception as err:
            app.logger.error(f"{err}")
        con = get_db("DATA")
        table = get_prop_table(job_id)
        insert_row(job_id, proposal)
        session.clear()

        session["hhi_resp_adm"] = True
        session["worker_code"] = worker_code
    return render_template("hhi_resp_adm.done.html", worker_code=session["worker_code"])


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
@bp.route("/hhi_resp_adm/webhook", methods=["GET", "POST"])
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
@bp.route("/hhi_resp_adm/upload", methods=["GET", "POST"])
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
            df[LAST_CHANGE_KEY] = time.time()
            df[WORKER_KEY] = None
            table = get_table(job_id)
            # TODO should use g instead
            con = get_db("DATA")
            insert(df, table, con=con, overwrite=overwrite)
            return redirect(url_for('hhi_resp_adm.upload',
                                    filename=filename))
    return render_template('upload.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
