import unittest
import random
import string
import json

from flask import session

from tests.test_survey import client, app, generate_worker_id
from survey.tasks import cg, crt, eff, goat, cpc, exp, risk, cc
from survey.tasks.helpers import (_process_cc, _process_cg, _process_cpc, _process_crt, _process_eff, _process_exp, _process_goat,
    _process_hexaco, _process_risk)
from survey.utils import get_worker_bonus

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


def test_cpc(client):
    res = _process_cpc(client)
    assert b"cpc:" in res


def test_cc(client):
    res = _process_cc(client)
    assert b"cc:" in res


def test_exp(client):
    res = _process_exp(client)
    assert b"exp:" in res


def test_risk(client):
    res = _process_risk(client)
    assert b"risk:" in res
