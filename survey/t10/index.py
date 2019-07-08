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

from survey.figure_eight import FigureEight

from core.models.metrics import MAX_GAIN
from survey._app import app, csrf_protect
from survey.admin import get_job_config
from survey.db import get_db, table_exists
from survey.figure_eight import RowState
from survey.utils import get_table, increase_worker_bonus
from .prop import BASE as prop_BASE, finalize_round, JUDGING_TIMEOUT_SEC, LAST_MODIFIED_KEY, STATUS_KEY
from .resp import BASE as resp_BASE, finalize_resp


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


def _process_judgments(signal, payload, job_id, job_config):
    """
    :param signal: (str)
    :param payload: (dict)
    :param job_id: (int|str)
    :param job_config: (JobConfig)
    """
    error_happened = False
    with app.app_context():
        try:
            # app.logger.info(f"Started part-payments..., with signal: {signal}")
            if signal == "new_judgments":
                judgments_count = payload['judgments_count']
                fig8 = FigureEight(job_id, job_config["api_key"])
                for idx in range(judgments_count):
                    # try:
                    if True:
                        con = get_db("RESULT")
                        worker_judgment = payload['results']['judgments'][idx]
                        worker_id = worker_judgment["worker_id"]
                        #TODO: Not paying any bonus yet
                        #TODO: may compute the next level here
                        is_responder = False
                        is_proposer = False
                        table_resp = get_table(resp_BASE, job_id, treatment=TREATMENT)
                        table_prop = get_table(prop_BASE, job_id, treatment=TREATMENT)
                        with con:
                            if table_exists(con, table_resp):
                                res = con.execute(f"SELECT * from {table_resp} WHERE job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
                                if res:
                                    is_responder = True
                            if not is_responder and table_exists(con, table_prop):
                                res = con.execute(f"SELECT * from {table_prop} WHERE job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
                                if res:
                                    is_responder= True

                        if is_responder:
                            finalize_resp(job_id=job_id, worker_id=worker_id)
                        elif is_proposer:
                            finalize_round(job_id=job_id, prop_worker_id=worker_id)

                        # worker_bonus = get_worker_bonus(con, job_id, worker_id)
                        #pay_worker_bonus(con, job_id, worker_id, worker_bonus, fig8)
                    # except Exception as err:
                    #     if not error_happened:
                    #         app.logger.error(f"Error: {err}")
                    #         error_happened = True
            elif signal == "unit_complete":
                #TODO: may process the whole unit here
                pass
        except Exception as err:
            app.log_exception(err)
        app.logger.info("Done dispatching tasks..., with signal: %s ^_^ " % signal)

@csrf_protect.exempt
@bp.route("/webhook/", methods=["GET", "POST"])
def webhook():
    form = request.form.to_dict()
    signal = form['signal']
    if signal in {'unit_complete', 'new_judgments'}:
        # app.logger.info(f"SIGNAL: {signal}")
        payload_raw = form['payload']
        signature = form['signature']
        payload = json.loads(payload_raw)
        job_id = payload['job_id']
        
        job_config = get_job_config(get_db("DB"), job_id)
        payload_ext = payload_raw + job_config["api_key"]
        verif_signature = hashlib.sha1(payload_ext.encode()).hexdigest()
        if signature == verif_signature:
            args = (signal, payload, job_id, job_config)
            app.config["THREADS_POOL"].starmap_async(_process_judgments, [args])
    return Response(status=200)
