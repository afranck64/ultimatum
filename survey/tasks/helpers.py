import unittest
import random
import string
import json
import numpy as np

from flask import session

from survey._app import app
from . import cg, crt, eff, goat, cpc, exp, risk, cc, ras

#NOTE:
# - The tasks are run after the responder task and the responder round can therefore be finalize at the end of the hexaco task
# - The responder's turn is internaly closed on the last task: by passing the query-parms auto_finalize=1 and treatment=$TXX

def process_tasks(client, job_id="test", worker_id=None, bonus_mode="full", url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param url_kwars: (dict)
    """
    non_final_tasks = app.config["TASKS"][:-1]
    if worker_id is None:
        worker_id = generate_worker_id("tasks")
    if "cc" in non_final_tasks:
        _process_cc(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "cg" in non_final_tasks:
        _process_cg(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "cpc" in non_final_tasks:
        _process_cpc(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "crt" in non_final_tasks:
        _process_crt(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "eff" in non_final_tasks:
        _process_eff(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "goat" in non_final_tasks:
        _process_goat(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "hexaco" in non_final_tasks:
        _process_hexaco(client, job_id, worker_id=worker_id)
    if "risk" in non_final_tasks:
        _process_risk(client, job_id, worker_id=worker_id, bonus_mode=bonus_mode)
    if "exp" in non_final_tasks:
        _process_exp(client, job_id, worker_id=worker_id)
    if "ras" in non_final_tasks:
        _process_ras(client, job_id, worker_id=worker_id)
    
    final_task = app.config["TASKS"][-1]
    handler = globals().get(f"_process_{final_task}")
    handler(client, job_id=job_id, worker_id=worker_id, url_kwargs=url_kwargs)

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
    path_check = f"/tasks/cc/check/?job_id={job_id}&worker_id={worker_id}"
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
        clicked = [letter==cc.LETTER_SIGNAL for letter in letters]
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

def _process_exp(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    exp_value = int(100 * (1 - np.random.power(10)))
    if worker_id is None:
        worker_id = generate_worker_id("exp")
    path = f"/tasks/exp/?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    data = {field:str(exp_value) for field in exp.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data


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

def _process_ras(client, job_id="test", worker_id=None, bonus_mode="random", clear_session=True, url_kwargs=None):
    """
    :param client: (flask.testclient)
    :param job_id: (str)
    :param worker_id: (str)
    :param bonus_mode: (str: random|full|none)
    :param clear_session: (bool)
    """
    if worker_id is None:
        worker_id = generate_worker_id("ras")
    path = f"/tasks/ras/?job_id={job_id}&worker_id={worker_id}"
    if url_kwargs:
        for k,v in url_kwargs.items():
            path += f"&{k}={v}"
        app.logger.debug("PATH: " + str(path))
    data = {field:random.choice(list(ras.SCALAS)) for field in ras.FIELDS}
    with app.test_request_context(path):
        if clear_session:
            with client:
                with client.session_transaction() as sess:
                    sess.clear()
        client.get(path)
        return client.post(path, data=data, follow_redirects=True).data


def generate_worker_id(base="test", k=10):
    return f"{base}_" + "".join(random.choices(string.ascii_lowercase+string.digits, k=k))


__all__ = ["_process_cc", "_process_cg", "_process_cpc", "_process_crt", "_process_eff", "_process_exp", "_process_goat", "_process_hexaco", "_process_risk", "_process_ras", "process_tasks", "generate_worker_id"]