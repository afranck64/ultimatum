import datetime
import time

from flask import (
    Blueprint, render_template, request, session, redirect, flash, url_for
)

from survey._app import csrf_protect
from survey.utils import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.risk", __name__)

MAX_BONUS = 100

FIELDS = {f"cell{i}" for i in range(1, 51)}
def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for field in FIELDS:
        bonus += response[field] * 2
    return bonus


def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        cells: number of opened cells
        time_spent_risk: time (ms) spent on this task
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    result["cells"] = response_to_bonus(response)//2
    result["time_spent_risk"] = int(response["time_stop"] - response["time_start"]) * 1000
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route("/risk/", methods=["GET", "POST"])
def index():
    base = "risk"
    #return handle_task_index("risk", validate_response=validate_response)

    # if session.get("eff", None) and session.get("worker_id", None):
    #     return redirect(url_for("eff.done"))
    if request.method == "GET":
        worker_id = request.args.get("worker_id", "na")
        job_id = request.args.get("job_id", "na")
        session[base] = True
        session["worker_id"] = worker_id
        session["job_id"] = job_id
        session["time_start"] = time.time()
        session["cells"] = {f"cell{cid}":0 for cid in range(1, 51)}
    if request.method == "POST":
        #response = request.form.to_dict()
        response = session["cells"]
        if validate_response is not None and validate_response(response):
            response["time_stop"] = time.time()
            response["time_start"] = session.get("time_start")
            session["response"] = response
            return redirect(url_for(f"tasks.{base}.done"))
        else:
            flash("Please check your fields")
    return render_template(f"tasks/{base}.html")



@bp.route("/risk/done/")
def done():
    return handle_task_done("risk", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)

@bp.route("/risk/check/")
def check():
    if not session.get("risk", None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    cell = request.args.get("cell")
    cells = session["cells"]
    cells[cell] = 1
    session["cells"] = cells
    return ""