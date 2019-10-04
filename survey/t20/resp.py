import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index
from survey.txx.helpers import finalize_resp


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
        """An AI Recommendation System (Machine-Learning System) will face you in the name of the PROPOSER. The system was trained using prior interactions of comparable bargaining situations. The gains of the AI-System will be transfered to the human PROPOSER."""
    ]
    return handle_index(TREATMENT, messages=messages)

@bp.route("/resp/done")
def done():
    return handle_done(TREATMENT)