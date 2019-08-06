import datetime

from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.crt", __name__)

MAX_BONUS = 45

def validate_response(response):
    for field in ["q1", "q2", "q3"]:
        if field not in response:
            return False
    return True

SOLUTIONS = {
    "q1": 10,
    "q2": 10,
    "q3": 23
}
def response_to_bonus(response):
    bonus = 0
    for key, value in SOLUTIONS.items():
        if response[key] == value:
            bonus += 15
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
    result["crt_performance"] = response_to_bonus(response) / 15
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route("/crt/", methods=["GET", "POST"])
def index():
    return handle_task_index("crt", validate_response=validate_response)


@bp.route("/crt/done")
def done():
    return handle_task_done("crt", numeric_fields="*", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)