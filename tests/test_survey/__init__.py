import os
import tempfile
import random
import string
import json
import hashlib

import pytest
from survey.app import app
from survey import db
from survey.admin import get_job_config

BASE_DIR = os.path.split(os.path.split(os.path.split(__file__)[0])[0])[0]

# from survey import app
# from survey import db
@pytest.fixture
def client():
    app.config["ADMIN_SECRET"] = "secret"
    app.config["OUTPUT_DIR"] = os.path.join(BASE_DIR, "data", "output", "test")
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    dbs = ["DATABASE", "DATABASE_RESULT", "DATABASE_DATA"]
    dbs_fds = []
    for _db in dbs:
        #_fd, app.config[_db] = tempfile.mkstemp(dir=os.path.join(BASE_DIR, "data", "output", "test"))
        _fd, app.config[_db] = 0, os.path.join(BASE_DIR, "data", "output", "test", f"{_db.lower()}.sqlite3")
        dbs_fds.append(_fd)
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        db.init_db()

    yield client

    # for _fd in dbs_fds:
    #     os.close(_fd)
    # for _db in dbs:
    #     os.unlink(app.config[_db])


def emit_webhook(client, url, job_id="test", worker_id=None, signal="new_judgments"):
    with app.app_context():
        payload_dict = {
            "job_id": job_id,
            "judgments_count": 1,
            "results": {
                "judgments": [
                    {
                        "worker_id": worker_id
                    }
                ]
            }
        }
        job_config = get_job_config(db.get_db("DB"), job_id)
        payload = json.dumps(payload_dict)
        payload_ext = payload + str(job_config["api_key"])
        signature = hashlib.sha1(payload_ext.encode()).hexdigest()
        data = {
            "signal": signal,
            "payload": payload,
            "signature": signature
        }
        client.post(url, data=data, follow_redirects=True)

def generate_worker_id(base="test"):
    return f"{base}_" + "".join(random.choices(string.ascii_lowercase+string.digits, k=8))