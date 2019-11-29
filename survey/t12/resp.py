import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index, handle_index_dss

############ Consts #################################

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.resp", __name__)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/resp/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT, has_dss_component=True)

@csrf_protect.exempt
@bp.route("/resp_dss/", methods=["GET", "POST"])
def index_dss():
    messages = [
        """The Proposer has the option to use an AI Recommendation System (AI System) to help him decide which offer to make.
The system was trained using prior interactions of comparable bargaining situations."""
    ]
    return handle_index_dss(TREATMENT, messages=messages)

@bp.route("/resp/done")
def done():
    return handle_done(TREATMENT)