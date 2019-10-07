import unittest
import random
import string
import json

from flask import session

from survey.db import get_db
from survey.utils import get_table
from tests.test_survey import client, app, generate_worker_id
from survey.tasks import cg, crt, eff, goat, cpc, exp, risk, cc, hexaco, ras
from survey.tasks.helpers import (_process_cc, _process_cg, _process_cpc, _process_crt, _process_eff, _process_exp, _process_goat,
    _process_hexaco, _process_risk, generate_worker_id, _process_ras)
from survey.utils import get_worker_bonus, is_worker_available

def has_worker_and_features(base, task_module, job_id,  worker_id):
    con = get_db()
    table = get_table(base, job_id, "result")
    features = [feature for feature in task_module.FEATURES]
    sql = f"SELECT {','.join(features)} FROM {table} WHERE job_id=? AND worker_id=?"
    res = con.execute(sql, [job_id, worker_id])
    return res is not None

def test_cg(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_cg(client, job_id=job_id, worker_id=worker_id)
        assert b"cg:" in res
        assert is_worker_available(worker_id, get_table("cg", job_id, "result"))
        assert has_worker_and_features("cg", cg, job_id, worker_id)

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


def test_crt(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_crt(client, job_id=job_id, worker_id=worker_id)
        assert b"crt:" in res
        assert is_worker_available(worker_id, get_table("crt", job_id, "result"))
        assert has_worker_and_features("crt", crt, job_id, worker_id)


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


def test_eff(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_eff(client, job_id=job_id, worker_id=worker_id)
        assert b"eff:" in res
        assert is_worker_available(worker_id, get_table("eff", job_id, "result"))
        assert has_worker_and_features("eff", eff, job_id, worker_id)


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


def test_hexaco(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_hexaco(client, job_id=job_id, worker_id=worker_id)
        assert b"hexaco:" in res
        assert is_worker_available(worker_id, get_table("hexaco", job_id, "result"))
        assert has_worker_and_features("hexaco", hexaco, job_id, worker_id)


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


def test_goat(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_goat(client, job_id=job_id, worker_id=worker_id)
        assert b"goat:" in res
        assert is_worker_available(worker_id, get_table("goat", job_id, "result"))
        assert has_worker_and_features("goat", goat, job_id, worker_id)


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


def test_cpc(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_cpc(client, job_id=job_id, worker_id=worker_id)
        assert b"cpc:" in res
        assert is_worker_available(worker_id, get_table("cpc", job_id, "result"))
        assert has_worker_and_features("cpc", cpc, job_id, worker_id)


def test_cc(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_cc(client, job_id=job_id, worker_id=worker_id)
        assert b"cc:" in res
        assert is_worker_available(worker_id, get_table("cc", job_id, "result"))
        assert has_worker_and_features("cc", cc, job_id, worker_id)


def test_exp(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_exp(client, job_id=job_id, worker_id=worker_id)
        assert b"exp:" in res
        assert is_worker_available(worker_id, get_table("exp", job_id, "result"))
        assert has_worker_and_features("exp", exp, job_id, worker_id)


def test_risk(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_risk(client, job_id=job_id, worker_id=worker_id)
        assert b"risk:" in res
        assert is_worker_available(worker_id, get_table("risk", job_id, "result"))
        assert has_worker_and_features("risk", risk, job_id, worker_id)


def test_ras(client):
    with app.app_context():
        job_id = "test"
        worker_id = generate_worker_id("task")
        res = _process_ras(client, job_id=job_id, worker_id=worker_id)
        assert b"ras:" in res
        assert is_worker_available(worker_id, get_table("ras", job_id, "result"))
        assert has_worker_and_features("ras", ras, job_id, worker_id)
