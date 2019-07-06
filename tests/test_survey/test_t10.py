import os
import unittest

from flask import jsonify

from survey.t10.prop import insert_row, HHI_Prop_ADM, prop_to_prop_result
from survey.t10.resp import HHI_Resp_ADM, resp_to_resp_result
from tests.test_survey import client
from tests.test_survey import app
from tests.test_survey.test_tasks import process_tasks


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]

def _process_resp(client, worker_id="na", clear_session=True):
    path = f"/{TREATMENT}/resp/?worker_id={worker_id}"
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={"min_offer":100}, follow_redirects=True)

def test_index(client):
    path = f"/{TREATMENT}"
    with app.test_request_context(path):
        res = client.get(path, follow_redirects=True).data
        assert b"RESPONDER" in res
        process_tasks(client)
        _process_resp(client)
        res = client.get(path, follow_redirects=True).data
        assert b"PROPOSER" in res
        


def test_resp_index(client):
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"RESPONDER" in res

def test_resp_done_success(client):
    process_tasks(client, worker_id="na")
    res = _process_resp(client).data
    assert b"resp:" in res

def test_resp_done_both_models(client):
    process_tasks(client, worker_id="na")
    res = _process_resp(client, worker_id="na").data
    assert b"resp:" in res

    process_tasks(client, worker_id="1")
    res = _process_resp(client, worker_id="1").data
    assert b"resp:" in res

def test_prop_index(client):
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"PROPOSER" in res

def test_prop_check(client):
    path = f"/{TREATMENT}/prop/"
    
    process_tasks(client)
    _process_resp(client)

    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{path}check/?offer=100").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def _process_prop(client, worker_id="na", clear_session=True):
    path = f"/{TREATMENT}/prop/?worker_id={worker_id}"
    process_tasks(client, worker_id=worker_id)
    _process_resp(client, worker_id=worker_id)
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={"offer":100}, follow_redirects=True).data

def test_prop_done(client):
    res = _process_prop(client, worker_id="na")
    assert b"prop:" in res
    res = _process_prop(client, worker_id="1")
    assert b"prop:" in res
    res = _process_prop(client, worker_id="2")
    assert b"prop:" in res
    res = _process_prop(client, worker_id="3")
    assert b"prop:" in res
