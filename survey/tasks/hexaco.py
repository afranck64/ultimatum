from flask import (
    Blueprint, render_template
)

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
    return handle_task_done("hexaco", unique_fields=["worker_id"])