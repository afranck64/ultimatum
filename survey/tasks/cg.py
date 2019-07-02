from flask import (
    Blueprint, render_template
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### helpers
bp = Blueprint("tasks.cg", __name__)

FIELDS = {"donation_a", "donation_b", "donation_c"}

def validate_response(response):
    for key in FIELDS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 60
    for k in ["donation_a", "donation_b", "donation_c"]:
        bonus -= response["donation_a"]
    return bonus

############

@csrf_protect.exempt
@bp.route("/cg/", methods=["GET", "POST"])
def index():
    return handle_task_index("cg", validate_response=validate_response)


@bp.route("/cg/done")
def done():
    return handle_task_done("cg", numeric_fields="*", unique_fields=["worker_id"])