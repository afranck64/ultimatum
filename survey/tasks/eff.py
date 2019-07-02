from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.eff", __name__)

SOLUTIONS = {
    "img_1": "ydrn",
    "img_2": None,
    "img_3": "bawb",
    "img_4": "swfd",
    "img_5": "rrgq",
    "img_6": "rcnb",
    "img_7": "wwch",
    "img_8": "yqch",
    "img_9": None,
    "img_10": "zzqp",
    "img_11": "dbhw",
    "img_12": "wqyw",
    "img_13": "cdmm",
    "img_14": "broi",
    "img_15": "rybs",
    "img_16": None,
    "img_17": "yfyo",
    "img_18": "pwbq",
    "img_19": "whqw",   #None?
    "img_20": "tnrb"    #None?
}

def validate_response(response):
    for key in SOLUTIONS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for key, value in SOLUTIONS:
        if response[key].lower() == value:
            bonus += 2
    return bonus
############

@csrf_protect.exempt
@bp.route("/eff/", methods=["GET", "POST"])
def index():
    return handle_task_index("eff", validate_response=validate_response)


@bp.route("/eff/done")
def done():
    return handle_task_done("eff", unique_fields=["worker_id"])