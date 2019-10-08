import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index


############ Consts #################################

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.resp", __name__)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/resp/", methods=["GET", "POST"])
def index():
    messages = [
        """An AI Machine-Learning System will autonomously make an offer to you on behalf of a human proposer. The system was trained using prior interactions of comparable bargaining situations. The human proposer does not make any decisions, he/she only receives whatever money the system earns from this task."""
    ]
    return handle_index(TREATMENT, messages=messages)

@bp.route("/resp/done")
def done():
    return handle_done(TREATMENT)