import unittest
import random
import string

from flask import session

from tests.test_survey import client, app, generate_worker_id
from survey.tasks import cg, crt, eff, risk
from survey.utils import get_worker_bonus

#NOTE:
# - The hexaco tasks is run as the last one for feature generation
# - The tasks are run after the responder task and the responder round can therefore be finalize at the end of the hexaco task

def process_tasks(client, job_id="test", worker_id=None, bonus_mode="full", url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param url_kwars: (dict)
    """
    if worker_id is None:
        worker_id = generate_worker_id("tasks")
    _process_cg(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_crt(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_eff(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_risk(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_hexaco(client, job_id, worker_id=worker_id, url_kwargs=url_kwargs)

def _process_cg(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    if worker_id is None:
        worker_id = generate_worker_id("cg")
    path = f"/tasks/cg/?job_id={job_id}&worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.choice([0, 5, 10, 15, 20]) if random.random()>0.6 else 0 for field in cg.FIELDS}
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
    with app.app_context():
        worker_id = generate_worker_id("cg")
        res = _process_cg(client, worker_id=worker_id, bonus_mode="full")
        assert b"cg:" in res
        assert get_worker_bonus("test", worker_id) == cg.MAX_BONUS
        worker_id = generate_worker_id("cg")
        res = _process_cg(client, worker_id=worker_id, bonus_mode="random")
        assert b"cg:" in res
        res = _process_cg(client, worker_id=worker_id, bonus_mode="none")
        worker_id = generate_worker_id("cg")
        assert b"cg:" in res
        assert get_worker_bonus("test", worker_id) == 0


def _process_crt(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    if worker_id is None:
        worker_id = generate_worker_id("crt")
    path = f"/tasks/crt/?job_id={job_id}&worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.randint(0, 100) if random.random() > 0.6 else crt.SOLUTIONS[field] for field in crt.SOLUTIONS}
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
    with app.app_context():
        worker_id = generate_worker_id("crt")
        res = _process_crt(client, worker_id=worker_id, bonus_mode="full")
        assert b"crt:" in res
        assert get_worker_bonus("test", worker_id) == crt.MAX_BONUS
        worker_id = generate_worker_id("crt")
        res = _process_crt(client, worker_id=worker_id, bonus_mode="random")
        assert b"crt:" in res
        worker_id = generate_worker_id("crt")
        res = _process_crt(client, worker_id=worker_id, bonus_mode="none")
        assert b"crt:" in res
        assert get_worker_bonus("test", worker_id) == 0

def _process_eff(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    """
    if worker_id is None:
        worker_id = generate_worker_id("eff")
    #worker_id = generate_worker_id("eff_FORCED")
    path = f"/tasks/eff/?job_id={job_id}&worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:"".join(random.choices(string.ascii_lowercase, k=4)) if random.random()>0.6 else eff.SOLUTIONS[field] for field in eff.SOLUTIONS}
    elif bonus_mode=="none":
        data = {field: "----" for field in eff.SOLUTIONS}
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
    with app.app_context():
        worker_id = generate_worker_id("eff")
        res = _process_eff(client, worker_id=worker_id, bonus_mode="full")
        assert b"eff:" in res
        assert get_worker_bonus("test", worker_id) == eff.MAX_BONUS
        res = _process_eff(client, worker_id=worker_id, bonus_mode="random")
        worker_id = generate_worker_id("eff")
        assert b"eff:" in res
        res = _process_eff(client, worker_id=worker_id, bonus_mode="none")
        worker_id = generate_worker_id("eff")
        assert b"eff:" in res
        assert get_worker_bonus("test", worker_id) == 0

def _process_hexaco(client, job_id="test", worker_id=None, clear_session=True, url_kwargs=None):
    if worker_id is None:
        worker_id = generate_worker_id("hexaco")
    path = f"/tasks/hexaco/?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
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
    with app.app_context():
        worker_id = generate_worker_id("hexaco")
        res = _process_hexaco(client, worker_id=worker_id)
        assert b"hexaco:" in res
        assert get_worker_bonus("test", worker_id) == 0
        worker_id = generate_worker_id("hexaco")
        res = _process_hexaco(client, worker_id=worker_id)
        assert b"hexaco:" in res
        worker_id = generate_worker_id("hexaco")
        res = _process_hexaco(client, worker_id=worker_id)
        assert b"hexaco:" in res
        assert get_worker_bonus("test", worker_id) == 0

def _process_risk(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("risk")
    path = f"/tasks/risk/?job_id={job_id}&worker_id={worker_id}"
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
        with app.test_request_context(f"/tasks/risk/check/?job_id={job_id}&woker_id={worker_id}"):
            for key, value in data.items():
                if value:
                    client.get(f"/tasks/risk/check/?job_id={job_id}&worker_id={worker_id}&cell={key}")
        return client.post(path, data=data, follow_redirects=True).data

def test_risk(client):
    res = _process_risk(client)
    assert b"risk:" in res

def test_risk_bonus(client):
    with app.app_context():
        worker_id = generate_worker_id("risk")
        res = _process_risk(client, worker_id=worker_id, bonus_mode="full")
        assert b"risk:" in res
        assert get_worker_bonus("test", worker_id) == risk.MAX_BONUS
        worker_id = generate_worker_id("risk")
        res = _process_risk(client, worker_id=worker_id, bonus_mode="random")
        assert b"risk:" in res
        worker_id = generate_worker_id("risk")
        res = _process_risk(client, worker_id=worker_id, bonus_mode="none")
        assert b"risk:" in res
        assert get_worker_bonus("test", worker_id) == 0

def test_tasks_bonus(client):
    job_id = "test"
    worker_id = generate_worker_id("tasks")
    with app.app_context():
        _process_cg(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus = cg.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_crt(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += crt.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_eff(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += eff.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_hexaco(client, worker_id=worker_id)
        exp_bonus += 0  #NO bonus for hexaco actually
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_risk(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += risk.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
    worker_id = generate_worker_id("tasks")
    with app.app_context():
        _process_cg(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus = cg.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_crt(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += crt.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_eff(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += eff.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_hexaco(client, worker_id=worker_id)
        exp_bonus += 0  #NO bonus for hexaco actually
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
        _process_risk(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += risk.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus