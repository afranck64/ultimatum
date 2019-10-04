import unittest
import random
import string
import json

from flask import session

from tests.test_survey import client, app, generate_worker_id
from survey.tasks import cg, crt, eff, goat, cpc, exp, risk, cc
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
    # _process_cg(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    # _process_crt(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    # _process_eff(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    # _process_goat(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    # _process_hexaco(client, job_id, worker_id=worker_id, url_kwargs=url_kwargs)
    _process_cc(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_exp(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_risk(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    _process_cpc(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode, url_kwargs=url_kwargs)

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
        worker_id = generate_worker_id("cg")
        res = _process_cg(client, worker_id=worker_id, bonus_mode="none")
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
        worker_id = generate_worker_id("eff")
        res = _process_eff(client, worker_id=worker_id, bonus_mode="random")
        assert b"eff:" in res
        worker_id = generate_worker_id("eff")
        res = _process_eff(client, worker_id=worker_id, bonus_mode="none")
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

def _process_goat(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("goat")
    path = f"/tasks/goat/?job_id={job_id}&worker_id={worker_id}"
    if bonus_mode=="random":
        data = {field:random.randint(0, 1) for field in goat.FIELDS}
    elif bonus_mode=="none":
        data = {field:0 for field in goat.FIELDS}
    else:
        data = {field:1 for field in goat.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        with app.test_request_context(f"/tasks/goat/check/?job_id={job_id}&woker_id={worker_id}"):
            for key, value in data.items():
                if value:
                    client.get(f"/tasks/goat/check/?job_id={job_id}&worker_id={worker_id}&cell={key}")
        return client.post(path, data=data, follow_redirects=True).data

def test_goat(client):
    res = _process_goat(client)
    assert b"goat:" in res

def test_goat_bonus(client):
    with app.app_context():
        worker_id = generate_worker_id("goat")
        res = _process_goat(client, worker_id=worker_id, bonus_mode="full")
        assert b"goat:" in res
        assert get_worker_bonus("test", worker_id) == goat.MAX_BONUS
        worker_id = generate_worker_id("goat")
        res = _process_goat(client, worker_id=worker_id, bonus_mode="random")
        assert b"goat:" in res
        worker_id = generate_worker_id("goat")
        res = _process_goat(client, worker_id=worker_id, bonus_mode="none")
        assert b"goat:" in res
        assert get_worker_bonus("test", worker_id) == 0

def test_tasks_bonus(client):
    job_id = "test"
    worker_id = generate_worker_id("tasks")
    with app.app_context():
        _process_cg(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus = cg.MAX_BONUS
        print("worker_id:", worker_id, "bonus: ", exp_bonus)
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
        _process_goat(client, worker_id=worker_id, bonus_mode="full")
        exp_bonus += goat.MAX_BONUS
        assert get_worker_bonus(job_id, worker_id) == exp_bonus
    # worker_id = generate_worker_id("tasks")
    # with app.app_context():
    #     _process_cg(client, worker_id=worker_id, bonus_mode="full")
    #     exp_bonus = cg.MAX_BONUS
    #     assert get_worker_bonus(job_id, worker_id) == exp_bonus
    #     _process_crt(client, worker_id=worker_id, bonus_mode="full")
    #     exp_bonus += crt.MAX_BONUS
    #     assert get_worker_bonus(job_id, worker_id) == exp_bonus
    #     _process_eff(client, worker_id=worker_id, bonus_mode="full")
    #     exp_bonus += eff.MAX_BONUS
    #     assert get_worker_bonus(job_id, worker_id) == exp_bonus
    #     _process_hexaco(client, worker_id=worker_id)
    #     exp_bonus += 0  #NO bonus for hexaco actually
    #     assert get_worker_bonus(job_id, worker_id) == exp_bonus
    #     _process_goat(client, worker_id=worker_id, bonus_mode="full")
    #     exp_bonus += goat.MAX_BONUS
    #     assert get_worker_bonus(job_id, worker_id) == exp_bonus


def _process_cpc(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("cpc")
    path = f"/tasks/cpc/?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    if bonus_mode=="random":
        data = {field:random.choice(["A", "B"]) for field in cpc.FIELDS}
    elif bonus_mode=="none":
        data = {field:"A" for field in cpc.FIELDS}
    else:
        data = {field:"B" for field in cpc.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_cpc(client):
    res = _process_cpc(client)
    assert b"cpc:" in res



def _process_cc(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("cc")
    path = f"/tasks/cc/?job_id={job_id}&worker_id={worker_id}"
    path_check = f"/tasks/cc/check?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    letters = list(cc.ITEMS)
    random.shuffle(letters)
    delays = [random.randint(0, 1000) for _ in letters]
    data = dict()
    if bonus_mode=="random":
        clicked = [random.choice([True, False]) for _ in letters]
    elif bonus_mode=="none":
        clicked = [False] * len(letters)
    else:
        clicked = [letter==cc.LETTER_M for letter in letters]
    data = json.dumps({
        "letters": letters,
        "delays": delays,
        "clicked": clicked,
    })
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        client.post(path_check, data=data, follow_redirects=True)
        return client.post(path, follow_redirects=True).data

def test_cc(client):
    res = _process_cc(client)
    assert b"cc:" in res


def _process_exp(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("exp")
    path = f"/tasks/exp/?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    data = {field:random.choice(["0", "1", "2", "3"]) for field in exp.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_exp(client):
    res = _process_exp(client)
    assert b"exp:" in res


def _process_risk(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
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
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    data = {field:random.randint(1, len(risk.FIELDS)) for field in risk.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data

def test_risk(client):
    res = _process_risk(client)
    assert b"risk:" in res

# def test_cpc_bonus(client):
#     with app.app_context():
#         worker_id = generate_worker_id("cpc")
#         res = _process_cpc(client, worker_id=worker_id, bonus_mode="full")
#         assert b"cpc:" in res
#         assert get_worker_bonus("test", worker_id) == cpc.MAX_BONUS
#         worker_id = generate_worker_id("cpc")
#         res = _process_cpc(client, worker_id=worker_id, bonus_mode="random")
#         assert b"cpc:" in res
#         worker_id = generate_worker_id("cpc")
#         res = _process_cpc(client, worker_id=worker_id, bonus_mode="none")
#         assert b"cpc:" in res
#         assert get_worker_bonus("test", worker_id) == 0