import json
import os
import time
import datetime

from flask import (
    Blueprint
)

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row, handle_index_dss, handle_feedback, create_prop_data_table, get_row_ignore_job
from survey.globals import AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_PROPOSER, AI_SYSTEM_DESCRIPTION_USAGE_PROPOSER, AI_SYSTEM_UNINFORMED_RESPONDER_INFORMATION_PROPOSER

############ Consts #################################
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

MODEL_INFOS_KEY = f"{TREATMENT.upper()}_MODEL_INFOS"
MODEL_KEY = f"{TREATMENT.upper()}_MODEL"

bp = Blueprint(f"{TREATMENT}.{BASE}", __name__)

REF = "t10a"

with app.app_context():
    create_prop_data_table(TREATMENT, REF)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT,  get_row_func=get_row_ignore_job)

@bp.route("/prop_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_PROPOSER, AI_SYSTEM_UNINFORMED_RESPONDER_INFORMATION_PROPOSER, AI_SYSTEM_DESCRIPTION_USAGE_PROPOSER]
    return handle_index_dss(TREATMENT, messages=messages)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@csrf_protect.exempt
@bp.route("/prop_feedback/", methods=["GET", "POST"])
def feedback():
    alternative_affirmation = "I would have made another offer if the RESPONDER was informed about the AI System"
    return handle_feedback(TREATMENT, alternative_affirmation=alternative_affirmation)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT, ignore_job=True)
    