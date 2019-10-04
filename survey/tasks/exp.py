import datetime
import os

from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.tasks.task import handle_task_done, handle_task_index


#### helpers
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint(f"tasks.{BASE}", __name__)

FIELDS = {"ultimatum_game_experience"}
FEATURES = {f"{BASE}_{k}" for k in FIELDS}

MAX_BONUS = 60


def validate_response(response):
    for key in FIELDS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    return 0

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
    result.update({f"{BASE}_{k}": response[k] for k in FIELDS})
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route(f"/{BASE}/", methods=["GET", "POST"])
def index():
    return handle_task_index(BASE, validate_response=validate_response)


@bp.route("/exp/done")
def done():
    return handle_task_done(BASE, numeric_fields="*", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)