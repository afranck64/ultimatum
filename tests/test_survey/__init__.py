import os
import tempfile

import pytest
from survey._app import app
from survey import db

# from survey import app
# from survey import db
@pytest.fixture
def client():
    app.config["ADMIN_SECRET"] = "secret"
    app.config["OUTPUT_DIR"] = os.path.join("..", "data", "output", "test")
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    dbs = ["DATABASE", "DATABASE_RESULT", "DATABASE_DATA"]
    dbs_fds = []
    for _db in dbs:
        _fd, app.config[_db] = tempfile.mkstemp()
        dbs_fds.append(_fd)
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        db.init_db()

    yield client

    for _fd in dbs_fds:
        os.close(_fd)
    for _db in dbs:
        os.unlink(app.config[_db])