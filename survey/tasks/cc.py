import os
import datetime
import time
import json

from flask import (
    Blueprint, render_template, request, redirect, flash, url_for, make_response, g
)

from survey._app import csrf_protect, app, VALUES_SEPARATOR
from survey.utils import set_cookie_obj, get_cookie_obj

from survey.tasks.task import handle_task_done, handle_task_index


#### const
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint(f"tasks.{BASE}", __name__)

CELL_BONUS_CENTS = 2
NB_CELLS = 50
MAX_BONUS = NB_CELLS * CELL_BONUS_CENTS
LETTER_M = "M"
LETTER_W = "W"
LETTER_M_BONUS = 10
LETTER_W_BONUS = -5
ITEMS = [LETTER_M] * 3 + [LETTER_W] * 2


FIELDS = {}
FEATURES = {
    "cc_m_count",  #how often the user clicked on cc
    "cc_m_avg_click_delay", #the average time after which the user clicked on m
    "cc_w_count",
    "cc_w_avg_click_delay",
}
def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for letter, clicked in zip(response["letters"], response["clicked"]):
        if letter==LETTER_M and clicked:
            bonus += LETTER_M_BONUS
        elif letter==LETTER_W and clicked:
            bonus += LETTER_W_BONUS
    if bonus < 0:
        bonus = 0
    return bonus


def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        cells: number of opened cells
        time_spent_???: time (ms) spent on this task
        timestamp: server time when genererting the result
        job_id: job id
        worker_id: worker id
        *: response's keys
    }
    """
    result = dict()
    letters = response["letters"]
    clicked = response["clicked"]
    delays = response["delays"]
    result["letters"] = VALUES_SEPARATOR.join(letters)
    result["clicked"] = VALUES_SEPARATOR.join(str(int(v)) for v in clicked)
    result["delays"] = VALUES_SEPARATOR.join(str(round(delay, 4)) for delay in delays)
    result["cc_m_count"] = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_M and click])
    result["cc_m_avg_click_delay"] = sum([delay if (letter==LETTER_M and click) else 0 for letter, click, delay in zip(letters, clicked, delays)]) / (result["cc_m_count"] or 1)
    result["cc_w_count"] = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_W and click])
    result["cc_w_avg_click_delay"] = sum([delay if (letter==LETTER_W and click) else 0 for letter, click, delay in zip(letters, clicked, delays)]) / (result["cc_w_count"] or 1)
    result["cc_time_spent"] = response["time_spent"]
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route(f"/{BASE}/", methods=["GET", "POST"])
def index():
    app.logger.debug("index cc")
    # return handle_task_index(f"{BASE}", validate_response=validate_response, template_kwargs={"callback_url": url_for(f"tasks.{BASE}.check")})

    cookie_obj = get_cookie_obj(BASE)
    worker_code_key = f"{BASE}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id:
        req_response =  make_response(redirect(url_for(f"tasks.{BASE}.done")))
        return req_response
    if request.method == "GET":
        app.logger.debug("index cc get")
        cookie_obj[BASE] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["time_start"] = time.time()
    if request.method == "POST":
        app.logger.debug("index cc post")
        #response = request.form.to_dict()
        response = cookie_obj["result"]
        if validate_response is not None and validate_response(response):
            response["time_stop"] = time.time()
            response["time_start"] = cookie_obj.get("time_start")
            cookie_obj["response"] = response
            req_response = make_response(redirect(url_for(f"tasks.{BASE}.done")))
            set_cookie_obj(req_response, BASE, cookie_obj)
            return req_response

    req_response = make_response(render_template(f"tasks/{BASE}.html", callback_url=url_for(f"tasks.{BASE}.check"), items=ITEMS))
    cookie_obj[BASE] = True
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response



@bp.route(f"/{BASE}/done/")
def done():
    return handle_task_done(f"{BASE}", unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)

@csrf_protect.exempt
@bp.route(f"/{BASE}/check/", methods=["GET", "POST"])
def check():
    app.logger.debug("index cc check")
    cookie_obj = get_cookie_obj(BASE)
    if not cookie_obj.get(BASE, None):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    #data: {"letters":[], "delays":[], "clicked":[]}
    result = json.loads(request.data)
    cookie_obj["result"] = result
    req_response = make_response("")
    set_cookie_obj(req_response, BASE, cookie_obj)
    app.logger.debug("index cc check - done")
    return req_response