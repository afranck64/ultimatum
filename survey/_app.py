import os
import logging
import random
import warnings
import json
import joblib
import importlib
from multiprocessing import pool
from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify
)
from flask_wtf.csrf import CSRFProtect

from core.models.metrics import MAX_GAIN

CODE_DIR = os.path.split(os.path.split(__file__)[0])[0]

app = Flask(__name__)

csrf_protect = CSRFProtect(app)

TREATMENTS = ["T00", "T10", "T11", "T12", "T13", "T20", "T21", "T22"]

TREATMENTS_AUTO_DSS = {
    "T20"
    "T21",
    "T22"
}
TREATMENTS_MODEL_REFS= {
    "T00": None,
    "T10": "T00",
    "T11": "T00",
    "T12": "T00",
    "T13": "T00",
    "T20": "T00",
    "T21": "T10",
    "T22": "T10",    
}

class FakeModel(object):
    _warned = False
    def predict(self, *args, **kwargs):
        if not self._warned:
            warnings.warn("You are using the fake model!!!")
            self._warned = True
        return kwargs.get("min_offer", random.randint(0, MAX_GAIN))

def _env2bool(env_value):
    if env_value is None:
        return False
    return env_value.upper() in {"YES", "TRUE", "ENABLED"}

app.config["DEBUG"] = _env2bool(os.getenv("DEBUG"))
app.config["MTURK_SANDBOX"] = _env2bool(os.getenv("MTURK_SANDBOX"))
app.logger.info(f"M_TURK_SANDBOX: {app.config['MTURK_SANDBOX']}")
app.config["TASKS"] = ["cpc", "exp", "risk"]
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
_treatments = []
for treatment in TREATMENTS:
    app.config[treatment] = _env2bool(os.getenv(treatment)) or _env2bool(os.getenv("TXX"))
    model_treatment = TREATMENTS_MODEL_REFS[treatment]
    model_key = f"{model_treatment}_MODEL"
    model_infos_key = f"{model_treatment}_MODEL_INFOS"
    if model_treatment is None:
        app.config[model_key] = None
        app.config[model_infos_key] = None
        try:
            importlib.import_module(f"survey.{treatment.lower()}")
            _treatments.append(treatment)
        except Exception as err:
            app.logger.warning(err)
    else:
        treatment_dir = f"{CODE_DIR}/data/{model_treatment.lower()}/"
        fake_model_key = f"{treatment}_FAKE_MODEL"
        app.config[fake_model_key] = _env2bool(os.getenv(fake_model_key)) or _env2bool(os.getenv("TXX_FAKE_MODEL"))
        if app.config[treatment] :# and os.path.exists(treatment_dir):
            try:
                if app.config.get(model_key) is None or app.config.get(model_infos_key) is None:
                    app.config[model_key] = joblib.load(os.path.join(treatment_dir, "model.pkl"))
                    with open(os.path.join(treatment_dir, "model.json")) as inp_f:
                        app.config[model_infos_key] = json.load(inp_f)
                try:
                    importlib.import_module(f"survey.{treatment.lower()}")
                    _treatments.append(treatment)
                except ImportError as err:
                    app.logger.warning(err)
                except Exception as err:
                    app.logger.error(err)
            except Exception as err:
                app.logger.warning(err)
app.config["TREATMENTS"] = _treatments
app.config["TREATMENTS_AUTO_DSS"] = TREATMENTS_AUTO_DSS
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