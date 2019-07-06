import os
import logging
import random
import warnings
import json
from sklearn.externals import joblib
from multiprocessing import pool
from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)
from flask_wtf.csrf import CSRFProtect

CODE_DIR = os.path.split(os.path.split(__file__)[0])[0]

app = Flask(__name__)

csrf_protect = CSRFProtect(app)

class FakeModel(object):
    _warned = False
    def predict(self, *args, **kwargs):
        if not self._warned:
            warnings.warn("You are using the fake model!!!")
            self._warned = True
        return kwargs.get("min_offer", random.randint(0, 200))

def _env2bool(env_value):
    if env_value is None:
        return False
    return env_value.upper() in {"YES", "TRUE", "ENABLED"}

app.config["DEBUG"] = _env2bool(os.getenv("DEBUG"))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(32))
app.config["APPLICATION_ROOT"] = os.getenv("APPLICATION_ROOT", "/")
# Main database
app.config["DATABASE"] = os.getenv("DATABASE", "./db.sqlite3")
# Data (job based) database
app.config["DATABASE_DATA"] = os.getenv("DATABASE_DATA", "./db.data.sqlite3")
# Results (job based) database
app.config["DATABASE_RESULT"] = os.getenv("DATABASE_RESULT", "./db.result.sqlite3")
app.config["ADMIN_SECRET"] = os.getenv("ADMIN_SECRET", "")
app.config["THREADS_POOL"] = pool.ThreadPool(processes=1)
app.config["FAKE_MODEL"] = _env2bool(os.getenv("FAKE_MODEL", 'yes'))
_treatments = []
for treatment in ["T10", "T11", "T12", "T13", "T20", "T21", "T22"]:
    app.config[treatment] = _env2bool(os.getenv(treatment)) or _env2bool(os.getenv("TXX"))
    treatment_dir = f"{CODE_DIR}/data/{treatment.lower()}/"
    if app.config[treatment] and os.path.exists(treatment_dir):
        app.config[f"{treatment}_MODEL"] = joblib.load(os.path.join(treatment_dir, "model.pkl"))
        with open(os.path.join(treatment_dir, "model.json")) as inp_f:
            app.config[f"{treatment}_MODEL_INFOS"] = json.load(inp_f)
        _treatments.append(treatment)
app.config["TREATMENTS"] = _treatments
app.config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR", "./data/output")
os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the 
    front-end server to add these headers, to let you quietly bind 
    this to a URL other than / and to an HTTP scheme that is 
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.DEBUG)
app.wsgi_app = ReverseProxied(app.wsgi_app)

from survey.db import init_app, init_db

#init_app(app)