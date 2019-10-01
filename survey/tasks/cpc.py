import math
import datetime
import time
import pandas as pd
import os
import random

import numpy as np
from scipy import stats
from flask import (
    Blueprint, render_template, session, url_for, redirect, request, flash
)

from survey._app import csrf_protect, app, CODE_DIR
from survey.tasks.task import handle_task_done, handle_task_index


#### helpers
BASE = os.path.splitext(os.path.split(__file__)[1])[0]
bp = Blueprint("tasks.cpc", __name__)

def CPC18_getDist(H, pH, L, lot_shape, lot_num):
    # Extract true full distributions of an option in CPC18
    #   input is high outcome (H: int), its probability (pH: double), low outcome
    #   (L: int), the shape of the lottery ('-'/'Symm'/'L-skew'/'R-skew' only), and
    #   the number of outcomes in the lottery (lot_num: int)
    #   output is a matrix (numpy matrix) with first column a list of outcomes (sorted
    #   ascending) and the second column their respective probabilities.

    if lot_shape == '-':
        if pH == 1:
            dist = np.array([H, pH])
            dist.shape = (1, 2)
        else:
            dist = np.array([[L, 1-pH], [H, pH]])

    else:  # H is multi outcome
        # compute H distribution
        high_dist = np.zeros(shape=(lot_num, 2))
        if lot_shape == 'Symm':
            k = lot_num - 1
            for i in range(0, lot_num):
                high_dist[i, 0] = H - k / 2 + i
                high_dist[i, 1] = pH * stats.binom.pmf(i, k, 0.5)

        elif (lot_shape == 'R-skew') or (lot_shape == 'L-skew'):
            if lot_shape == 'R-skew':
                c = -1 - lot_num
                dist_sign = 1
            else:
                c = 1 + lot_num
                dist_sign = -1
            for i in range(1, lot_num+1):
                high_dist[i - 1, 0] = H + c + dist_sign * pow(2, i)
                high_dist[i - 1, 1] = pH / pow(2, i)

            high_dist[lot_num - 1, 1] = high_dist[lot_num - 1, 1] * 2

        # incorporate L into the distribution
        dist = high_dist
        locb = np.where(high_dist[:, 0] == L)
        if np.all(locb):
            dist[locb, 1] = dist[locb, 1] + (1-pH)
        elif pH < 1:
            dist = np.vstack((dist, [L, 1-pH]))

    if dist[:, 1].sum() < 1:
        if dist.shape[0] < lot_num:
            dist = np.vstack((dist, [L, 1-pH]))
        else:
            dist[-1][0] = L
            dist[-1][1] = 1 - dist[:-1, 1].sum()
    dist = dist[np.argsort(dist[:, 0])]
    return dist

def generate_problems(filename):
    df = pd.read_csv(filename)
    problems = []
    distributions = {}
    for idx in range(df.shape[0]):
        row = df.iloc[idx]
        problem = {}
        Ha = row['Ha']
        pHa = row['pHa']
        La = row['La']
        LotShapeA = row['LotShapeA']
        LotNumA = row['LotNumA']
        Hb = row['Hb']
        pHb = row['pHb']
        Lb = row['Lb']
        LotShapeB = row['LotShapeB']
        LotNumB = row['LotNumB']
        Amb = row['Amb']
        Corr = row['Corr']
        distA = CPC18_getDist(Ha, pHa, La, LotShapeA, LotNumA)
        distB = CPC18_getDist(Hb, pHb, Lb, LotShapeB, LotNumB)
        problem["optionsA"] = []    #[f"{row['M']} (with probability {pHa}"]
        problem["optionsB"] = []
        multiplicator = 1
        for n in range(distA.shape[0]):
            val = math.ceil(distA[n][0] * multiplicator)
            problem["optionsA"].append(f"{val} USD cents with probability {distA[n][1]:.3f}")
        for n in range(distB.shape[0]):
            val = math.ceil(distB[n][0] * multiplicator)
            problem["optionsB"].append(f"{val} USD cents with probability {distB[n][1]:.3f}")
        problems.append(problem)
        distributions[f"q{idx+1}"] = ({"distA": distA, "distB": distB})
    return problems, distributions


PROBLEMS, DISTRIBUTIONS = generate_problems(os.path.join(CODE_DIR, "data/t00/ug2cpc.csv"))
FIELDS = {k for k in DISTRIBUTIONS}
FEATURES = set(f"cpc_{k}" for k in FIELDS) | {
    "cpc_expected_value",   #expected value of the user's selected lotteries
    "cpc_expected_value_max",   #expected value of the user's selected lotteries' highest bonus
    "cpc_expected_value_min",   #expected value of the user's selected lotteries' lowest bonus
    "cpc_time_spent",       #time spent by the user on this task
}

max_lotteries = ([max(item["distA"][:, 0].max(), item["distB"][:,0].max()) for item in DISTRIBUTIONS.values()])
MAX_BONUS = sum(max_lotteries) / len(max_lotteries)
def validate_response(response):
    for key in FIELDS:
        if key not in response:
            return False
    return True

def response_to_bonus(response):
    #0: A, 1: B
    tmp_bonus = 0
    for k in FIELDS:
        choice = response[k]
        if choice == "A":
            dist = DISTRIBUTIONS[k]["distA"]
        else:
            dist = DISTRIBUTIONS[k]["distB"]
        cum_p = np.cumsum(dist[:, 1])
        p = np.random.random()
        gain = None
        for idx in range(dist.shape[0]):
            if p >= cum_p[idx]:
                gain = dist[idx][0]
                break
        if gain is None:
            gain = dist[-1][0]
        tmp_bonus += gain
    bonus = tmp_bonus / len(FIELDS)
    return int(bonus)

def response_to_expected_values(response):
    #0: A, 1: B
    tmp_expected_value = 0.0
    tmp_expected_value_max = 0.0
    tmp_expected_value_min = 0.0
    result = dict()
    for k in FIELDS:
        choice = response[k]
        if choice == "A":
            dist = DISTRIBUTIONS[k]["distA"]
        else:
            dist = DISTRIBUTIONS[k]["distB"]
        #cum_p = np.cumsum(dist[:, 1])
        dist *= 1.0
        dist_p = dist[:, 1]
        dist_gain = dist[:, 0]
        product = dist_p * dist_gain
        tmp_expected_value_max += product[-1]
        tmp_expected_value_min += product[0]
        tmp_expected_value += np.mean(product)
        result[f"{BASE}_{k}"] = round(np.mean(product), 4)
    result.update({
        "cpc_expected_value": round(tmp_expected_value / len(FIELDS), 4),
        "cpc_expected_value_max": round(tmp_expected_value_max / len(FIELDS), 4),
        "cpc_expected_value_min": round(tmp_expected_value_min / len(FIELDS), 4),
    })
    return result

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
    result.update(response_to_expected_values(response))
    result["cpc_time_spent"] = result["time_spent"]
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result
############

@csrf_protect.exempt
@bp.route("/cpc/", methods=["GET", "POST"])
def index():
    return handle_task_index("cpc", validate_response=validate_response, template_kwargs={"problems":PROBLEMS})


@bp.route("/cpc/done")
def done():
    return handle_task_done("cpc", numeric_fields=None, unique_fields=["worker_id"], response_to_result_func=response_to_result, response_to_bonus=response_to_bonus)