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

from tests.test_survey import client
from tests.test_survey import txx_auto_prop as txx


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]
COMPLETION_CODE_PREFIX = "respNF:"
RESP_FEEDBACK_FIELDS = [
    "feedback_alternative",
    "feedback_fairness",
    "feedback_accuracy",
    "feedback_ai_offers",
    "feedback_fairness_against_ai"
]
# NOTE: no proposal should be externally triggered in treatments t2x

def test_available():
    txx.test_available(TREATMENT)

def test_index(client):
    txx.test_index(client, TREATMENT, completion_code_prefix=COMPLETION_CODE_PREFIX, resp_feedback_fields=RESP_FEEDBACK_FIELDS)


def test_resp_index(client):
    txx.test_resp_index(client, TREATMENT)

def test_resp_done_success(client):
    txx.test_resp_done_success(client, TREATMENT, completion_code_prefix=COMPLETION_CODE_PREFIX, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_resp_done_both_models(client):
    txx.test_resp_done_both_models(client, TREATMENT, completion_code_prefix=COMPLETION_CODE_PREFIX, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_prop_index(client):
    txx.test_prop_index(client, TREATMENT, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

# def test_prop_check(client):
#     txx.test_prop_check(client, TREATMENT)

# def test_prop_done(client):
#     txx.test_prop_done(client, TREATMENT)


def test_bonus_delayed(client, synchron=False):
    txx.test_bonus_delayed(client, TREATMENT, synchron, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_bonus_nodelay(client, synchron=True):
    txx.test_bonus_nodelay(client, TREATMENT, synchron, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_webhook(client):
    txx.test_webhook(client, TREATMENT, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_auto_finalize(client):
    txx.test_auto_finalize(client, TREATMENT, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_payment(client):
    txx.test_payment(client, TREATMENT, resp_feedback_fields=RESP_FEEDBACK_FIELDS)

def test_survey_resp(client):
    txx.test_survey_resp(client, TREATMENT)

def test_survey_prop(client):
    txx.test_survey_prop(client, TREATMENT)

# def test_prop_check_done(client):
#     txx.test_prop_check_done(client, TREATMENT)

def test_survey_drop(client):
    txx.test_survey_drop(client, TREATMENT)

def test_survey_unique(client):
    txx.test_survey_unique(client, TREATMENT)