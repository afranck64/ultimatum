import json
import os
import time
import datetime

from flask import (
    Blueprint, make_response, jsonify
)

from core.utils import cents_repr

from survey._app import app, csrf_protect
from survey.txx.prop import handle_check, handle_done, handle_index, insert_row, handle_index_dss

############ Consts #################################
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.{BASE}", __name__)
######################################################



############# HELPERS   ###########################

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT)

@bp.route("/prop/check/")
def check():
    app.logger.warning(f"{TREATMENT}index_dss")
    req_response = make_response(jsonify({"offer": 0, "acceptance_probability": 0, "best_offer_probability": 0}))    
    return req_response

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT)
    