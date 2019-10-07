import os
import datetime
import time
import json
import random

from flask import (
    Blueprint, render_template, request, redirect, flash, url_for, make_response, g
)

from survey._app import csrf_protect, app, VALUES_SEPARATOR
from survey.utils import set_cookie_obj, get_cookie_obj

from survey.tasks.task import handle_task_done, handle_task_index

from scipy.stats import norm
import math
Z = norm.ppf
 
def SDT(hits, misses, fas, crs):
    """
    :param hits: Number correct hits (M)
    :param misses: Number of misses (M)
    :param fas: false alarms, Number of wrong clicks (W)
    :param crs: correct-rejections
    returns a dict with d-prime measures given hits, misses, false alarms, and correct rejections
    #Thanks: https://lindeloev.net/calculating-d-in-python-and-php/
    """
    # Floors an ceilings are replaced by half hits and half FA's
    half_hit = 0.5 / (hits + misses)
    half_fa = 0.5 / (fas + crs)
 
    # Calculate hit_rate and avoid d' infinity
    hit_rate = hits / (hits + misses)
    if hit_rate == 1: 
        hit_rate = 1 - half_hit
    if hit_rate == 0: 
        hit_rate = half_hit
 
    # Calculate false alarm rate and avoid d' infinity
    fa_rate = fas / (fas + crs)
    if fa_rate == 1: 
        fa_rate = 1 - half_fa
    if fa_rate == 0: 
        fa_rate = half_fa
 
    # Return d', beta, c and Ad'
    out = {}
    out['cc_sensitivity'] = Z(hit_rate) - Z(fa_rate)
    out['cc_beta'] = math.exp((Z(fa_rate)**2 - Z(hit_rate)**2) / 2)
    out['cc_criterion'] = -(Z(hit_rate) + Z(fa_rate)) / 2
    out['cc_Ad'] = norm.cdf(out['cc_sensitivity'] / math.sqrt(2))
    out["cc_hit_rate"] = hits / (hits + misses)     #raw hit_rate
    out["cc_false_alarm_rate"] = fas / (fas + crs)   #raw false_alarm rate
    out["cc_hits"] = hits
    out["cc_misses"] = misses
    out["cc_false_alarms"] = fas
    out["cc_correct_rejections"] = crs

    
    return(out)

#### const
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint(f"tasks.{BASE}", __name__)

LETTER_SIGNAL = "M"
LETTER_NOISE = "W"
LETTER_SIGNAL_BONUS = 5
LETTER_NOISE_BONUS = -5
NB_HIT_LETTERS = 10
NB_NOISE_LETTERS = 5
ITEMS = [LETTER_SIGNAL] * NB_HIT_LETTERS + [LETTER_NOISE] * NB_NOISE_LETTERS
## Following, delays are expressed in milliseconds
# how long the stimulus is shown
TIME_SHOW = 100
# how long to wait before activation of the button
TIME_HIDE = 0
# how long the button should remain active
TIME_WAIT = 500
# the assigned time in case the user didn't clicked on time
DELAY_MISSED = TIME_WAIT * 2 + TIME_HIDE
# the minimum delay before starting a round
START_DELAY_MIN = 500
# the maximum delay before starting a round
START_DELAY_MAX = 3000
START_DELAYS = [random.randint(START_DELAY_MIN, START_DELAY_MAX) for _ in ITEMS]

MAX_BONUS = sum(LETTER_SIGNAL_BONUS for letter in ITEMS if letter==LETTER_SIGNAL)

FIELDS = {}
FEATURES = {
    "cc_hits",  #how often the user clicked on cc
    "cc_hit_avg_click_delay", #the average time after which the user clicked on m
    "cc_false_alarms",
    "cc_false_alarm_avg_click_delay",
    "cc_sensitivity",    #dprime/sensitivity, beta c and Ad of signal detection theory
    "cc_beta",          # another measure of criterion
    "cc_criterion",     # a measure of criterion
    # "cc_Ad",
    "cc_hit_rate",
    "cc_false_alarm_rate",
}
def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True

def response_to_bonus(response):
    bonus = 0
    for letter, clicked in zip(response["letters"], response["clicked"]):
        if letter==LETTER_SIGNAL and clicked:
            bonus += LETTER_SIGNAL_BONUS
        elif letter==LETTER_NOISE and clicked:
            bonus += LETTER_NOISE_BONUS
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
    hits = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_SIGNAL and click])
    misses = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_SIGNAL and not click])
    false_alarms = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_NOISE and click])
    correct_rejections = len([letter for letter, click in zip(letters, clicked) if letter==LETTER_NOISE and not click])
    result["letters"] = VALUES_SEPARATOR.join(letters)
    result["clicked"] = VALUES_SEPARATOR.join(str(int(v)) for v in clicked)
    result["delays"] = VALUES_SEPARATOR.join(str(round(delay, 4)) for delay in delays)
    result["cc_hit_avg_click_delay"] = sum([delay if (letter==LETTER_SIGNAL and click) else 0 for letter, click, delay in zip(letters, clicked, delays)]) / (hits or 1)
    result["cc_false_alarm_avg_click_delay"] = sum([delay if (letter==LETTER_NOISE and click) else 0 for letter, click, delay in zip(letters, clicked, delays)]) / (false_alarms or 1)
    result.update(SDT(hits, misses, false_alarms, correct_rejections))
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
            response["time_spent"] = response["time_stop"] - response["time_start"] 
            cookie_obj["response"] = response
            req_response = make_response(redirect(url_for(f"tasks.{BASE}.done")))
            set_cookie_obj(req_response, BASE, cookie_obj)
            return req_response

    req_response = make_response(render_template(f"tasks/{BASE}.html", callback_url=url_for(f"tasks.{BASE}.check"), items=ITEMS, start_delays=START_DELAYS, time_show=TIME_SHOW, time_wait=TIME_WAIT, time_hide=TIME_HIDE, delay_missed=DELAY_MISSED, letter_signal_bonus=LETTER_SIGNAL_BONUS, letter_noise_bonus=LETTER_NOISE_BONUS))
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