import os
import time
import unittest
from unittest import mock
import requests
import random
from flask import jsonify
from httmock import urlmatch, HTTMock, response

from survey import tasks
from survey.txx.survey import MainForm
from survey.utils import get_worker_bonus, get_worker_paid_bonus, get_total_worker_bonus, WORKER_CODE_DROPPED

from tests.test_survey import app, client, generate_worker_id, emit_webhook
from tests.test_survey.test_tasks import process_tasks


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]

WEBHOOK_DELAY = 0.25

TASK_REPETITION = 1

@urlmatch(netloc=r'api.figure-eight.com$')
def figure_eight_mock(url, request):
    return response()


def _process_resp(client, job_id="test", worker_id=None, min_offer=100, clear_session=True, path=None):
    if worker_id is None:
        worker_id = generate_worker_id()
    if path is None:
        path = f"/{TREATMENT}/resp/?job_id={job_id}&worker_id={worker_id}"
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path, follow_redirects=True)
        return client.post(path, data={"min_offer":min_offer, "other_prop":min_offer, "other_resp": min_offer}, follow_redirects=True)

def _process_resp_tasks(client, job_id="test", worker_id=None, min_offer=100, bonus_mode="random", clear_session=True, synchron=True, path=None):
    if worker_id is None:
        worker_id = generate_worker_id("resp")
    process_tasks(client, job_id=job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    res = _process_resp(client, job_id=job_id, worker_id=worker_id, min_offer=min_offer, clear_session=clear_session, path=path)
    if synchron:
        emit_webhook(client, url=f"/{TREATMENT}/webhook/?synchron=1", job_id=job_id, worker_id=worker_id)
    else:
        emit_webhook(client, url=f"/{TREATMENT}/webhook/", job_id=job_id, worker_id=worker_id)
    return res

def test_available():
    assert TREATMENT.upper() in app.config["TREATMENTS"]

def test_index(client):
    job_id = "test"
    for _ in range(TASK_REPETITION):
        resp_worker_id = generate_worker_id("index_resp")
        path = f"/{TREATMENT}/?worker_id={resp_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            assert b"RESPONDER" in res.data
            # res = _process_resp_tasks(client, worker_id=worker_id)

            res = _process_resp(client, job_id=job_id, worker_id=resp_worker_id, min_offer=100)
            process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": TREATMENT})
            assert b"resp:" in res.data
        prop_worker_id = generate_worker_id("index_prop")
        time.sleep(WEBHOOK_DELAY)
        path = f"/{TREATMENT}/?worker_id={prop_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            # assert b"PROPOSER" in res.data
            res = _process_prop_round(client, worker_id=prop_worker_id, response_available=True)
            assert b"prop:" in res.data


def test_resp_index(client):
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"RESPONDER" in res

def test_resp_done_success(client):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, worker_id=worker_id).data
    assert b"resp:" in res

def test_resp_done_both_models(client):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, worker_id=worker_id).data
    assert b"resp:" in res

    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, worker_id=worker_id).data
    assert b"resp:" in res

def test_prop_index(client):
    resp_worker_id = generate_worker_id("resp")
    job_id = "test"
    _process_resp(client, job_id=job_id, worker_id=resp_worker_id, min_offer=100)
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": TREATMENT})
    time.sleep(WEBHOOK_DELAY)
    prop_worker_id = generate_worker_id("prop")
    res = client.get(f"/{TREATMENT}/prop/?job_id={job_id}&worker_id={prop_worker_id}").data
    assert b"PROPOSER" in res

def test_prop_check(client):
    worker_id = generate_worker_id("prop_check")
    path = f"/{TREATMENT}/prop/?job_id=test&worker_id={worker_id}"
    _process_resp_tasks(client, worker_id=None)
    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{TREATMENT}/prop/check/?offer=100").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def _process_prop(client, job_id="test", worker_id=None, offer=100, clear_session=True, response_available=False, path=None, auto_finalize=False):
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if path is None:
        path = f"/{TREATMENT}/prop/?job_id={job_id}&worker_id={worker_id}"
    if auto_finalize is True:
        path += "&auto_finalize=1"
    if not response_available:
        _process_resp_tasks(client, job_id=job_id)
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={"offer":offer}, follow_redirects=True)

def _process_prop_round(client, job_id="test", worker_id=None, offer=100, clear_session=True, response_available=False, synchron=False, path=None):
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if synchron:
        webhook_url = f"/{TREATMENT}/webhook/?synchron=1"
    else:
        webhook_url = f"/{TREATMENT}/webhook/"
        
    if not response_available:
        _process_resp_tasks(client, worker_id=None, min_offer=100, bonus_mode="full")
    res = _process_prop(client, worker_id=worker_id, offer=offer, response_available=True, path=path)
    time.sleep(WEBHOOK_DELAY)
    emit_webhook(client, url=webhook_url, job_id=job_id, worker_id=worker_id)
    return res



def test_prop_done(client):
    res = _process_prop(client)
    assert b"prop:" in res.data
        # res = _process_prop(client)
        # assert b"prop:" in res.data
        # res = _process_prop(client)
        # assert b"prop:" in res.data
        # res = _process_prop(client)
        # assert b"prop:" in res.data



def test_bonus_delayed(client, synchron=False):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(TASK_REPETITION):
        job_id = "test"
        resp_worker_id = generate_worker_id("resp")
        prop_worker_id = generate_worker_id("prop")
        _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=100, bonus_mode="full", synchron=synchron)
        time.sleep(WEBHOOK_DELAY)
        _process_prop_round(client, worker_id=prop_worker_id, offer=100, response_available=True, synchron=synchron)
        time.sleep(WEBHOOK_DELAY)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert bonus_resp == tasks.MAX_BONUS + 100
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == 100

def test_bonus_nodelay(client, synchron=True):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(TASK_REPETITION):
        job_id = "test"
        resp_worker_id = generate_worker_id("resp")
        prop_worker_id = generate_worker_id("prop")
        _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=100, bonus_mode="full", synchron=synchron)
        _process_prop_round(client, worker_id=prop_worker_id, offer=100, response_available=True, synchron=synchron)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert bonus_resp == tasks.MAX_BONUS + 100
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == 100

def test_webhook(client):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    job_id = "test"
    resp_worker_id = generate_worker_id("resp")
    prop_worker_id = generate_worker_id("prop")
    process_tasks(client, job_id, resp_worker_id, bonus_mode="full")
    _process_resp(client, job_id, resp_worker_id, min_offer=100)
    emit_webhook(client, url=f"/{TREATMENT}/webhook/", worker_id=resp_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    _process_prop(client, worker_id=prop_worker_id, offer=100, response_available=True)
    emit_webhook(client, url=f"/{TREATMENT}/webhook/", worker_id=prop_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        bonus_resp = get_worker_bonus(job_id, resp_worker_id)
        assert bonus_resp == tasks.MAX_BONUS + 100
        bonus_prop = get_worker_bonus(job_id, prop_worker_id)
        assert bonus_prop == 100


def test_auto_finalize(client):
    # Test automatic webhook triggering to finalize tasks
    job_id = "test"
    resp_worker_id = generate_worker_id("resp")
    prop_worker_id = generate_worker_id("prop")
    _process_resp(client, job_id, resp_worker_id, min_offer=100)
    process_tasks(client, job_id, resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": TREATMENT})
    time.sleep(WEBHOOK_DELAY)
    _process_prop(client, job_id=job_id, worker_id=prop_worker_id, response_available=True, auto_finalize=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        bonus_resp = get_worker_bonus(job_id, resp_worker_id)
        assert bonus_resp == tasks.MAX_BONUS + 100
        bonus_prop = get_worker_bonus(job_id, prop_worker_id)
        assert bonus_prop == 100


def test_payment(client):
    with HTTMock(figure_eight_mock):
        job_id = "test"
        resp_worker_id = generate_worker_id("resp")
        prop_worker_id = generate_worker_id("prop")
        _process_resp(client, job_id, resp_worker_id, min_offer=100)
        process_tasks(client, job_id, resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": TREATMENT})
        time.sleep(WEBHOOK_DELAY)
        _process_prop(client, job_id=job_id, worker_id=prop_worker_id, response_available=True, auto_finalize=True)
        time.sleep(WEBHOOK_DELAY)
        for _ in range(5):
            emit_webhook(client, url=f"/{TREATMENT}/webhook/", job_id="test", worker_id=prop_worker_id, by_get=False)
            emit_webhook(client, url=f"/{TREATMENT}/webhook/", job_id="test", worker_id=resp_worker_id, by_get=False)
            time.sleep(WEBHOOK_DELAY)
            with app.app_context():
                assert 0 == get_worker_bonus(job_id, resp_worker_id)
                assert get_worker_paid_bonus(job_id, resp_worker_id) == tasks.MAX_BONUS + 100
                assert 0 == get_worker_bonus(job_id, prop_worker_id)
                assert get_worker_paid_bonus(job_id, prop_worker_id) == 100



def test_survey_resp(client):
    CONTROL_FIELDS = ["proposer", "responder", "proposer_responder"]
    CHOICE_FIELDS = {"age", "gender", "income", "ethnicity", "test"}
    codes = {"code_crt": "crt:", "code_cg":"cg:", "code_hexaco": "hexaco:", "code_effort": "eff:", "code_risk": "risk:", "code_resp_prop": "resp:"}
    with app.app_context():
        worker_id = generate_worker_id("survey")
        assignment_id = worker_id.upper().replace("_", "")
        path = f"/survey/{TREATMENT}/?job_id=test&worker_id={worker_id}&assignment_id={assignment_id}"
        with app.test_request_context(path):
            client.get(path, follow_redirects=True)
            form = MainForm()
            form_data = {}
            for field, item in form._fields.items():
                if field in CONTROL_FIELDS:
                    form_data[field] = "correct"
                elif field in CHOICE_FIELDS:
                    form_data[field] = random.choice(item.choices)[0]
                else:
                    form_data[field] = "abc"
            form_data.update(codes)
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"Your survey completion code is:" in res.data
            assert b"dropped" not in res.data

def test_survey_prop(client):
    CONTROL_FIELDS = ["proposer", "responder", "proposer_responder"]
    CHOICE_FIELDS = {"age", "gender", "income", "ethnicity", "test"}
    codes = {"code_crt": "", "code_cg":"", "code_hexaco": "", "code_effort": "", "code_risk": "", "code_resp_prop": "prop:"}
    with app.app_context():
        worker_id = generate_worker_id("survey")
        assignment_id = worker_id.upper().replace("_", "")
        path = f"/survey/{TREATMENT}/?job_id=test&worker_id={worker_id}&assignment_id={assignment_id}"
        with app.test_request_context(path):
            client.get(path, follow_redirects=True)
            form = MainForm()
            form_data = {}
            for field, item in form._fields.items():
                if field in CONTROL_FIELDS:
                    form_data[field] = "correct"
                elif field in CHOICE_FIELDS:
                    form_data[field] = random.choice(item.choices)[0]
                else:
                    form_data[field] = "abc"
            form_data.update(codes)
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"Your survey completion code is:" in res.data
            assert b"dropped" not in res.data

def test_survey_drop(client):
    """
        test if the submissed is dropped without control on other fields when <drop> is set to "1"
    """
    with app.app_context():
        worker_id = generate_worker_id("survey")
        path = f"/survey/{TREATMENT}/?job_id=test&worker_id={worker_id}"
        with app.test_request_context(path):
            form = MainForm()
            form_data = {key: "" for key in form._fields}
            form_data["drop"] = "1"
            res = client.post(path, data=form_data, follow_redirects=True)
            assert b"dropped" in res.data

def test_survey_unique(client):
    """
        test if the submissed is dropped without control on other fields when <drop> is set to "1"
    """
    with app.app_context():
        worker_id = generate_worker_id("survey")
        path = f"/survey/{TREATMENT}/?job_id=test&worker_id={worker_id}"
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