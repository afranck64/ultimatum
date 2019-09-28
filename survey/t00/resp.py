import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index, finalize_resp


############ Consts #################################

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