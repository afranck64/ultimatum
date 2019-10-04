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
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response
)

from survey.figure_eight import FigureEight

from core.models.metrics import MAX_GAIN
from survey._app import app, csrf_protect
from survey.admin import get_job_config
from survey.db import get_db, table_exists
from survey.figure_eight import RowState
from survey.utils import get_table, increase_worker_bonus, pay_worker_bonus, get_resp_worker_id
from .prop import BASE as prop_BASE, finalize_round, JUDGING_TIMEOUT_SEC, LAST_MODIFIED_KEY, STATUS_KEY, WORKER_KEY
from .resp import BASE as resp_BASE

from survey.txx.helpers import finalize_resp 

BASE = "txx"

NEXT_IS_RESPONDER = 0
NEXT_IS_PROPOSER = 1
NEXT_IS_PROPOSER_WAITING = 2
def check_is_proposer_next(job_id, worker_id, treatment, max_judgments=None):
    app.logger.debug("check_is_proposer_next")
    resp_table = get_table(resp_BASE, job_id=job_id, schema="result", treatment=treatment)
    prop_table = get_table(prop_BASE, job_id=job_id, schema="result", treatment=treatment)
    prop_table_data = get_table(prop_BASE, job_id=job_id, schema="data", treatment=treatment)
    job_config = get_job_config(get_db("DB"), job_id)

    con = get_db("DATA")
    nb_resp = 0
    nb_prop = 0
    nb_prop_open = 0
    if table_exists(con, resp_table):
        with con:
            tmp = con.execute(f"SELECT COUNT(*) as count from {resp_table} where job_id=?", (job_id, )).fetchone()
            if tmp:
                nb_resp = tmp["count"]
    if table_exists(con, prop_table_data):
        with con:
            judging_timeout = time.time() - JUDGING_TIMEOUT_SEC
            tmp = con.execute(f"SELECT COUNT(*) as count from {prop_table_data} where job_id=? and ({STATUS_KEY}=? OR ({STATUS_KEY}=? and {LAST_MODIFIED_KEY}<?) OR ({WORKER_KEY}=?))", (job_id, RowState.JUDGEABLE, RowState.JUDGING, judging_timeout, worker_id)).fetchone()
            if tmp:
                nb_prop_open = tmp["count"]
    if table_exists(con, prop_table):
        with con:
            tmp = con.execute(f"SELECT COUNT(*) as count from {prop_table} where job_id=?", (job_id, )).fetchone()
            if tmp:
                nb_prop = tmp["count"]
    
    #TODO: if nb_resp >= expected row/2, should only take props
    if max_judgments is None or max_judgments==0:
        max_judgments = job_config["expected_judgments"]
    if max_judgments > 0:
        if (max_judgments // 2) <= nb_resp and (max_judgments // 2) > nb_prop:
            if nb_prop_open > 0:
                is_proposer = NEXT_IS_PROPOSER
            else:
                is_proposer = NEXT_IS_PROPOSER_WAITING
        elif nb_prop_open > 0:
            is_proposer = NEXT_IS_PROPOSER
        else:
            is_proposer = NEXT_IS_RESPONDER
    elif nb_prop_open > 0:
        is_proposer = NEXT_IS_PROPOSER
    else:
        is_proposer = NEXT_IS_RESPONDER
    app.logger.debug(f"max_judgments: {max_judgments}, nb_prop: {nb_prop}, nb_resp: {nb_resp}, nb_prop_open: {nb_prop_open}, is_proposer: {is_proposer}")
    return is_proposer

def handle_index(treatment):
    job_id = request.args.get("job_id", "na")
    worker_id = request.args.get("worker_id", "na")
    max_judgments = None
    try:
        max_judgments = int(request.args.get("max_judgments", "0"))
    except ValueError:
        pass
    auto_finalize = request.args.get("auto_finalize")
    app.logger.debug(f"handle_index: job_id: {job_id}, worker_id: {worker_id}")
    is_proposer = check_is_proposer_next(job_id, worker_id, treatment, max_judgments=max_judgments)

    table_all = get_table(BASE, "all", schema=None)
    con = get_db()
    if table_exists(con, table_all):
        with con:
            res = con.execute(f"SELECT * from {table_all} WHERE worker_id=?", (worker_id,)).fetchone()
            if res:
                flash(f"You already took part on this survey. Thank you for your participation")
                return render_template("error.html")
    

    if is_proposer:
        return redirect(url_for(f"{treatment}.prop.index", **request.args))
    else:
        return redirect(url_for(f"{treatment}.resp.index", **request.args))


def _process_judgments(signal, payload, job_id, job_config, treatment, auto_finalize=False):
    """
    :param signal: (str)
    :param payload: (dict)
    :param job_id: (int|str)
    :param job_config: (JobConfig)
    :param auto_finalize (bool)
    """
    error_happened = False
    app.logger.debug(f"_process_judgments: {signal}, job_id: {job_id}, auto_finalize: {auto_finalize}")
    with app.app_context():
        try:
            if signal == "new_judgments":
                judgments_count = payload['judgments_count']
                fig8 = FigureEight(job_id, job_config["api_key"])
                for idx in range(judgments_count):
                    if auto_finalize == True:
                        try:
                            con = get_db("RESULT")
                            worker_judgment = payload['results']['judgments'][idx]
                            worker_id = worker_judgment["worker_id"]
                            app.logger.debug(f"_process_judgments: {signal}, job_id: {job_id}, worker_id: {worker_id}")
                            is_responder = False
                            is_proposer = False
                            table_resp = get_table(resp_BASE, job_id=job_id, schema="result", treatment=treatment)
                            table_prop = get_table(prop_BASE, job_id=job_id, schema="result", treatment=treatment)
                            with con:
                                if table_exists(con, table_resp):
                                    res = con.execute(f"SELECT * from {table_resp} WHERE job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
                                    if res:
                                        is_responder = True
                                if not is_responder and table_exists(con, table_prop):
                                    res = con.execute(f"SELECT * from {table_prop} WHERE job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
                                    if res:
                                        is_proposer= True
                            if is_responder:
                                finalize_resp(job_id=job_id, worker_id=worker_id, treatment=treatment)
                            elif is_proposer:
                                finalize_round(job_id=job_id, prop_worker_id=worker_id, treatment=treatment)
                            else:
                                app.logger.error(f"Error: unknown worker_id: {worker_id} for job_id: {job_id}")
                        except Exception as err:
                            if not error_happened:
                                app.log_exception(err)
                                error_happened = True
                    else:
                        worker_judgment = payload['results']['judgments'][idx]
                        worker_id = worker_judgment["worker_id"]
                        pay_worker_bonus(job_id, worker_id, fig8)

            elif signal == "unit_complete":
                judgments_count = payload['judgments_count']
                fig8 = FigureEight(job_id, job_config["api_key"])
                for idx in range(judgments_count):
                    if auto_finalize == False:
                        worker_judgment = payload['results']['judgments'][idx]
                        worker_id = worker_judgment["worker_id"]
                        # PAY_WORKER won't pay someone twice.
                        pay_worker_bonus(job_id, worker_id, fig8)

                #TODO: may process the whole unit here
                pass
        except Exception as err:
            app.log_exception(err)
    app.logger.debug(f"_process_judgments: {signal}, job_id: {job_id} - done")



def handle_webhook(treatment):
    """
    request.args:
        - job_id: job's id
        - worker_id: worker's id
        - synchron: Directly process data without puting in a queue for another thread

    """
    app.logger.debug("handle_webhook")
    sync_process = False
    auto_finalize = False
    sync_process = request.args.get("synchron", False)
    form = request.form.to_dict()
    if "signal" in form:
        signal = form['signal']
        if signal in {'unit_complete', 'new_judgments'}:
            payload_raw = form['payload']
            signature = form['signature']
            payload = json.loads(payload_raw)
            job_id = payload['job_id']
            
            job_config = get_job_config(get_db("DB"), job_id)
            payload_ext = payload_raw + job_config["api_key"]
            verif_signature = hashlib.sha1(payload_ext.encode()).hexdigest()
            if signature == verif_signature:
                args = (signal, payload, job_id, job_config, treatment, auto_finalize)
                if sync_process:
                    _process_judgments(*args)
                else:
                    app.config["THREADS_POOL"].starmap_async(_process_judgments, [args])
    else:
        job_id = request.args.get("job_id")
        worker_id = request.args.get("worker_id")
        job_config = get_job_config(get_db("DB"), job_id)
        auto_finalize = True
        payload = {
            "judgments_count": 1,
            "job_id": job_id,
            "results": {
                "judgments": [
                        {
                        "job_id": job_id,
                        "worker_id": worker_id
                    }
                ]
            }
        }
        args = ("new_judgments", payload, job_id, job_config, treatment, auto_finalize)
        if sync_process:
            _process_judgments(*args)
        else:
            app.config["THREADS_POOL"].starmap_async(_process_judgments, [args])
        # flash("You may close this tab now and continue with the survey.")
        # return render_template("info.html", job_id=job_id, webhook=True)
    return Response(status=200)
