import json
import os
import time
import datetime

from flask import (
    Blueprint
)

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row, handle_index_dss

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
    # messages = [
    #     """You have been assigned the role of a PROPOSER. As a PROPOSER, you will make an offer to the RESPONDER.""",
    # ]
    return handle_index(TREATMENT, messages=messages)

@bp.route("/prop_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [
        """You have been assigned the role of a PROPOSER. As a PROPOSER, you will make an offer to the RESPONDER. Instead of purely relying on your own intuition, you can use an AI Recommendation System (Machine-Learning System) to help you with your offer. The system was trained using prior interactions of comparable bargaining situations.""",
        """To use the AI System, simply select a test offer and submit it to the system. The system will tell you its estimates on:
1. The probability that your offer will be accepted by your specific RESPONDER.
2. The probability that your offer is the minimal offer accepted by your specific RESPONDER.

You can use the system as often as you want."""
    ]
    return handle_index_dss(TREATMENT, messages=messages)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    