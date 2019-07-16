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

from core.utils.explanation import get_acceptance_propability, get_best_offer_probability
from core.utils.preprocessing import df_to_xy
from core.utils import cents_repr
from core.models.metrics import gain, MAX_GAIN

from survey._app import app, csrf_protect
from survey.figure_eight import FigureEight, RowState
from survey.admin import get_job_config
from survey.db import insert, get_db, table_exists
from survey.utils import (save_result2db, save_result2file, get_output_filename, get_table,
    generate_completion_code, increase_worker_bonus, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY)
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row

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
    ai_times = []
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
        if k not in discard_row_data_fields:
            result[k] = v
    return result

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    