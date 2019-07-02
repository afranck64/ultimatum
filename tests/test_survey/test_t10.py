import os
import unittest

from flask import jsonify

from tests.test_survey import client
from tests.test_survey import app
from survey.t10.prop import insert_row, HHI_Prop_ADM, prop_to_prop_result
from survey.t10.resp import HHI_Resp_ADM, resp_to_resp_result


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]

def _process_resp(client):
    with app.test_request_context(f"/{TREATMENT}/resp"):
        client.get(f"/{TREATMENT}/resp/")
        return client.post(f"/{TREATMENT}/resp/", data={"min_offer":100}, follow_redirects=True)

def test_index(client):
    path = f"/{TREATMENT}"
    with app.test_request_context(path):
        res = client.get(path, follow_redirects=True).data
        assert b"RESPONDER" in res

        _process_resp(client)
        res = client.get(path, follow_redirects=True).data
        assert b"PROPOSER" in res
        


def test_resp_index(client):
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"RESPONDER" in res

def test_resp_done(client):
    res = _process_resp(client).data
    assert b"resp:" in res


def test_prop_index(client):
    res = client.get(f"/{TREATMENT}/resp/").data
    assert b"PROPOSER" in res

def test_prop_check(client):
    path = f"/{TREATMENT}/prop/"
    
    _process_resp(client)

    with app.test_request_context(path):
        client.get(path)
        res = client.get(f"{path}check/?offer=100").data
        assert b"acceptance_probability" in res
        assert b"best_offer_probability" in res

def test_prop_done(client):
    path = f"/{TREATMENT}/prop/"

    _process_resp(client)

    with app.test_request_context(path):
        client.get(path)
        res = client.post(path, data={"offer":100}, follow_redirects=True).data
        assert b"prop:" in res
