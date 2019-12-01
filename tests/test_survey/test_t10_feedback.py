import os
import time
import unittest
from unittest import mock
import requests
import random
from flask import jsonify
from httmock import urlmatch, HTTMock, response

from core.models.metrics import MAX_GAIN
from survey import tasks
from survey.txx.survey import MainForm
from survey.utils import get_worker_bonus, get_worker_paid_bonus, get_total_worker_bonus, WORKER_CODE_DROPPED
from survey.t10_feedback.prop import df_prop

from tests.test_survey import client
from tests.test_survey import txx


TREATMENT = "t10_feedback"

def generate_worker_id_mock(*args):
    res = df_prop.sample(1).iloc[0]["worker_id"]
    # raise Exception(f"Stop: {res}")
    return res



def test_available():
    txx.test_available(TREATMENT)

@mock.patch("tests.test_survey.txx.generate_worker_id", new=generate_worker_id_mock)
def test_index(client):
    txx.test_index_feedback(client, TREATMENT, response_available=True)

@mock.patch("tests.test_survey.txx.generate_worker_id", new=generate_worker_id_mock)
def test_prop_index(client):
    txx.test_prop_index(client, TREATMENT, response_available=True)

@mock.patch("tests.test_survey.txx.generate_worker_id", new=generate_worker_id_mock)
def test_prop_check(client):
    txx.test_prop_check(client, TREATMENT, response_available=True)

@mock.patch("tests.test_survey.txx.generate_worker_id", new=generate_worker_id_mock)
@mock.patch("survey.txx.helpers.generate_worker_id", new=generate_worker_id_mock)
def test_prop_done(client):
    txx.test_prop_done(client, TREATMENT, response_available=True)


@mock.patch("tests.test_survey.txx.generate_worker_id", new=generate_worker_id_mock)
def test_survey_prop(client):
    txx.test_survey_prop(client, TREATMENT)

@mock.patch("survey.txx.helpers.generate_worker_id", new=generate_worker_id_mock)
def test_prop_check_done(client):
    txx.test_prop_check_done(client, TREATMENT, response_available=True)
