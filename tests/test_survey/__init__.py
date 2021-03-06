import os
import tempfile
import random
import string
import json
import hashlib
import time

import pytest
from core.models.metrics import MAX_GAIN
from survey.app import app
from survey import db
from survey.db import get_db
from survey.utils import get_table
from survey.admin import get_job_config

BASE_DIR = os.path.split(os.path.split(os.path.split(__file__)[0])[0])[0]

KEEP_TESTS_RESULTS = False

def _client():
    app.config["ADMIN_SECRET"] = "secret"
    app.config["OUTPUT_DIR"] = os.path.join(BASE_DIR, "data", "output", "test")
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    dbs = ["DATABASE", "DATABASE_RESULT", "DATABASE_DATA"]
    dbs_fds = []
    for _db in dbs:
        if KEEP_TESTS_RESULTS:
            _fd, app.config[_db] = 0, os.path.join(BASE_DIR, "data", "output", "test", f"{_db.lower()}.sqlite3")
        else:
            _fd, app.config[_db] = tempfile.mkstemp(dir=os.path.join(BASE_DIR, "data", "output", "test"))
        dbs_fds.append(_fd)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    test_client = app.test_client()

    with app.app_context():
        db.init_db()

    yield test_client

    if not KEEP_TESTS_RESULTS:
        for _fd in dbs_fds:
            os.close(_fd)
        for _db in dbs:
            os.unlink(app.config[_db])


@pytest.fixture
def client():
    for test_client in _client():
        yield test_client

def get_client():
    return next(_client())
            


webhook_data_template =  {
    "signal": "new_judgments",
    "payload":{
        "id":2329205222,
        "data":{
            "ai_offer": f"{MAX_GAIN//2}",
            "min_offer":f"{MAX_GAIN//2}"
        },
        "judgments_count":1,
        "state":"finalized",
        "agreement":1.0,
        "missed_count":0,
        "gold_pool":None,
        "created_at":"2019-06-11T19:18:19+00:00",
        "updated_at":"2019-06-16T00:58:08+00:00",
        "job_id":1392288,
        "results": {
            "judgments":[
                {
                    "id":4900876098,
                    "created_at":"2019-06-16T00:57:58+00:00",
                    "started_at":"2019-06-16T00:56:09+00:00",
                    "acknowledged_at":None,
                    "external_type":"cf_internal",
                    "golden":False,
                    "missed":None,
                    "rejected":None,
                    "tainted":False,
                    "country":"GBR",
                    "region":"",
                    "city":"",
                    "unit_id":2329205222,
                    "job_id":1392288,
                    "worker_id":45314141,
                    "trust":1.0,
                    "worker_trust":1.0,
                    "unit_state":"finalized",
                    "data":{
                        "proposer":["correct"],
                        "responder":["correct"],
                        "prop_and_resp":["correct"],
                        "ai":["correct"],
                        "comp_code":"lAT2JV2QtTkEnH5A4syJ6N4tcNZod1O6",
                        "please_enter_your_comments_feedback_or_suggestions_below":"Thank you for everything. ^_^",
                        "id_user_agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/74.0.3729.169 Chrome/74.0.3729.169 Safari/537.36",
                        "_clicks":["http://tube.ddns.net/ultimatum/hhi_prop_adm?job_id=1392288&worker_id=45314141&unit_id=na"]
                    },
                    "unit_data":{
                        "ai_offer":f"{MAX_GAIN//2}",
                        "min_offer":f"{MAX_GAIN//2}"
                    }
                }
            ],
            "proposer":{
                "agg":"correct",
                "confidence":1.0
            },
            "responder":{
                "agg":"correct",
                "confidence":1.0
            },
            "prop_and_resp":{
                "agg":"correct",
                "confidence":1.0
            },
            "ai":{
                "agg":"correct",
                "confidence":1.0
            }
        }
    },
    "signature": ""
}

def emit_webhook(client, url, job_id="test", worker_id=None, signal="new_judgments", unit_state="finalized", treatment="t10", by_get=True):
    """
    :param client:
    :param url: (str) relative path to target api
    :param job_id: (str)
    :param worker_id: (str)
    :param signal: (new_judgments|unit_complete)
    :param unit_state: (finalized|new|judging|judgeable?)
    :param by_get: (True|False) simulate a setup were each user triggers the webhook using a get request
    """
    import time
    proceed = False
    max_retries = 5
    with app.app_context():
        while not proceed and max_retries>0:
            table_resp = get_table("resp", job_id, "result", treatment=treatment)
            table_prop = get_table("prop", job_id, "result", treatment=treatment)
            app.logger.debug("Waiting for the db...")
            con = get_db()
            with con:
                if con.execute(f"SELECT * FROM {table_resp} where worker_id=?", (worker_id,)).fetchone():
                    proceed = True
                elif con.execute(f"SELECT * FROM {table_prop} where worker_id=?", (worker_id,)).fetchone():
                    proceed = True
            con = None
            time.sleep(0.01)
            max_retries -= 1
        data_dict = dict(webhook_data_template)
        data_dict["signal"] = signal
        data_dict["payload"]["job_id"] = job_id
        data_dict["payload"]["results"]["judgments"][0]["job_id"] = job_id
        data_dict["payload"]["results"]["judgments"][0]["worker_id"] = worker_id
        data_dict["payload"]["results"]["judgments"][0]["unit_state"] = unit_state
        job_config = get_job_config(db.get_db("DB"), job_id)
        payload = json.dumps(data_dict["payload"])
        payload_ext = payload + str(job_config["api_key"])
        signature = hashlib.sha1(payload_ext.encode()).hexdigest()
        data = {
            "signal": signal,
            "payload": payload,
            "signature": signature
        }
        if by_get:
            # An empty form is submitted when triggering the webhook by click
            data = {}
            if "?" in url:
                url += f"&job_id={job_id}&worker_id={worker_id}"
            else:
                url += f"?job_id={job_id}&worker_id={worker_id}"
            res = client.get(url, follow_redirects=True).status
        else:
            res = client.post(url, data=data, follow_redirects=True).status
        return res

def generate_worker_id(base="test", k=10):
    return f"{base}_" + "".join(random.choices(string.ascii_lowercase+string.digits, k=k))