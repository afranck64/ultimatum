import os
import datetime
import random
from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.tasks.task import handle_task_done, handle_task_index


#### const
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint(f"tasks.{BASE}", __name__)

FIELDS = {"q1", "q2", "q3", "q4"}
def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

INDEX_PROBABILITY = 0
INDEX_GAIN = 1
CHOICES = {
    "q1": [(1,1), (0.9, 1.1), (0.8, 1.3), (0.7, 1.5), (0.6, 1.7), (0.5, 2.1), (0.4, 2.7), (0.3, 3.6), (0.2, 5.4), (0.1, 10.90)],
    "q2": [(1,1), (0.9, 1.2), (0.8, 1.5), (0.7, 1.9), (0.6, 2.3), (0.5, 3.0), (0.4, 4.0), (0.3, 5.7), (0.2, 9.0), (0.1, 19.90)],
    "q3": [(1,1), (0.9, 1.7), (0.8, 2.5), (0.7, 3.6), (0.6, 5.0), (0.5, 7.0), (0.4, 10), (0.3, 15), (0.2, 25), (0.1, 55)],
    "q4": [(1,1), (0.9, 2.2), (0.8, 3.8), (0.7, 5.7), (0.6, 8.3), (0.5, 12), (0.4, 17.5), (0.3, 26.7), (0.2, 45), (0.1, 100)],
}

MAX_BONUS = sum(options[-1][1] for options in CHOICES.values()) / len(CHOICES)

FEATURES = set(f"risk_{k}" for k in FIELDS) | set({
    "risk_expected_value",
    "risk_time_spent"
})

def response_to_bonus(response):
    bonus = 0
    tmp_bonus = 0.0
    for key, options in CHOICES.items():
        user_choice = int(response[key])
        user_p = options[user_choice][INDEX_PROBABILITY]
        p = random.random()
        if user_p >= p:
            tmp_bonus += options[user_choice][INDEX_GAIN]
    bonus = round(tmp_bonus / len(CHOICES))
    return bonus

def get_expected_value_from_response(response):
    tmp_expected_value = 0
    for key, options in CHOICES.items():
        user_choice = int(response[key])
        tmp_expected_value += options[user_choice][INDEX_GAIN] * options[user_choice][INDEX_PROBABILITY]
    expected_value = round(tmp_expected_value / len(CHOICES), 4)
    return expected_value


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
    result.update({f"{BASE}_{key}": CHOICES[key][response[key]][INDEX_PROBABILITY]*CHOICES[key][response[key]][INDEX_GAIN] for key in FIELDS})
    result["timestamp"] = str(datetime.datetime.now())
    result["risk_expected_value"] = get_expected_value_from_response(response)
    result["risk_time_spent"] = result["time_spent"]
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    return result
############

@csrf_protect.exempt
@bp.route(f"/{BASE}/", methods=["GET", "POST"])
def index():
    return handle_task_index(f"{BASE}", validate_response=validate_response, template_kwargs={"options": CHOICES})


@bp.route(f"/{BASE}/done")
def done():
    return handle_task_done(f"{BASE}", numeric_fields="*", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)