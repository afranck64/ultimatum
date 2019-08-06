from flask import (
    Blueprint, render_template
)
import datetime
from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.hexaco", __name__)

FIELDS = {f"q{i}" for i in range(1, 31)}

MAX_BONUS = 0

def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

REVERSE_SCORED_QUESTIONS = {"q6", "q12", "q15", "q21", "q24", "q30", "q5", "q14", "q23", "q26", "q4", "q7", "q10", "q28"}
Honesty_Humility_qxx = {"q3", "q9", "q18", "q6", "q12", "q15", "q21", "q24", "q27", "q30"}
Extraversion_qxx = {"q2", "q8", "q11", "q17", "q20", "q5", "q14", "q23", "q29"}
Agreeableness_qxx = {"q1", "q4", "q7", "q10", "q13", "q16", "q19", "q22", "q25", "q28"}

def response_to_result(response, job_id=None, worker_id=None):
    """
    The questions are saved "as-it" prior to reverserving questions scores to compute emotional traits
    :returns: {
        Honesty_Humility:
        Extraversion:
        Agreeableness:
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    for key in REVERSE_SCORED_QUESTIONS:
        response[key] = 6 - response[key]
    result["Honesty_Humility"] = sum(response[key] for key in Honesty_Humility_qxx)/10
    result["Extraversion"] = sum(response[key] for key in Extraversion_qxx)/10
    result["Agreeableness"] = sum(response[key] for key in Agreeableness_qxx)/10
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result

def response_to_bonus(response):
    bonus = 0
    return bonus
############

@csrf_protect.exempt
@bp.route("/hexaco/", methods=["GET", "POST"])
def index():
    return handle_task_index("hexaco", validate_response)


@bp.route("/hexaco/done")
def done():
    return handle_task_done("hexaco", unique_fields=["worker_id"], response_to_result_func=response_to_result, numeric_fields="*")