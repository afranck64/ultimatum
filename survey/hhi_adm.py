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

from survey._app import app
from survey.db import get_db, table_exists
from survey.hhi_prop_adm import BASE as hhi_prop_adm_BASE, JUDGING_TIMEOUT_SEC, LAST_CHANGE_KEY, STATUS_KEY
from survey.hhi_resp_adm import BASE as hhi_resp_adm_BASE
from survey.figure_eight import RowState
from survey.utils import get_table


#### const
bp = Blueprint("hhi_adm", __name__)
############



@bp.route("/hhi_adm/")
def index():
    is_proposer = (random.random() > 0.5)
    job_id = request.args.get("job_id", "na")
    worker_id = request.args.get("worker_id", "na")
    resp_table = get_table(hhi_resp_adm_BASE, job_id)
    prop_table = get_table(hhi_prop_adm_BASE, job_id)

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
            tmp = con.execute(f"SELECT COUNT(*) as count from {prop_table} where {STATUS_KEY}=? OR ({STATUS_KEY}=? and {LAST_CHANGE_KEY}>?)", (RowState.JUDGEABLE, RowState.JUDGING, judging_timeout)).fetchone()
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
        return redirect(url_for("hhi_prop_adm.index", job_id=job_id, worker_id=worker_id))
    else:
        return redirect(url_for("hhi_resp_adm.index", job_id=job_id, worker_id=worker_id))



@bp.route("/hhi_adm/webhook", methods=["GET", "POST"])
def webhook():
    app.logger.info(f"{request.form}")