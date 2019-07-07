import unittest
import random

from flask import session

from tests.test_survey import client, app
from survey.tasks import cg, crt, eff, risk

def process_tasks(client, worker_id="na", bonus_mode="random"):
    _process_cg(client, worker_id, bonus_mode)
    _process_crt(client, worker_id, bonus_mode)
    _process_eff(client, worker_id, bonus_mode)
    _process_hexaco(client, worker_id)
    _process_risk(client, worker_id, bonus_mode)

def _process_cg(client, worker_id="na", bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    path = f"/tasks/cg/?worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.choice([0, 5, 10, 15, 20]) for field in cg.FIELDS}
    elif bonus_mode=="none":
        data = {field:20 for field in cg.FIELDS}
    elif bonus_mode=="full":
        data = {field:0 for field in cg.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_cg(client):
    res = _process_cg(client)
    assert b"cg:" in res

def test_cg_bonus(client):
    res = _process_cg(client, worker_id="cg1", bonus_mode="full")
    assert b"cg:" in res
    assert b"60 CENTS" in res
    res = _process_cg(client, worker_id="cg2", bonus_mode="random")
    assert b"cg:" in res
    res = _process_cg(client, worker_id="cg3", bonus_mode="none")
    assert b"cg:" in res
    assert b"0 CENTS" in res


def _process_crt(client, worker_id="na", bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    path = f"/tasks/crt/?worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.randint(0, 100) for field in crt.SOLUTIONS}
    elif bonus_mode=="none":
        data = {field:0 for field in crt.SOLUTIONS}
    else:
        data = crt.SOLUTIONS
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_crt(client):
    res = _process_crt(client)
    assert b"crt:" in res
    
def test_crt_bonus(client):
    res = _process_crt(client, worker_id="crt1", bonus_mode="full")
    assert b"crt:" in res
    assert b"45 CENTS" in res
    res = _process_crt(client, worker_id="crt2", bonus_mode="random")
    assert b"crt:" in res
    res = _process_crt(client, worker_id="crt3", bonus_mode="none")
    assert b"crt:" in res
    assert b"0 CENTS" in res

def _process_eff(client, worker_id="na", bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    path = f"/tasks/eff/?worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.randint(0, 100) for field in eff.SOLUTIONS}
    elif bonus_mode=="none":
        data = {field:0 for field in eff.SOLUTIONS}
    else:
        data = {field: str(solution) for field, solution in eff.SOLUTIONS.items()}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_eff(client):
    res = _process_eff(client)
    assert b"eff:" in res

def test_eff_bonus(client):
    res = _process_eff(client, worker_id="eff1", bonus_mode="full")
    assert b"eff:" in res
    assert b"40 CENTS" in res
    res = _process_eff(client, worker_id="eff2", bonus_mode="random")
    assert b"eff:" in res
    res = _process_eff(client, worker_id="eff3", bonus_mode="none")
    assert b"eff:" in res
    assert b"0 CENTS" in res

def _process_hexaco(client, worker_id="na", clear_session=True):
    path = f"/tasks/hexaco/?worker_id={worker_id}"
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data={f"q{qid}": random.randint(1, 5) for qid in range(1, 31)}, follow_redirects=True).data

def test_hexaco(client):
    res = _process_hexaco(client)
    assert b"hexaco:" in res

def disabled__test_hexaco_bonus():
    res = _process_hexaco(client, worker_id="hexaco1")
    assert b"hexaco:" in res
    res = _process_hexaco(client, worker_id="hexaco2")
    assert b"hexaco:" in res
    res = _process_hexaco(client, worker_id="hexaco3")
    assert b"hexaco:" in res

def _process_risk(client, worker_id="na", bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    path = f"/tasks/risk/?worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.randint(0, 1) for field in risk.FIELDS}
    elif bonus_mode=="none":
        data = {field:0 for field in risk.FIELDS}
    else:
        data = {field:1 for field in risk.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        with app.test_request_context(f"/tasks/risk/check/?woker_id={worker_id}"):
            for key, value in data.items():
                if value:
                    client.get(f"/tasks/risk/check/?worker_id={worker_id}&cell={key}")
        return client.post(path, data=data, follow_redirects=True).data

def test_risk(client):
    res = _process_risk(client)
    assert b"risk:" in res

def test_risk_bonus(client):
    res = _process_risk(client, worker_id="risk1", bonus_mode="full")
    assert b"risk:" in res
    assert b"1.0 USD" in res
    res = _process_risk(client, worker_id="risk2", bonus_mode="random")
    assert b"risk:" in res
    res = _process_risk(client, worker_id="risk3", bonus_mode="none")
    assert b"risk:" in res
    assert b"0 CENTS" in res
