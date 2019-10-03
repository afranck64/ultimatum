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

class HHI_Prop_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["offer"] = None
        self["offer_final"] = None
        self["time_start"] = time.time()
        self["time_stop"] = None
        self["ai_calls_offer"] = []
        self["ai_calls_time"] = []
        self["ai_calls_response"] = []
        self.__dict__ = self


def prop_to_prop_result(proposal, job_id=None, worker_id=None, row_data=None):
    """
    :returns: {
        timestamp: server time when genererting the result
        offer: final proposer offer
        time_spent: whole time spent for the proposal
        ai_nb_calls: number of calls of the ADM system
        ai_call_min_offer: min offer checked on the ADM
        ai_call_max_offer: max offer checked on the ADM
        ai_mean_time: mean time between consecutive calls on to the ADM
        ai_call_offers: ":" separated values
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        data__*: base unit data
    }
    """
    if row_data is None:
        row_data = {}
    result = {}
    result["timestamp"] = str(datetime.datetime.now())
    result["offer"] = proposal["offer"]
    result["offer_final"] = proposal["offer"]
    result["prop_time_spent"] = round(proposal["time_stop"] - proposal["time_start"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["prop_worker_id"] = worker_id
    result["resp_worker_id"] = row_data["resp_worker_id"]
    result["min_offer"] = row_data["min_offer"]
    discard_row_data_fields = {"job_id", "worker_id", "job_id", "min_offer", "resp_worker_id", "row_id", "status", "time_start", "time_stop", "timestamp", "updated", "worker_id"}
    for k, v in row_data.items():
        if k not in discard_row_data_fields:
            result[k] = v
    return result

@csrf_protect.exempt
@bp.route("/prop/", methods=["GET", "POST"])
def index():
    return handle_index(TREATMENT)


# @bp.route("/prop_dss/", methods=["GET", "POST"])
# def index_dss():
#     app.logger.warn(f"{TREATMENT}index_dss")
#     return handle_index_dss(TREATMENT)

@bp.route("/prop/check/")
def check():
    app.logger.warn(f"{TREATMENT}index_dss")
    req_response = make_response(jsonify({"offer": 0, "acceptance_probability": 0, "best_offer_probability": 0}))    
    return req_response

# @bp.route("/prop/check/")
# def check():
#     return handle_check(TREATMENT)

@bp.route("/prop/done")
def done():
    return handle_done(TREATMENT, response_to_result_func=prop_to_prop_result)
    