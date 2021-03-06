import os
import time
import unittest
from unittest import mock
import requests
import random
import time
import uuid
import json
import hashlib

from flask import jsonify
# from httmock import urlmatch, HTTMock, response

from core.models.metrics import MAX_GAIN
from survey._app import TREATMENTS_MODEL_REFS, app, TREATMENTS_AUTO_DSS
from survey.admin import get_job_config
from survey.db import get_db
from survey.txx.prop import insert_row
from survey.utils import get_worker_bonus, get_worker_paid_bonus, get_total_worker_bonus, WORKER_CODE_DROPPED, get_table, get_secret_key_hash

from survey.globals import AI_FEEDBACK_SCALAS, AI_FEEDBACK_ACCURACY_SCALAS, AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS
from survey.tasks.helpers import process_tasks, generate_worker_id


AI_FEEDBACK_SCALAS_KEYS = list(AI_FEEDBACK_SCALAS)
AI_FEEDBACK_ACCURACY_SCALAS_KEYS = list(AI_FEEDBACK_ACCURACY_SCALAS)
AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS_KEYS = list(AI_FEEDBACK_ACCURACY_RESPONDER_SCALAS)

WEBHOOK_DELAY = 0.25

TASK_REPETITION = 8

OFFER = MAX_GAIN//2
MIN_OFFER = MAX_GAIN//2
SURVEY_MAIN_TASK_CODE_FIELD = "code_resp_prop"
SURVEY_CONTROL_FIELDS = {"proposer", "responder", "proposer_responder", "money_division"}
SURVEY_CHOICE_FIELDS = {"age", "gender", "income", "ethnicity", "test"}



def _process_resp(client, treatment, job_id="test", worker_id=None, min_offer=MIN_OFFER, clear_session=True, path=None, dss_available=False, resp_feedback_fields=None):
    app.logger.error("_process_resp")
    MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    dss_available = bool(app.config.get(MODEL_KEY))
    dss_available = dss_available and treatment[:3] not in {"t00", "t10", "t11"} #Treatments where the responder isn't informed about the DSS
    if worker_id is None:
        worker_id = generate_worker_id()
    if path is None:
        path = f"/{treatment}/resp/?job_id={job_id}&worker_id={worker_id}"
    if resp_feedback_fields is None:
        resp_feedback_fields = [
                "feedback_alternative",
                "feedback_fairness",
                "feedback_accuracy"
        ]
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path, follow_redirects=True)

        data={
            "min_offer": min_offer,
        }
        res = client.post(path, data=data, follow_redirects=True)
        if dss_available:
            path_dss = f"/{treatment}/resp_dss/?job_id={job_id}&worker_id={worker_id}"
            client.get(path_dss, follow_redirects=True)
            data_dss={
                "min_offer": min_offer,
            }
            client.post(path_dss, data=data_dss, follow_redirects=True)
            data_feedback = {field:random.choice(AI_FEEDBACK_SCALAS_KEYS) for field in resp_feedback_fields}
            path_feedback = f"/{treatment}/resp_feedback/?job_id={job_id}&worker_id={worker_id}"
            res = client.post(path_feedback, data=data_feedback, follow_redirects=True)

        return res

def _process_resp_tasks(client, treatment, job_id="test", worker_id=None, min_offer=MIN_OFFER, bonus_mode="random", clear_session=True, synchron=True, path=None, resp_feedback_fields=None):
    app.logger.debug("_process_resp_tasks")
    if worker_id is None:
        worker_id = generate_worker_id("resp")
    process_tasks(client, job_id=job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    res = _process_resp(client, treatment, job_id=job_id, worker_id=worker_id, min_offer=min_offer, clear_session=clear_session, path=path, resp_feedback_fields=resp_feedback_fields)
    if synchron:
        emit_webhook(client, url=f"/{treatment}/webhook/?synchron=1", treatment=treatment, job_id=job_id, worker_id=worker_id)
    else:
        emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, job_id=job_id, worker_id=worker_id)
    return res


def _process_prop(client, treatment, job_id="test", worker_id=None, offer=OFFER, clear_session=True, response_available=False, path=None, auto_finalize=False, nb_dss_check=None):
    app.logger.debug("_process_prop")
    MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    dss_available = bool(app.config.get(MODEL_KEY))
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if path is None:
        path = f"/{treatment}/prop/?job_id={job_id}&worker_id={worker_id}"
    path_dss = f"/{treatment}/prop_dss/?job_id={job_id}&worker_id={worker_id}"
    path_feedback = f"/{treatment}/prop_feedback/?job_id={job_id}&worker_id={worker_id}"
    path_check = f"{treatment}/prop/check/?secret_key_hash={get_secret_key_hash()}"
    if auto_finalize is True:
        path += "&auto_finalize=1"
        path_dss += "&auto_finalize=1"
        path_feedback += "&auto_finalize=1"
    if not response_available:
        _process_resp_tasks(client, treatment, job_id=job_id)
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path, follow_redirects=True)
        app.logger.debug(f"Path: {path}, Path2: {path_dss}, Path-check: {path_check}")
        if dss_available:
            # gather the "optimal" offer from the dss
            if offer == "auto":
                info = client.get(path_check, follow_redirects=True)
                try:
                    offer = json.loads(info.data)["ai_offer"]
                except Exception as err:
                    app.logger.error(f"couldn't access to the ai_offer: - {info.data}")
                    app.log_exception(err)
                    offer = -1
            data = {"offer": offer}
            res = client.post(path, data=data, follow_redirects=True)

            data_dss = {
                "offer_dss": offer,
            }
                  

            # if nb_dss_check is None:
            #     res = client.post(path_dss, data=data_dss, follow_redirects=True)
            if nb_dss_check is not None:
                client.get(path_dss, follow_redirects=True)
                client.get(path_check)
                for _ in range(nb_dss_check):
                    client.get(f"{path_check}?offer={random.choice(list(range(0, MAX_GAIN+1, 5)))}")

            res = client.post(path_dss, data=data_dss, follow_redirects=True)

            data_feedback = {
                "feedback_alternative": random.choice(AI_FEEDBACK_SCALAS_KEYS),
                "feedback_understanding": random.choice(AI_FEEDBACK_SCALAS_KEYS),
                "feedback_explanation":  random.choice(AI_FEEDBACK_SCALAS_KEYS),
                "feedback_accuracy": random.choice(AI_FEEDBACK_ACCURACY_SCALAS_KEYS),
            } 
            res = client.post(path_feedback, data=data_feedback, follow_redirects=True)
        else:
            if offer=="auto":
                offer = MAX_GAIN // 2
            res = client.post(path, data={"offer":offer}, follow_redirects=True)
        return res


def _process_prop_round(client, treatment, job_id="test", worker_id=None, offer=OFFER, clear_session=True, response_available=False, synchron=False, path=None, finalize_round=True):
    app.logger.debug("_process_prop_round")
    if client is None:
        client = app.test_client()
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if synchron:
        webhook_url = f"/{treatment}/webhook/?synchron=1"
    else:
        webhook_url = f"/{treatment}/webhook/"
        
    if not response_available:
        _process_resp_tasks(client, treatment=treatment, job_id=job_id, worker_id=None, min_offer=MIN_OFFER, bonus_mode="full")
    res = _process_prop(client, treatment=treatment, job_id=job_id, worker_id=worker_id, offer=offer, response_available=True, path=path, nb_dss_check=1)
    time.sleep(WEBHOOK_DELAY)
    if finalize_round:
        emit_webhook(client, url=webhook_url, treatment=treatment, job_id=job_id, worker_id=worker_id)
    return res


def finalize_resp(job_id, worker_id, treatment):
    app.logger.debug("finalize_resp")
    table = get_table(base="resp", job_id=job_id, schema="result", treatment=treatment)
    with get_db("RESULT") as con:
        res = con.execute(f"SELECT * from {table} where job_id=? and worker_id=?", (job_id, worker_id)).fetchone()
        if res:
            resp_result = dict(res)
            insert_row(job_id, resp_result, treatment)
        else:
            app.logger.warning(f"finalize_resp: worker_id {worker_id} not found - job_id: {job_id}")

    app.logger.debug(f"Treatment: {treatment}, auto_dss: {TREATMENTS_AUTO_DSS}")
    if treatment.upper() in TREATMENTS_AUTO_DSS:
        time.sleep(WEBHOOK_DELAY)
        worker_id = f"auto_prop_{uuid.uuid4()}"
        args = [None, treatment, job_id, worker_id, "auto", True, True, True, None]
        app.logger.debug(f"auto-proposal! {args}")
        # client = app.test_client()
        app.config["THREADS_POOL"].starmap_async(_process_prop_round, [args])
        # _process_prop_round(client=None, treatment=treatment, job_id=job_id, worker_id=worker_id, offer="auto", clear_session=True, response_available=True, synchron=True, path=None)


## figure-eight webhook template
webhook_data_template =  {
    "signal": "new_judgments",
    "payload":{
        "id":2329205222,
        "data":{
            "ai_offer": f"{MAX_GAIN//2}",
            "min_offer":f"{MAX_GAIN//2}"
        },
        "judgments_count":1,
        "state":"finalized",
        "agreement":1.0,
        "missed_count":0,
        "gold_pool":None,
        "created_at":"2019-06-11T19:18:19+00:00",
        "updated_at":"2019-06-16T00:58:08+00:00",
        "job_id":1392288,
        "results": {
            "judgments":[
                {
                    "id":4900876098,
                    "created_at":"2019-06-16T00:57:58+00:00",
                    "started_at":"2019-06-16T00:56:09+00:00",
                    "acknowledged_at":None,
                    "external_type":"cf_internal",
                    "golden":False,
                    "missed":None,
                    "rejected":None,
                    "tainted":False,
                    "country":"GBR",
                    "region":"",
                    "city":"",
                    "unit_id":2329205222,
                    "job_id":1392288,
                    "worker_id":45314141,
                    "trust":1.0,
                    "worker_trust":1.0,
                    "unit_state":"finalized",
                    "data":{
                        "proposer":["correct"],
                        "responder":["correct"],
                        "prop_and_resp":["correct"],
                        "ai":["correct"],
                        "comp_code":"lAT2JV2QtTkEnH5A4syJ6N4tcNZod1O6",
                        "feedback":"Thank you for everything. ^_^",
                        "id_user_agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/74.0.3729.169 Chrome/74.0.3729.169 Safari/537.36",
                        "_clicks":["http://tube.ddns.net/ultimatum/hhi_prop_adm?job_id=1392288&worker_id=45314141&unit_id=na"]
                    },
                    "unit_data":{
                        "ai_offer":f"{MAX_GAIN//2}",
                        "min_offer":f"{MAX_GAIN//2}"
                    }
                }
            ],
            "proposer":{
                "agg":"correct",
                "confidence":1.0
            },
            "responder":{
                "agg":"correct",
                "confidence":1.0
            },
            "prop_and_resp":{
                "agg":"correct",
                "confidence":1.0
            },
            "ai":{
                "agg":"correct",
                "confidence":1.0
            }
        }
    },
    "signature": ""
}

def emit_webhook(client, url, job_id="test", worker_id=None, signal="new_judgments", unit_state="finalized", treatment="t10", by_get=True):
    """
    :param client:
    :param url: (str) relative path to target api
    :param job_id: (str)
    :param worker_id: (str)
    :param signal: (new_judgments|unit_complete)
    :param unit_state: (finalized|new|judging|judgeable?)
    :param by_get: (True|False) simulate a setup were each user triggers the webhook using a get request
    """
    app.logger.debug(f"emit_webhook: job_id: {job_id}, worker_id: {worker_id}, treatment: {treatment}")
    proceed = False
    max_retries = 5
    with app.app_context():
        while not proceed and max_retries>0:
            table_resp = get_table("resp", job_id, "result", treatment=treatment)
            table_prop = get_table("prop", job_id, "result", treatment=treatment)
            app.logger.debug("Waiting for the db...")
            
            with get_db() as con:
                if con.execute(f"SELECT * FROM {table_resp} where worker_id=?", (worker_id,)).fetchone():
                    proceed = True
                elif con.execute(f"SELECT * FROM {table_prop} where worker_id=?", (worker_id,)).fetchone():
                    proceed = True
            con = None
            time.sleep(0.01)
            max_retries -= 1
        data_dict = dict(webhook_data_template)
        data_dict["signal"] = signal
        data_dict["payload"]["job_id"] = job_id
        data_dict["payload"]["results"]["judgments"][0]["job_id"] = job_id
        data_dict["payload"]["results"]["judgments"][0]["worker_id"] = worker_id
        data_dict["payload"]["results"]["judgments"][0]["unit_state"] = unit_state
        with get_db() as con:
            job_config = get_job_config(con, job_id)
        payload = json.dumps(data_dict["payload"])
        payload_ext = payload + str(job_config["api_key"])
        signature = hashlib.sha1(payload_ext.encode()).hexdigest()
        data = {
            "signal": signal,
            "payload": payload,
            "signature": signature
        }
        if by_get:
            # An empty form is submitted when triggering the webhook by click
            data = {}
            if "?" in url:
                url += f"&job_id={job_id}&worker_id={worker_id}"
            else:
                url += f"?job_id={job_id}&worker_id={worker_id}"
            res = client.get(url, follow_redirects=True).status
        else:
            res = client.post(url, data=data, follow_redirects=True).status
        return res
