import datetime
from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.tasks.task import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.eff", __name__)

SOLUTIONS = {
    "img_1": "ydrn",
    "img_2": "tbta",    #None?
    "img_3": "bawb",
    "img_4": "swfd",
    "img_5": "rrgq",
    "img_6": "rcnb",
    "img_7": "wwch",
    "img_8": "yqch",
    "img_9": "ebqn",    #None?
    "img_10": "zzqp",
    "img_11": "dbhw",
    "img_12": "wqyw",
    "img_13": "cdmm",
    "img_14": "broi",
    "img_15": "rybs",
    "img_16": "mcms",     #None?
    "img_17": "yfyo",
    "img_18": "pwbq",
    "img_19": "whqw",   #None?
    "img_20": "tnrb"    #None?
}

MAX_BONUS = 40

def validate_response(response):
    for key in SOLUTIONS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for key, value in SOLUTIONS.items():
        if response[key].lower() == value:
            bonus += 2
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
    result["count_effort"] = response_to_bonus(response) // 2
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route("/eff/", methods=["GET", "POST"])
def index():
    return handle_task_index("eff", validate_response=validate_response)


@bp.route("/eff/done")
def done():
    return handle_task_done("eff", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)