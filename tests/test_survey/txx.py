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


def get_offer():
    return int(random.choice(OFFERS_RATIO) * MAX_GAIN)

def get_min_offer():
    return int(random.choice(MIN_OFFERS_RATIO) * MAX_GAIN)

WEBHOOK_DELAY = 0.25

TASK_REPETITION = 3
TASK_REPETITION_LOWER = 2

OFFER = MAX_GAIN//2
MIN_OFFER = MAX_GAIN//2
SURVEY_MAIN_TASK_CODE_FIELD = "code_resp_prop"
SURVEY_CONTROL_FIELDS = {"proposer", "responder", "proposer_responder", "money_division"}
SURVEY_CHOICE_FIELDS = {"age", "gender", "income", "ethnicity", "test", "education"}

    

@urlmatch(netloc=r'api.figure-eight.com$')
def figure_eight_mock(url, request):
    return response()

def get_completion_code(field):
    # field is assumed to be named: "code_" + $TASK_NAME
    # codes are then: $TASK_NAME + ":" + random-part
    return f"{field[5:]}:"

def test_available(treatment):
    assert treatment.upper() in app.config["TREATMENTS"]

def test_index(client, treatment, prefix="", response_available=False, resp_feedback_fields=None):
    client = None
    job_id = "test"
    for _ in range(TASK_REPETITION):
        client = get_client()
        if not response_available:
            resp_worker_id = generate_worker_id(f"{prefix}index_resp")
            path = f"/{treatment}/?worker_id={resp_worker_id}"
            with app.test_request_context(path):
                res = client.get(path, follow_redirects=True)
                assert b"RESPONDER" in res.data
                # res = _process_resp_tasks(client, worker_id=worker_id)

                res = _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
                process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
                assert b"resp:" in res.data
        prop_worker_id = generate_worker_id(f"{prefix}index_prop")
        time.sleep(WEBHOOK_DELAY)
        path = f"/{treatment}/?worker_id={prop_worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True)
            # assert b"PROPOSER" in res.data
            res = _process_prop_round(client, treatment, worker_id=prop_worker_id, offer=get_offer(), response_available=True)
            assert b"prop:" in res.data

def test_index_feedback(client, treatment, prefix="", response_available=False, resp_feedback_fields=None):
    client = None
    job_id = "test"
    for _ in range(TASK_REPETITION):
        client = get_client()
        if not response_available:
            resp_worker_id = generate_worker_id(f"{prefix}index_feedback_resp")
            path = f"/{treatment}/?worker_id={resp_worker_id}"
            with app.test_request_context(path):
                res = client.get(path, follow_redirects=True)
                assert b"RESPONDER" in res.data
                # res = _process_resp_tasks(client, worker_id=worker_id)

                res = _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
                assert b"resp:" in res.data
        else:
            prop_worker_id = generate_worker_id(f"{prefix}index_prop")
            path = f"/{treatment}/?worker_id={prop_worker_id}"
            with app.test_request_context(path):
                res = client.get(path, follow_redirects=True)
                res = _process_prop_round(client, treatment, worker_id=prop_worker_id, offer=get_offer(), response_available=True, finalize_round=False)
                assert b"prop:" in res.data

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
    res = client.get(f"/{treatment}/resp/").data
    assert b"RESPONDER" in res

def test_resp_done_success(client, treatment, resp_feedback_fields=None):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields).data
    assert b"resp:" in res

def test_resp_done_both_models(client, treatment, resp_feedback_fields=None):
    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields).data
    assert b"resp:" in res

    worker_id = generate_worker_id("resp")
    process_tasks(client, worker_id=worker_id)
    res = _process_resp(client, treatment, worker_id=worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields).data
    assert b"resp:" in res

def test_prop_index(client, treatment, response_available=False, resp_feedback_fields=None):
    resp_worker_id = generate_worker_id("resp")
    job_id = "test"
    if not response_available:
        _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
        process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
        time.sleep(WEBHOOK_DELAY)
    prop_worker_id = generate_worker_id("prop")
    res = client.get(f"/{treatment}/prop/?job_id={job_id}&worker_id={prop_worker_id}", follow_redirects=True).data
    assert b"PROPOSER" in res

def test_prop_check(client, treatment, response_available=False, resp_feedback_fields=None):
    worker_id = generate_worker_id("prop_check")
    path = f"/{treatment}/prop/?job_id=test&worker_id={worker_id}"
    if not response_available:
        _process_resp_tasks(client, treatment, worker_id=None, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
    with app.test_request_context(path):
        client.get(path, follow_redirects=True)
        res = client.get(f"{treatment}/prop/check/?offer={OFFER}", follow_redirects=True).data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def test_prop_done(client, treatment, response_available=False):
    res = _process_prop(client, treatment, offer=get_offer(), response_available=response_available)
    assert b"prop:" in res.data

def test_prop_check_done(client, treatment, response_available=False):
    nb_dss_check = random.randint(1, 20)
    res = _process_prop(client, treatment, offer=get_offer(), nb_dss_check=nb_dss_check, response_available=response_available)
    assert b"prop:" in res.data


def test_bonus_delayed(client, treatment, synchron=False):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(TASK_REPETITION):
        client = get_client()
        job_id = "test"
        resp_worker_id = generate_worker_id("bonus_resp")
        prop_worker_id = generate_worker_id("bonus_prop")
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=MIN_OFFER, bonus_mode="random", synchron=synchron)
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
        _process_resp_tasks(client, treatment, worker_id=resp_worker_id, min_offer=MIN_OFFER, bonus_mode="random", synchron=synchron)
        _process_prop_round(client, treatment, worker_id=prop_worker_id, offer=OFFER, response_available=True, synchron=synchron)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert MIN_OFFER <= bonus_resp
            assert bonus_resp <=  tasks.MAX_BONUS + (MAX_GAIN - OFFER)
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == OFFER

def test_webhook(client, treatment, resp_feedback_fields=None):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    job_id = "test"
    resp_worker_id = generate_worker_id("webhook_resp")
    prop_worker_id = generate_worker_id("webhook_prop")
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
    emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, worker_id=resp_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    _process_prop(client, treatment, job_id=job_id, worker_id=prop_worker_id, offer=get_offer(), response_available=True)
    emit_webhook(client, url=f"/{treatment}/webhook/", treatment=treatment, worker_id=prop_worker_id, by_get=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        assert is_worker_available(resp_worker_id, get_table("resp", job_id=job_id, schema="result", treatment=treatment))
        assert is_worker_available(prop_worker_id, get_table("prop", job_id=job_id, schema="result", treatment=treatment))

def test_auto_finalize(client, treatment, resp_feedback_fields=None):
    # Test automatic webhook triggering to finalize tasks
    job_id = "test"
    resp_worker_id = generate_worker_id("auto_resp")
    prop_worker_id = generate_worker_id("auto_prop")
    _process_resp(client, treatment, job_id=job_id, worker_id=resp_worker_id, min_offer=get_min_offer(), resp_feedback_fields=resp_feedback_fields)
    process_tasks(client, job_id=job_id, worker_id=resp_worker_id, bonus_mode="random", url_kwargs={"auto_finalize": 1, "treatment": treatment})
    time.sleep(WEBHOOK_DELAY)
    res = _process_prop(client, treatment, job_id=job_id, worker_id=prop_worker_id, offer=get_offer(), response_available=True, auto_finalize=True)
    time.sleep(WEBHOOK_DELAY)
    with app.app_context():
        assert is_worker_available(resp_worker_id, get_table("resp", job_id=job_id, schema="result", treatment=treatment))
        assert is_worker_available(prop_worker_id, get_table("prop", job_id=job_id, schema="result", treatment=treatment))


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



def test_survey_no_workerid(client, treatment):
    for _ in range(TASK_REPETITION_LOWER):
        with app.app_context():
            assignment_id = generate_worker_id().upper().replace("_", "")
            path = f"/survey/{treatment}/?assignment_id={assignment_id}&preview=true"
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
                print("RESULT", res.data)
                # assert b"Your survey completion code is:" in res.data
                # assert b"dropped" not in res.data