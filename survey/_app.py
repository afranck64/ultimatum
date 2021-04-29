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

#["T10_FEEDBACK", "T10B", "T11A", "T11B", "T12A", "T13A", "T20A"]
TREATMENTS = ["T00", "T10", "T11", "T12", "T13", "T20"] + ["T10_FEEDBACK", "T12A", "T11B", "T13A", "T10B", "T11A", "T20A"] + ["T21", "T22", "T30", "T31"]

TREATMENTS_AUTO_DSS = {
    "T20",
    "T21",
    "T22",
    "T30",
    "T31",
}
TREATMENTS_MODEL_REFS= {
    "T00": None,
    "TAB": None,
    "T10": "T00",
    "T10_FEEDBACK": "T00",
    "T11": "T00",
    "T12": "T00",
    "T13": "T00",
    "T20": "T00",
    "T21": "T10",
    "T22": "T10",
    "T10B": "T00",
    "T11A": "T00",
    "T11B": "T00",
    "T12A": "T00",
    "T13A": "T00",
    "T20A": "T00",
    "T30": "T00",
    "T31": "T00",
}

VALUES_SEPARATOR = ":"
MAXIMUM_CONTROL_MISTAKES = 4

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

app.config["DEBUG"] = _env2bool(os.getenv("DEBUG"))

gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
if app.config["DEBUG"]:
    app.logger.setLevel(logging.DEBUG)
app.wsgi_app = ReverseProxied(app.wsgi_app)

app.config["MTURK_SANDBOX"] = _env2bool(os.getenv("MTURK_SANDBOX"))
app.logger.info(f"MTURK_SANDBOX: {app.config['MTURK_SANDBOX']}, AWS_PROFILE: {os.getenv('AWS_PROFILE')}")
app.config["TASKS"] = ["exp", "risk", "cc", "ras", "cpc"]
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(32))
app.config["APPLICATION_ROOT"] = os.getenv("APPLICATION_ROOT", "/")
# Main database
app.config["DATABASE"] = os.getenv("DATABASE", os.path.join(CODE_DIR, "db.sqlite3"))

app.config["ADMIN_SECRET"] = os.getenv("ADMIN_SECRET", "")

class FakePool(object):
    def starmap_async(self, func, args_list):
        for args in args_list:
            func(*args)

if app.config["TESTING"]:
    app.config["THREADS_POOL"] = FakePool()
else:
    app.config["THREADS_POOL"] = pool.ThreadPool(processes=1)

_treatments = []
for treatment in TREATMENTS:
    app.config[treatment] = _env2bool(os.getenv(treatment)) or _env2bool(os.getenv("TXX"))
    model_treatment = TREATMENTS_MODEL_REFS.get(treatment)
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
                    app.logger.warning(f"Disabling treatment {treatment} due to: {err}")
                except Exception as err:
                    app.logger.error(err)
            except Exception as err:
                app.logger.warning(f"Disabling treatment {treatment} due to: {err}")
app.logger.warn(f"Treatments: {_treatments}")
app.config["TREATMENTS"] = _treatments
app.config["TREATMENTS_AUTO_DSS"] = TREATMENTS_AUTO_DSS
app.config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR", "./data/output")
os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)

