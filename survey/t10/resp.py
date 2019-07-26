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
from survey.utils import save_result2db, save_result2file, get_output_filename, generate_completion_code, get_table, LAST_MODIFIED_KEY, WORKER_KEY, STATUS_KEY, PK_KEY
from survey.txx.resp import handle_done, handle_index, finalize_resp


############ Consts #################################
SURVEY_INFOS_FILENAME = os.getenv("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.resp", __name__)
######################################################



############# HELPERS   ###########################

class HHI_Resp_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["min_offer"] = None
        self["time_start"] = time.time()
        self["timestamp"] = None

@csrf_protect.exempt
@bp.route("/resp/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT)

@bp.route("/resp/done")
def done():
    return handle_done(TREATMENT)