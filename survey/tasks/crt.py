from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.crt", __name__)

def response_to_bonus(response):
    bonus = 0
    if response["q1"] == 10:
        bonus += 15
    if response["q2"] == 10:
        bonus += 15
    if response["q3"] == 23:
        bonus += 15
    return bonus
############

@csrf_protect.exempt
@bp.route("/crt/", methods=["GET", "POST"])
def index():
    return handle_task_index("crt")


@bp.route("/crt/done")
def done():
    return handle_task_done("crt", numeric_fields="*", unique_fields=["worker_id"])