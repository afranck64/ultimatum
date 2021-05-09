# The decision support system plays in place of the proposer!

import os
import time
import unittest
from unittest import mock
import requests
import random
from flask import jsonify
from httmock import urlmatch, HTTMock, response

from core.models.metrics import MAX_GAIN
from survey._app import TREATMENTS_MODEL_REFS
from survey import tasks
from survey.db import get_db
from survey.txx.survey import MainForm
from survey.utils import get_worker_bonus, get_worker_paid_bonus, get_total_worker_bonus, WORKER_CODE_DROPPED, WORKER_KEY, get_table, is_worker_available

from survey.tasks.helpers import process_tasks

from survey.txx.helpers import _process_prop, _process_prop_round, _process_resp, _process_resp_tasks

from tests.test_survey import app, client, get_client, generate_worker_id, emit_webhook
from tests.test_survey.txx_data import MIN_OFFERS_RATIO, OFFERS_RATIO

from tests.test_survey.txx import get_offer, get_min_offer, WEBHOOK_DELAY, TASK_REPETITION, SURVEY_CHOICE_FIELDS, SURVEY_CONTROL_FIELDS, SURVEY_MAIN_TASK_CODE_FIELD, OFFER, MIN_OFFER, get_completion_code, test_available, figure_eight_mock

AUTO_PROP_DELAY = 0.1
NB_MAX_AUTO_PLAY_RETRIES = 5

def is_resp_in_prop_result(resp_worker_id, job_id, treatment):
    con = get_db()
    table = get_table("prop", job_id, "result", treatment=treatment)
    sql = f"SELECT * FROM {table} WHERE job_id=? and resp_worker_id=?"
    print("SQL: ", sql)
    try:
        with con:
            res = con.execute(sql, [job_id, resp_worker_id]).fetchone()
        if res is None:
            return False
        else:
            return True
    except Exception:
        pass
    return False


def test_index(client, treatment, prefix="", completion_code_prefix="resp:"):
    client = None
    job_id = "test"
    completion_code_prefix_bytes = completion_code_prefix.encode("utf-8") if completion_code_prefix else b"resp:"
    for _ in range(TASK_REPETITION):
        client = get_client()
        resp_worker_id = generate_worker_id(f"{prefix}index_resp")
        path = f"/{treatment}/?worker_id={resp_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            assert b"RESPONDER" in res.data
            # res = _process_resp_tasks(client, worker_id=worker_id)

            res = _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer())
            process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
            assert completion_code_prefix_bytes in res.data
        time.sleep(WEBHOOK_DELAY)
        # let the auto-responder kick-in
        with app.app_context():
            # let the auto-responder kick-in
            for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
                if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                    break
                time.sleep(AUTO_PROP_DELAY)
            assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)

        

def test_index_auto(client, treatment, prefix=""):
    #takes the role assigned by the system and solves the corresponding tasks
    client = None
    job_id = "test_auto"
    for _ in range(TASK_REPETITION):
        auto_worker_id = generate_worker_id(f"{prefix}index_auto")
        path = f"/{treatment}/?worker_id={auto_worker_id}&job_id={job_id}"
        with app.test_request_context(path):
            client = get_client()
            res = client.get(path, follow_redirects=True)
            time.sleep(0.001)
            # Play as responder
            # print(res.data)
            if b"role of a RESPONDER" in res.data:
                # res = _process_resp(client, treatment, job_id=job_id, worker_id=auto_worker_id, min_offer=MIN_OFFER)
                # process_tasks(client, job_id=job_id, worker_id=auto_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": treatment})
                res = _process_resp_tasks(client, treatment, job_id=job_id, worker_id=auto_worker_id, min_offer=get_min_offer())
                assert b"resp:" in res.data
                assert is_worker_available(auto_worker_id, get_table("resp", job_id=job_id, schema="result"))
            # Play a proposer
            elif b"role of a PROPOSER" in res.data:
                app.logger.warning("PROPOSER")
                res = client.get(path, follow_redirects=True)
                res = _process_prop_round(client, treatment, job_id=job_id, worker_id=auto_worker_id, offer=get_offer(), response_available=True)
                assert b"prop:" in res.data
                assert is_worker_available(auto_worker_id, get_table("resp", job_id=job_id, schema="result"))
            else:
                assert False, "Nooooooooooooooo"
            time.sleep(WEBHOOK_DELAY)



def test_resp_index(client, treatment):
    res = client.get(f"/{treatment}/resp/", follow_redirects=True).data
    assert b"RESPONDER" in res

def test_resp_done_success(client, treatment, completion_code_prefix="resp:"):
    completion_code_prefix_bytes = completion_code_prefix.encode("utf-8") if completion_code_prefix else b"resp:"
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer()).data
    assert completion_code_prefix_bytes in res

def test_resp_done_both_models(client, treatment, completion_code_prefix="resp:"):
    completion_code_prefix_bytes = completion_code_prefix.encode("utf-8") if completion_code_prefix else b"resp:"
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer()).data
    assert completion_code_prefix_bytes in res

    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer()).data
    assert completion_code_prefix_bytes in res

def test_prop_index(client, treatment):
    resp_worker_id = generate_worker_id("resp")
    job_id = "test"
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer())
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
    time.sleep(WEBHOOK_DELAY)
    time.sleep(WEBHOOK_DELAY)
    # let the auto-responder kick-in
    with app.app_context():
        # let the auto-responder kick-in
        for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
            if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                break
            time.sleep(AUTO_PROP_DELAY)
        assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)

# def test_prop_check(client, treatment):
#     worker_id = generate_worker_id("prop_check")
#     path = f"/{treatment}/prop/?job_id=test&worker_id={worker_id}"
#     _process_resp_tasks(client, treatment, worker_id=None, min_offer=get_min_offer())
#     with app.test_request_context(path):
#         client.get(path)
#         res = client.get(f"{treatment}/prop/check/?offer={OFFER}").data
#         print("RES: ", res)
#         assert b"acceptance_probability" in res
#         assert b"best_offer_probability" in res

# def test_prop_done(client, treatment):
#     res = _process_prop(client, treatment, offer=get_offer())
#     assert b"prop:" in res.data

# def test_prop_check_done(client, treatment):
#     nb_dss_check = random.randint(1, 20)
#     res = _process_prop(client, treatment, offer=get_offer(), nb_dss_check=nb_dss_check)
#     assert b"prop:" in res.data


def test_bonus_delayed(client, treatment, synchron=False):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    # we make sure the offer is accepted!
    min_offer = 0
    for _ in range(TASK_REPETITION):
        client = get_client()
        job_id = "test"
        resp_worker_id = generate_worker_id("bonus_resp")
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=min_offer, bonus_mode="random", synchron=synchron)
        time.sleep(WEBHOOK_DELAY)
        # let the auto-responder kick-in
        with app.app_context():
            # let the auto-responder kick-in
            for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
                if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                    break
                time.sleep(AUTO_PROP_DELAY)
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert min_offer <= bonus_resp
            assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
            assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)

def test_bonus_nodelay(client, treatment, synchron=True):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    # we make sure the offer is accepted!
    min_offer = 0
    for _ in range(TASK_REPETITION):
        client = get_client()
        job_id = "test"
        resp_worker_id = generate_worker_id("bonus_resp")
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=min_offer, bonus_mode="random", synchron=synchron)

        time.sleep(WEBHOOK_DELAY)
        with app.app_context():
            # let the auto-responder kick-in
            for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
                if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                    break
                time.sleep(AUTO_PROP_DELAY)
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert min_offer <= bonus_resp
            assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
            assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)

def test_webhook(client, treatment):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    job_id = "test"
    resp_worker_id = generate_worker_id("webhook_resp")
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer())
    emit_webhook(client, url=f"/{treatment}/webhook/", job_id=job_id, treatment=treatment, worker_id=resp_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        # let the auto-responder kick-in
        for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
            if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                break
            time.sleep(AUTO_PROP_DELAY)
        assert is_worker_available(resp_worker_id, get_table("resp", job_id=job_id, schema="result", treatment=treatment))
        assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)

def test_auto_finalize(client, treatment):
    # Test automatic webhook triggering to finalize tasks
    job_id = "test"
    resp_worker_id = generate_worker_id("auto_resp")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer())
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        # let the auto-responder kick-in
        for _ in range(NB_MAX_AUTO_PLAY_RETRIES):
            if is_resp_in_prop_result(resp_worker_id, job_id, treatment):
                break
            time.sleep(AUTO_PROP_DELAY)
        assert is_worker_available(resp_worker_id, get_table("resp", job_id=job_id, schema="result", treatment=treatment))
        assert is_resp_in_prop_result(resp_worker_id, job_id, treatment)


def test_payment(client, treatment):
    with HTTMock(figure_eight_mock):
        job_id = "test"
        resp_worker_id = generate_worker_id("payment_resp")
        _process_resp_tasks(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
        time.sleep(WEBHOOK_DELAY)
        for _ in range(5):
            emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, job_id="test", worker_id=resp_worker_id, by_get=False)
            time.sleep(WEBHOOK_DELAY)
            with app.app_context():
                assert 0 == get_worker_bonus(job_id, resp_worker_id)
                worker_paid_bonus = get_worker_paid_bonus(job_id, resp_worker_id)
                assert 0 <= worker_paid_bonus <= tasks.MAX_BONUS + MAX_GAIN



def test_survey_resp(client, treatment):
    with app.app_context():
        worker_id = generate_worker_id("survey")
        assignment_id = worker_id.upper().replace("_", "")
        path = f"/survey/{treatment}/?job_id=test&worker_id={worker_id}&assignment_id={assignment_id}"
        with app.test_request_context(path):
            client.get(path, follow_redirects=True)
            form = MainForm()
            form_data = {}
            for field, item in form._fields.items():
                if field in SURVEY_CONTROL_FIELDS:
                    form_data[field] = "correct"
                elif field == SURVEY_MAIN_TASK_CODE_FIELD:
                    form_data[field] = "resp:"
                elif field.startswith("code_"):
                    form_data[field] = get_completion_code(field)
                elif field in SURVEY_CHOICE_FIELDS:
                    form_data[field] = random.choice(item.choices)[0]
                else:
                    form_data[field] = "abc"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"Your survey completion code is:" in res.data
            assert b"dropped" not in res.data

def test_survey_prop(client, treatment):
    with app.app_context():
        worker_id = generate_worker_id("survey")
        assignment_id = worker_id.upper().replace("_", "")
        path = f"/survey/{treatment}/?job_id=test&worker_id={worker_id}&assignment_id={assignment_id}"
        with app.test_request_context(path):
            client.get(path, follow_redirects=True)
            form = MainForm()
            form_data = {}
            for field, item in form._fields.items():
                if field in SURVEY_CONTROL_FIELDS:
                    form_data[field] = "correct"
                elif field == SURVEY_MAIN_TASK_CODE_FIELD:
                    form_data[field] = "prop:"
                elif field.startswith("code_"):
                    form_data[field] = ""
                elif field in SURVEY_CHOICE_FIELDS:
                    form_data[field] = random.choice(item.choices)[0]
                else:
                    form_data[field] = "abc"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"Your survey completion code is:" in res.data
            assert b"dropped" not in res.data

def test_survey_drop(client, treatment):
    """
        test if the submissed is dropped without control on other fields when <drop> is set to "1"
    """
    with app.app_context():
        worker_id = generate_worker_id("survey")
        path = f"/survey/{treatment}/?job_id=test&worker_id={worker_id}"
        with app.test_request_context(path):
            form = MainForm()
            form_data = {key: "" for key in form._fields}
            form_data["drop"] = "1"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"dropped" in res.data

def test_survey_unique(client, treatment):
    """
        test if the submissed is dropped without control on other fields when <drop> is set to "1"
    """
    with app.app_context():
        worker_id = generate_worker_id("survey")
        path = f"/survey/{treatment}/?job_id=test&worker_id={worker_id}"
        with app.test_request_context(path):
            form = MainForm()
            form_data = {key: "" for key in form._fields}
            form_data["drop"] = "1"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"dropped" in res.data
        with app.test_request_context(path):
            form = MainForm()
            form_data = {key: "" for key in form._fields}
            form_data["drop"] = "0"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"dropped" in res.data