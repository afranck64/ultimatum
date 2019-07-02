from flask import (
    Blueprint, render_template, request
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.risk", __name__)

FORM_FIELDS = {f"cell{i}" for i in range(1, 51)}
def validate_response(response):
    for field in FORM_FIELDS:
        if field not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for val in response.values():
        bonus += val * 2
    return bonus

############

@csrf_protect.exempt
@bp.route("/risk/", methods=["GET", "POST"])
def index():
    return handle_task_index("risk", validate_response=validate_response)


@bp.route("/risk/done")
def done():
    return handle_task_done("risk", unique_fields=["worker_id"])

@bp.route("/risk/check")
def check():
    print (request.args)
    return ""