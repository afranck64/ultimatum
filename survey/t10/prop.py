import json
import os
import time
import datetime

from flask import (
    Blueprint
)

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row

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
    # flash("""In this task, you will be helped by an Artificial intelligence which can help you get insights on how good your offer in respect to maximum you can gain from it before sending it to the RESPONDER""")
    messages = [
        """An artificial intelligence system (AI-System) is available to gain some insight about the RESPONDER. There is no restriction to the use of the AI-System.""",
        """The RESPONDER doesn't know about the existence of the AI-System."""
    ]
    return handle_index(TREATMENT, messages=messages)

@bp.route("/prop/check/")
def check():
    return handle_check(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    