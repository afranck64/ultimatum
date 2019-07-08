import os
import unittest

from flask import jsonify

from survey import tasks
from survey.utils import get_worker_bonus

from tests.test_survey import app, client, generate_worker_id
from tests.test_survey.test_tasks import process_tasks


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]

def _process_resp(client, job_id="test", worker_id=None, min_offer=100, clear_session=True):
    if worker_id is None:
        worker_id = generate_worker_id()
    path = f"/{TREATMENT}/resp/?job_id={job_id}&worker_id={worker_id}"
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={"min_offer":min_offer}, follow_redirects=True)

def _process_resp_tasks(client, job_id="test", worker_id=None, min_offer=100, bonus_mode="random", clear_session=True):
    if worker_id is None:
        worker_id = generate_worker_id("resp")
    process_tasks(client, job_id=job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_resp(client, job_id=job_id, worker_id=worker_id, min_offer=min_offer, clear_session=clear_session)

def test_index(client):
    worker_id = generate_worker_id("index")
    path = f"/{TREATMENT}/?worker_id={worker_id}"
    with app.test_request_context(path):
        res = client.get(path, follow_redirects=True).data
        assert b"RESPONDER" in res
        _process_resp_tasks(client, worker_id=worker_id)
        res = client.get(path, follow_redirects=True).data
        assert b"PROPOSER" in res
        


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
    _process_resp_tasks(client)
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"PROPOSER" in res

def test_prop_check(client):
    worker_id = generate_worker_id("prop_check")
    path = f"/{TREATMENT}/prop/?worker_id={worker_id}"
    print("PATH: ", path)
    _process_resp_tasks(client, worker_id=None)
    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{TREATMENT}/prop/check/?offer=100").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def _process_prop(client, job_id="test", worker_id=None, offer=100, clear_session=True, response_available=False):
    path = f"/{TREATMENT}/prop/?job_id={job_id}&worker_id={worker_id}"
    if worker_id is None:
        worker_id = generate_worker_id()
    if not response_available:
        _process_resp_tasks(client)
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={"offer":offer}, follow_redirects=True).data

def test_prop_done(client):
    res = _process_prop(client)
    assert b"prop:" in res
    res = _process_prop(client)
    assert b"prop:" in res
    res = _process_prop(client)
    assert b"prop:" in res
    res = _process_prop(client)
    assert b"prop:" in res

def test_bonus(client):
    resp_worker_id = generate_worker_id("resp")
    prop_worker_id = generate_worker_id("prop")
    job_id = "test"
    _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=100, bonus_mode="random")
    _process_prop(client, worker_id=prop_worker_id, offer=100, response_available=True)
    with app.app_context():
        assert get_worker_bonus(job_id, resp_worker_id) == tasks.MAX_BONUS +    100
        assert get_worker_bonus(job_id, prop_worker_id) == 100


    resp_worker_id = generate_worker_id("resp2")
    prop_worker_id = generate_worker_id("prop2")
    job_id = "test"
    _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=100, bonus_mode="none")
    _process_prop(client, worker_id=prop_worker_id, offer=150, response_available=True)
    with app.app_context():
        assert get_worker_bonus(job_id, resp_worker_id) == 0 + 0 + 0 + 0 + 0 +    150
        assert get_worker_bonus(job_id, prop_worker_id) == 50

    resp_worker_id = generate_worker_id("resp3")
    prop_worker_id = generate_worker_id("prop3")
    job_id = "test"
    _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=101, bonus_mode="none")
    _process_prop(client, worker_id=prop_worker_id, offer=100, response_available=True)
    with app.app_context():
        assert get_worker_bonus(job_id, resp_worker_id) == 0 + 0 + 0 + 0 + 0 +    0
        assert get_worker_bonus(job_id, prop_worker_id) == 0
