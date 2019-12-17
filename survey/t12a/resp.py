import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index, handle_index_dss, handle_feedback, handle_done_no_prop, create_resp_data_table
from survey.globals import AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_RESPONDER
############ Consts #################################

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.resp", __name__)

REF = 't10a'

with app.app_context():
    create_resp_data_table(TREATMENT, REF)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/resp/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT, has_dss_component=True)

@csrf_protect.exempt
@bp.route("/resp_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_RESPONDER]
    return handle_index_dss(TREATMENT, messages=messages)

@csrf_protect.exempt
@bp.route("/resp_feedback/", methods=["GET", "POST"])
def feedback():
    return handle_feedback(TREATMENT)

@bp.route("/resp/done")
def done():
    return handle_done_no_prop(TREATMENT, no_features=True)