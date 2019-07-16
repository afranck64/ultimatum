import unittest
import random
import string

from flask import session

from tests.test_survey import client, app, generate_worker_id
from survey.db import get_db
from survey.utils import get_worker_bonus
from survey.admin import get_job_config


def test_get_job_config():
    job_id = "--------"
    with app.app_context():
        job_config = get_job_config(get_db(), job_id=job_id)
        assert job_config["job_id"] == job_id
        assert "api_key" in job_config
        assert "nb_rows" in job_config
        assert "unique_worker" in job_config
        assert "base_code" in job_config
        assert "expected_judgments" in job_config
        assert len(job_config) == 6


def test_index(client):
    path = f"/admin"
    job_id="test_index_job"
    api_key="api_key"
    secret = app.config["ADMIN_SECRET"]
    base_code = "base_code"
    expected_judgments = 16
    with app.test_request_context(path):
        # if clear_session:
        #     with client:
        #         with client.session_transaction() as sess:
        #             sess.clear()
        client.get(path, follow_redirects=True)
        return client.post(path, data={"job_id":job_id, api_key:"api_key", "secret": secret, "base_code": base_code, "expected_judgments": expected_judgments}, follow_redirects=True)
    job_config = get_job_config(get_db(), job_id)
    assert job_config["job_id"] == job_id
    assert job_config["base_code"] == base_code
    assert job_config["api_key"] == api_key
    assert job_config["expected_judgments"] == expected_judgments

    expected_judgments = 32
    base_code = "super_base_code"
    job_config["expected_judgments"] = expected_judgments
    job_config["base_code"] = base_code
    with app.test_request_context(path):
        client.get(path, follow_redirects=True)
        return client.post(path, data=job_config, follow_redirects=True)
