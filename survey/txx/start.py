import os
import uuid
import datetime

import requests
from flask import render_template, request, flash, url_for, redirect, make_response, session
from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired, Optional, Regexp
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField, SelectMultipleField, SelectField
from wtforms.widgets import ListWidget, CheckboxInput

from survey.utils import (
    get_table, save_result2db, save_result2file, get_output_filename, get_latest_treatment, generate_completion_code, save_worker_id,
    get_cookie_obj, set_cookie_obj, table_exists, WORKER_CODE_DROPPED, ALL_COOKIES_KEY, is_worker_available)

from core.models.metrics import MAX_GAIN
from survey.db import insert, get_db
from survey.admin import get_job_config
from survey._app import app, VALUES_SEPARATOR, MAXIMUM_CONTROL_MISTAKES, TREATMENTS_AUTO_DSS
from survey.adapter import get_adapter, get_adapter_from_dict
from survey.txx.index import check_is_proposer_next, NEXT_IS_WAITING

BASE = os.path.splitext(os.path.split(__file__)[1])[0]

def select_adapter():
    cookie_obj = get_cookie_obj(BASE)
    adapter_cookie = get_adapter_from_dict(cookie_obj.get("adapter", {}))
    adapter_args = get_adapter_from_dict(request.args)
    adapter_referrer = get_adapter()
    
    if adapter_referrer.job_id not in {"", "na", None}:
        adapter = adapter_referrer
    elif adapter_cookie.job_id not in {"", "na", None}:
        adapter = adapter_cookie
    else:
        adapter = adapter_args
    return adapter

def handle_start(treatment=None, template=None, code_prefixes=None, form_class=None, overview_url=None, resp_only=None, prop_only=None):
    app.logger.info("handle_start")
    if template is None:
        template = "txx/start.html"
    if overview_url is None:
        overview_url = url_for("overview")
    cookie_obj = get_cookie_obj(BASE)
    
    adapter = select_adapter()

    app.logger.debug(f"adapter: {adapter.to_dict()}")

    arg_job_id = adapter.get_job_id()
    arg_worker_id = adapter.get_worker_id()
    assignment_id = adapter.get_assignment_id()
    job_id = arg_job_id or f"na"
    worker_id = arg_worker_id
    if worker_id in {"", "na", None}:
        worker_id = str(uuid.uuid4())
        adapter.worker_id = worker_id



    table_all = get_table("txx", "all", schema=None)
    # The task was already completed, so we skip to the completion code display
    # if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key):        
    #     req_response = make_response(redirect(url_for(f"{treatment}.survey.survey_done", **request.args)))
    #     set_cookie_obj(req_response, BASE, cookie_obj)
    #     return req_response
    if treatment is None:
        treatment = get_latest_treatment()
    cookie_obj["job_id"] = job_id
    cookie_obj["worker_id"] = worker_id
    cookie_obj["treatment"] = treatment
    cookie_obj["adapter"] = adapter.to_dict()
    cookie_obj[BASE] = True

    con = get_db()
    if table_exists(con, table_all):
        with con:
            res = con.execute(f"SELECT * from {table_all} WHERE worker_id=?", (worker_id,)).fetchone()
            if res:
                flash(f"You already took part on this survey.")
                flash("You can just ignore this HIT for the assignment to be RETURNED later to another worker.")
                req_response = make_response(render_template("error.html", worker_code=WORKER_CODE_DROPPED))
                return req_response

    req_response = make_response(render_template(template, job_id=job_id, worker_id=worker_id, assignment_id=assignment_id, treatment=treatment, submit_to_url=adapter.get_submit_to_URL()))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response

