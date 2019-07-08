import datetime

from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### helpers
bp = Blueprint("tasks.cg", __name__)

FIELDS = {"donation_a", "donation_b", "donation_c"}

MAX_BONUS = 60


def validate_response(response):
    for key in FIELDS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 60
    for key in ["donation_a", "donation_b", "donation_c"]:
        bonus -= response[key]
    return bonus

def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    result["selfish"] = 60 - response_to_bonus(response)
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route("/cg/", methods=["GET", "POST"])
def index():
    return handle_task_index("cg", validate_response=validate_response)


@bp.route("/cg/done")
def done():
    return handle_task_done("cg", numeric_fields="*", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)