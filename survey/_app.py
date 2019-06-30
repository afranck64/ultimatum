import os
import logging
from multiprocessing import pool
from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

csrf_protect = CSRFProtect(app)

class FakeModel(object):
    def predict(self, *args, **kwargs):
        import random
        import warnings
        warnings.warn("You are using the fake model!!!")
        return random.randint(0, 200)

_debug = os.environ.get("DEBUG")
_debug = _debug.upper() if _debug else _debug
app.config["DEBUG"] = _debug in {"YES", "TRUE"}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32))
app.config["APPLICATION_ROOT"] = os.environ.get("APPLICATION_ROOT", "/")
# Main database
app.config["DATABASE"] = os.environ.get("DATABASE", "./db.sqlite3")
# Data (job based) database
app.config["DATABASE_DATA"] = os.environ.get("DATABASE_DATA", "./db.data.sqlite3")
# Results (job based) database
app.config["DATABASE_RESULT"] = os.environ.get("DATABASE_RESULT", "./db.result.sqlite3")
app.config["API_KEY"] = os.environ.get("API_KEY", "")
app.config["ADMIN_SECRET"] = os.environ.get("ADMIN_SECRET", "")
app.config["THREADS_POOL"] = pool.ThreadPool(processes=1)
app.config["T10_MODEL"] = FakeModel()
app.config["OUTPUT_DIR"] = os.environ.get("OUTPUT_DIR", "./data/output")
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