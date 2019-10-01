import os
import datetime
import time

from flask import (
    Blueprint, render_template, request, redirect, flash, url_for, make_response, g
)

from survey._app import csrf_protect
from survey.utils import set_cookie_obj, get_cookie_obj

from survey.tasks.task import handle_task_done, handle_task_index


#### const
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint(f"tasks.{BASE}", __name__)

CELL_BONUS_CENTS = 2
NB_CELLS = 50
MAX_BONUS = NB_CELLS * CELL_BONUS_CENTS

FIELDS = {f"cell{i}" for i in range(1, 51)}
FEATURES = {
    "cells",
    f"time_spent_{BASE}"
}
def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for field in FIELDS:
        bonus += response[field] * CELL_BONUS_CENTS
    return bonus


def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        cells: number of opened cells
        time_spent_???: time (ms) spent on this task
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    result["cells"] = response_to_bonus(response)//CELL_BONUS_CENTS
    result[f"time_spent_{BASE}"] = int(response["time_stop"] - response["time_start"]) * 1000
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route(f"/{BASE}/", methods=["GET", "POST"])
def index():
    #return handle_task_index(f"{BASE}", validate_response=validate_response)

    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id:
        req_response =  make_response(redirect(url_for(f"tasks.{BASE}.done")))
        return req_response

    cookie_obj = get_cookie_obj(BASE)
    g.cookie_obj = cookie_obj
    if request.method == "GET":
        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["time_start"] = time.time()
        cookie_obj["cells"] = {f"cell{cid}":0 for cid in range(1, 51)}
    if request.method == "POST":
        #response = request.form.to_dict()
        response = cookie_obj["cells"]
        if validate_response is not None and validate_response(response):
            response["time_stop"] = time.time()
            response["time_start"] = cookie_obj.get("time_start")
            cookie_obj["response"] = response
            req_response = make_response(redirect(url_for(f"tasks.{BASE}.done")))
            set_cookie_obj(req_response, BASE, cookie_obj)
            return req_response

    req_response = make_response(render_template(f"tasks/{BASE}.html"))
    cookie_obj[BASE] = True
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response



@bp.route(f"/{BASE}/done/")
def done():
    return handle_task_done(f"{BASE}", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)

@bp.route(f"/{BASE}/check/")
def check():
    cookie_obj = get_cookie_obj(BASE)
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    cell = request.args.get("cell")
    cells = cookie_obj["cells"]
    cells[cell] = 1
    cookie_obj["cells"] = cells
    req_response = make_response("")
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response