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
from survey.txx.survey import MainForm
from survey.utils import get_worker_bonus, get_worker_paid_bonus, get_total_worker_bonus, WORKER_CODE_DROPPED

from tests.test_survey import app, client, get_client, generate_worker_id, emit_webhook
from tests.test_survey.test_tasks import process_tasks



WEBHOOK_DELAY = 0.25

TASK_REPETITION = 8

OFFER = MAX_GAIN//2
MIN_OFFER = MAX_GAIN//2
SURVEY_MAIN_TASK_CODE_FIELD = "code_resp_prop"
SURVEY_CONTROL_FIELDS = {"proposer", "responder", "proposer_responder", "money_division"}
SURVEY_CHOICE_FIELDS = {"age", "gender", "income", "location", "test"}

@urlmatch(netloc=r'api.figure-eight.com$')
def figure_eight_mock(url, request):
    return response()

def get_completion_code(field):
    # field is assumed to be named: "code_" + $TASK_NAME
    # codes are then: $TASK_NAME + ":" + random-part
    return f"{field[5:]}:"


def _process_resp(client, treatment, job_id="test", worker_id=None, min_offer=MIN_OFFER, clear_session=True, path=None):
    if worker_id is None:
        worker_id = generate_worker_id()
    if path is None:
        path = f"/{treatment}/resp/?job_id={job_id}&worker_id={worker_id}"
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path, follow_redirects=True)
        return client.post(path, data={"min_offer":min_offer, "other_prop":min_offer, "other_resp": min_offer}, follow_redirects=True)

def _process_resp_tasks(client, treatment, job_id="test", worker_id=None, min_offer=MIN_OFFER, bonus_mode="random", clear_session=True, synchron=True, path=None):
    if worker_id is None:
        worker_id = generate_worker_id("resp")
    process_tasks(client, job_id=job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    res = _process_resp(client, treatment, job_id=job_id, worker_id=worker_id, min_offer=min_offer, clear_session=clear_session, path=path)
    if synchron:
        emit_webhook(client, url=f"/{treatment}/webhook/?synchron=1", treatment=treatment, job_id=job_id, worker_id=worker_id)
    else:
        emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, job_id=job_id, worker_id=worker_id)
    return res

def test_available(treatment):
    assert treatment.upper() in app.config["TREATMENTS"]

def test_index(client, treatment, prefix=""):
    client = None
    job_id = "test"
    for _ in range(TASK_REPETITION):
        client = get_client()
        resp_worker_id = generate_worker_id(f"{prefix}index_resp")
        path = f"/{treatment}/?worker_id={resp_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            assert b"RESPONDER" in res.data
            # res = _process_resp_tasks(client, worker_id=worker_id)

            res = _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
            process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": treatment})
            assert b"resp:" in res.data
        prop_worker_id = generate_worker_id(f"{prefix}index_prop")
        time.sleep(WEBHOOK_DELAY)
        path = f"/{treatment}/?worker_id={prop_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            # assert b"PROPOSER" in res.data
            res = _process_prop_round(client, treatment, worker_id=prop_worker_id, response_available=True)
            assert b"prop:" in res.data

def test_index_auto(client, treatment="t10", prefix=""):
    client = None
    job_id = "test_auto"
    for _ in range(TASK_REPETITION):
        auto_worker_id = generate_worker_id(f"{prefix}index_auto")
        path = f"/{treatment}/?worker_id={auto_worker_id}"
        with app.test_request_context(path):
            client = get_client()
            res = client.get(path, follow_redirects=True)
            time.sleep(0.001)
            # Play as responder
            # print(res.data)
            if b"role of a RESPONDER" in res.data:
                # res = _process_resp(client, treatment, job_id=job_id, worker_id=auto_worker_id, min_offer=MIN_OFFER)
                # process_tasks(client, job_id=job_id, worker_id=auto_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": treatment})
                res = _process_resp_tasks(client, treatment, job_id=job_id, worker_id=auto_worker_id, min_offer=MIN_OFFER)
                assert b"resp:" in res.data
            # Play a proposer
            elif b"role of a PROPOSER" in res.data:
                app.logger.warn("PROPOSER")
                res = client.get(path, follow_redirects=True)
                res = _process_prop_round(client, treatment, job_id=job_id, worker_id=auto_worker_id, response_available=True)
                # assert b"prop:" in res.data
            else:
                assert False, "Nooooooooooooooo"
            time.sleep(WEBHOOK_DELAY)



def test_resp_index(client, treatment):
    res = client.get(f"/{treatment}/resp/").data
    assert b"RESPONDER" in res

def test_resp_done_success(client, treatment):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id).data
    assert b"resp:" in res

def test_resp_done_both_models(client, treatment):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id).data
    assert b"resp:" in res

    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id).data
    assert b"resp:" in res

def test_prop_index(client, treatment):
    resp_worker_id = generate_worker_id("resp")
    job_id = "test"
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": treatment})
    time.sleep(WEBHOOK_DELAY)
    prop_worker_id = generate_worker_id("prop")
    res = client.get(f"/{treatment}/prop/?job_id={job_id}&worker_id={prop_worker_id}").data
    assert b"PROPOSER" in res

def test_prop_check(client, treatment):
    worker_id = generate_worker_id("prop_check")
    path = f"/{treatment}/prop/?job_id=test&worker_id={worker_id}"
    _process_resp_tasks(client, treatment, worker_id=None)
    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{treatment}/prop/check/?offer={OFFER}").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def _process_prop(client, treatment, job_id="test", worker_id=None, offer=OFFER, clear_session=True, response_available=False, path=None, auto_finalize=False, nb_dss_check=None):
    MODEL_KEY = f"{TREATMENTS_MODEL_REFS[treatment.upper()]}_MODEL"
    dss_available = bool(app.config.get(MODEL_KEY))
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    path2 = None
    if path is None:
        path = f"/{treatment}/prop/?job_id={job_id}&worker_id={worker_id}"
    if path2 is None:
        path2 = f"/{treatment}/prop_dss/?job_id={job_id}&worker_id={worker_id}"

    if auto_finalize is True:
        path += "&auto_finalize=1"
        path2 += "&auto_finalize=1"
    if not response_available:
        _process_resp_tasks(client, treatment, job_id=job_id)
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        if dss_available:
            res = client.post(path, data={"offer":offer}, follow_redirects=False)
            if nb_dss_check is None:
                res = client.post(path2, data={"offer_dss":offer}, follow_redirects=True)
            else:
                check_path = f"{treatment}/prop/check/"
                client.get(path2, follow_redirects=True)
                client.get(check_path)
                for _ in range(nb_dss_check):
                    tmp = client.get(f"{check_path}?offer={random.choice(list(range(0, MAX_GAIN+1, 5)))}")
                res = client.post(path2, data={"offer_dss":offer}, follow_redirects=True)
        else:
            res = client.post(path, data={"offer":offer}, follow_redirects=True)
        return res


def _process_prop_round(client, treatment, job_id="test", worker_id=None, offer=OFFER, clear_session=True, response_available=False, synchron=False, path=None):
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if synchron:
        webhook_url = f"/{treatment}/webhook/?synchron=1"
    else:
        webhook_url = f"/{treatment}/webhook/"
        
    if not response_available:
        _process_resp_tasks(client, treatment, worker_id=None, min_offer=MIN_OFFER, bonus_mode="full")
    res = _process_prop(client, treatment, worker_id=worker_id, offer=offer, response_available=True, path=path)
    time.sleep(WEBHOOK_DELAY)
    emit_webhook(client, url=webhook_url, treatment=treatment, job_id=job_id, worker_id=worker_id)
    return res



def test_prop_done(client, treatment):
    res = _process_prop(client, treatment)
    assert b"prop:" in res.data

def test_prop_check_done(client, treatment):
    nb_dss_check = random.randint(1, 20)
    res = _process_prop(client, treatment, nb_dss_check=nb_dss_check)
    assert b"prop:" in res.data


def test_bonus_delayed(client, treatment, synchron=False):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(TASK_REPETITION):
        client = get_client()
        job_id = "test"
        resp_worker_id = generate_worker_id("bonus_resp")
        prop_worker_id = generate_worker_id("bonus_prop")
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=MIN_OFFER, bonus_mode="full", synchron=synchron)
        time.sleep(WEBHOOK_DELAY)
        _process_prop_round(client, treatment, worker_id=prop_worker_id, offer=OFFER, response_available=True, synchron=synchron)
        time.sleep(WEBHOOK_DELAY)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert MIN_OFFER <= bonus_resp
            assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == OFFER

def test_bonus_nodelay(client, treatment, synchron=True):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(TASK_REPETITION):
        client = get_client()
        job_id = "test"
        resp_worker_id = generate_worker_id("bonus_resp")
        prop_worker_id = generate_worker_id("bonus_prop")
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=MIN_OFFER, bonus_mode="full", synchron=synchron)
        _process_prop_round(client, treatment, worker_id=prop_worker_id, offer=OFFER, response_available=True, synchron=synchron)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert MIN_OFFER <= bonus_resp
            assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == OFFER

def test_webhook(client, treatment):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    job_id = "test"
    resp_worker_id = generate_worker_id("webhook_resp")
    prop_worker_id = generate_worker_id("webhook_prop")
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
    emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, worker_id=resp_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    _process_prop(client, treatment, job_id=job_id, worker_id=prop_worker_id, offer=OFFER, response_available=True)
    emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, worker_id=prop_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        bonus_resp = get_worker_bonus(job_id, resp_worker_id)
        assert MIN_OFFER <= bonus_resp
        assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
        bonus_prop = get_worker_bonus(job_id, prop_worker_id)
        assert bonus_prop == OFFER

def test_auto_finalize(client, treatment):
    # Test automatic webhook triggering to finalize tasks
    job_id = "test"
    resp_worker_id = generate_worker_id("auto_resp")
    prop_worker_id = generate_worker_id("auto_prop")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="full", url_kwargs={"auto_finalize": 1, "treatment": treatment})
    time.sleep(WEBHOOK_DELAY)
    res = _process_prop(client, treatment, job_id=job_id, worker_id=prop_worker_id, offer=OFFER, response_available=True, auto_finalize=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        bonus_resp = get_worker_bonus(job_id, resp_worker_id)
        assert MIN_OFFER <= bonus_resp
        assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
        bonus_prop = get_worker_bonus(job_id, prop_worker_id)
        assert bonus_prop == OFFER


def test_payment(client, treatment):
    with HTTMock(figure_eight_mock):
        job_id = "test"
        resp_worker_id = generate_worker_id("payment_resp")
        prop_worker_id = generate_worker_id("payment_prop")
        _process_resp_tasks(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=MIN_OFFER)
        time.sleep(WEBHOOK_DELAY)
        # _process_prop(client, treatment, job_id=job_id, worker_id=prop_worker_id, response_available=True, auto_finalize=True)
        _process_prop_round(client, treatment, job_id=job_id, worker_id=prop_worker_id, response_available=True)
        time.sleep(WEBHOOK_DELAY)
        for _ in range(5):
            emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, job_id="test", worker_id=prop_worker_id, by_get=False)
            emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, job_id="test", worker_id=resp_worker_id, by_get=False)
            time.sleep(WEBHOOK_DELAY)
            with app.app_context():
                bonus_resp = get_worker_bonus(job_id, resp_worker_id)
                assert 0 == get_worker_bonus(job_id, resp_worker_id)
                assert MIN_OFFER <= get_worker_paid_bonus(job_id, resp_worker_id) <= tasks.MAX_BONUS + (MAX_GAIN - OFFER)
                assert 0 == get_worker_bonus(job_id, prop_worker_id)
                assert get_worker_paid_bonus(job_id, prop_worker_id) == OFFER



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