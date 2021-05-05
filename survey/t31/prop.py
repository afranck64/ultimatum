import json
import os
import time
import datetime

from flask import (
    Blueprint
)

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row, handle_index_dss, handle_feedback
from survey.globals import AI_SYSTEM_DESCRIPTION_BRIEF_PROPOSER, AI_SYSTEM_DESCRIPTION_USAGE_PROPOSER, AI_SYSTEM_DESCRIPTION_EXTENDED_PROPOSER

############ Consts #################################
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

MODEL_INFOS_KEY = f"{TREATMENT.upper()}_MODEL_INFOS"
MODEL_KEY = f"{TREATMENT.upper()}_MODEL"

bp = Blueprint(f"{TREATMENT}.{BASE}", __name__)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    messages = []
    return handle_index(TREATMENT, messages=messages)

@bp.route("/prop_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [AI_SYSTEM_DESCRIPTION_BRIEF_PROPOSER, AI_SYSTEM_DESCRIPTION_EXTENDED_PROPOSER, AI_SYSTEM_DESCRIPTION_USAGE_PROPOSER]
    return handle_index_dss(TREATMENT, messages=messages)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@csrf_protect.exempt
@bp.route("/prop_feedback/", methods=["GET", "POST"])
def feedback():
    return handle_feedback(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    