import os
import time
import unittest

from flask import jsonify

from survey import tasks
from survey.utils import get_worker_bonus

from tests.test_survey import app, client, generate_worker_id, emit_webhook
from tests.test_survey.test_tasks import process_tasks


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]

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

def test_index(client):
    for _ in range(3):
        worker_id = generate_worker_id("index_resp")
        path = f"/{TREATMENT}/?worker_id={worker_id}"
        with app.test_request_context(path):
            res = client.get(path, follow_redirects=True).data
            assert b"RESPONDER" in res
            res = _process_resp_tasks(client, worker_id=worker_id)
            assert b"resp:" in res.data
            res = client.get(path, follow_redirects=True).data
            assert b"PROPOSER" in res
            res = _process_prop_round(client, worker_id=worker_id)
            assert b"prop:" in res.data
    
    # worker_id = generate_worker_id("index_resp")
    # path = f"/{TREATMENT}/?worker_id={worker_id}"
    # with app.test_request_context(path):
    #     res = client.get(path, follow_redirects=True).data
    #     assert b"RESPONDER" in res
    #     _process_resp_tasks(client, worker_id=worker_id)
    #     worker_id = generate_worker_id("index_prop")
    #     path = f"/{TREATMENT}/?worker_id={worker_id}"
    #     res = client.get(path, follow_redirects=True).data
    #     assert b"PROPOSER" in res
    #     _process_prop_round(client, worker_id=worker_id, path=path)
    
        


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
    path = f"/{TREATMENT}/prop/?job_id=test&worker_id={worker_id}"
    _process_resp_tasks(client, worker_id=None)
    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{TREATMENT}/prop/check/?offer=100").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def _process_prop(client, job_id="test", worker_id=None, offer=100, clear_session=True, response_available=False, path=None):
    if worker_id is None:
        worker_id = generate_worker_id("prop")
    if path is None:
        path = f"/{TREATMENT}/prop/?job_id={job_id}&worker_id={worker_id}"
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
    emit_webhook(client, url=webhook_url, job_id=job_id, worker_id=worker_id)
    return res



def test_prop_done(client):
    res = _process_prop(client)
    assert b"prop:" in res.data
    res = _process_prop(client)
    assert b"prop:" in res.data
    res = _process_prop(client)
    assert b"prop:" in res.data
    res = _process_prop(client)
    assert b"prop:" in res.data



def test_bonus_delayed(client, synchron=False):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(3):
        job_id = "test"
        resp_worker_id = generate_worker_id("resp")
        prop_worker_id = generate_worker_id("prop")
        _process_resp_tasks(client, worker_id=resp_worker_id, min_offer=100, bonus_mode="full", synchron=synchron)
        time.sleep(0.25)
        _process_prop_round(client, worker_id=prop_worker_id, offer=100, response_available=True, synchron=synchron)
        time.sleep(0.25)
        with app.app_context():
            bonus_resp = get_worker_bonus(job_id, resp_worker_id)
            assert bonus_resp == tasks.MAX_BONUS + 100
            bonus_prop = get_worker_bonus(job_id, prop_worker_id)
            assert bonus_prop == 100

def test_bonus_nodelay(client, synchron=True):
    # In real conditions, the tasks/webhook are delayed with +500 ms
    for _ in range(3):
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