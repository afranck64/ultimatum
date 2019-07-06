import json
import os
import warnings
import random
import string
import csv
import time
import datetime
import io
import hashlib

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify, Response
)

import random

from notebooks.models.metrics import MAX_GAIN
from survey._app import app
from survey.db import get_db, table_exists
from survey.figure_eight import RowState
from survey.utils import get_table
from .prop import BASE as prop_BASE, JUDGING_TIMEOUT_SEC, LAST_MODIFIED_KEY, STATUS_KEY
from .resp import BASE as resp_BASE


#### const
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}", __name__)
############



@bp.route("/")
def index():
    job_id = request.args.get("job_id", "na")
    worker_id = request.args.get("worker_id", "na")
    resp_table = get_table(base=resp_BASE, job_id=job_id, treatment=TREATMENT)
    prop_table = get_table(base=prop_BASE, job_id=job_id, treatment=TREATMENT)

    con = get_db("DATA")
    nb_resp = 0
    nb_prop = 0
    nb_prop_open = 0
    if table_exists(con, resp_table):
        with con:
            tmp = con.execute(f"SELECT COUNT(*) as count from {resp_table}").fetchone()
            if tmp:
                nb_resp = tmp["count"]
    if table_exists(con, prop_table):
        with con:
            judging_timeout = time.time() - JUDGING_TIMEOUT_SEC
            tmp = con.execute(f"SELECT COUNT(*) as count from {prop_table} where {STATUS_KEY}=? OR ({STATUS_KEY}=? and {LAST_MODIFIED_KEY}>?)", (RowState.JUDGEABLE, RowState.JUDGING, judging_timeout)).fetchone()
            if tmp:
                nb_prop_open = tmp["count"]
    if table_exists(con, prop_table):
        with con:
            tmp = con.execute(f"SELECT COUNT(*) as count from {prop_table}").fetchone()
            if tmp:
                nb_prop = tmp["count"]
    
    #TODO: if nb_resp >= expected row/2, should only take props
    if nb_prop_open > 0:
        is_proposer = True
    else:
        if nb_resp > nb_prop:
            is_proposer = True
        else:
            is_proposer = False


    if is_proposer:
        return redirect(url_for(f"{TREATMENT}.prop.index", job_id=job_id, worker_id=worker_id))
    else:
        return redirect(url_for(f"{TREATMENT}.resp.index", job_id=job_id, worker_id=worker_id))



@bp.route("/webhook", methods=["GET", "POST"])
def webhook():
    app.logger.info(f"{request.form}")
    return "webhook"


def finalize_resp_row():
    # TODO: At this point, all features have been gathered
    # generate prediction for the prop row
    resp_worker_id = "na"
    prop_worker_id = "na"
    job_id = "na"
    con = get_db("RESULT")
    resp_bonus = 0
    prop_bonus = 0
    with con:
        table = get_table("resp", job_id, treatment=TREATMENT)
        res = con.execute(f"SELECT offer, min_offer, resp_worker_id from {table} WHERE resp_worker_id=? and prop_worker_id=?", (resp_worker_id, prop_worker_id)).fetchone()
    offer, min_offer = res["offer"], res["min_offer"]
    resp_worker_id = res["resp_worker_id"]
    for task in ["cg", "crt", "eff", "hexaco", "risk"]:
        table = get_table(task, job_id)
        with con:
            res = con.execute(f"SELECT worker_bonus FROM {table} WHERE worker_id=?", (resp_worker_id,)).fetchone()
            resp_bonus += res["worker_bonus"]
    if offer >= min_offer:
        resp_bonus += offer
        prop_bonus += (MAX_GAIN - min_offer)
    print(resp_bonus, prop_bonus)