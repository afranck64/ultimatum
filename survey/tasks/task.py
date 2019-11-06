import csv
import datetime
import os
import string
import random
import time
import json

import pandas as pd
import requests

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response, make_response
)
from werkzeug.contrib.securecookie import SecureCookie



from core.utils import cents_repr
from core.models.metrics import MAX_GAIN

from survey._app import app
from survey.db import get_db, insert, table_exists, update
from survey.admin import get_job_config
from survey.utils import (
    get_cookie_obj, set_cookie_obj, value_to_numeric, get_output_filename, get_table, increase_worker_bonus, save_result2db, save_result2file,
    save_worker_id, generate_completion_code
)


def response_to_result(response, job_id=None, worker_id=None):
    """
    :returns: {
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = 0
    return result

def handle_task_index(base, validate_response=None, template_kwargs=None):
    app.logger.debug(f"handle_task_index: {base}")
    if template_kwargs is None:
        template_kwargs = dict()
    req_response = make_response(render_template(f"tasks/{base}.html", **template_kwargs))
    cookie_obj = get_cookie_obj(base)

    worker_code_key = f"{base}_worker_code"
    worker_id = request.args.get("worker_id", "na")
    job_id = request.args.get("job_id", "na")
    # The user has already processed this task. So we skip to the "done" page.
    if cookie_obj.get(base) and cookie_obj.get(worker_code_key) and cookie_obj.get("worker_id") == worker_id:
        req_response = make_response(redirect(url_for(f"tasks.{base}.done", **request.args)))
        return req_response

    if request.method == "GET":
        cookie_obj[base] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj["job_id"] = job_id
        cookie_obj["time_start"] = time.time()
        cookie_obj["auto_finalize"] = request.args.get("auto_finalize")
        cookie_obj["treatment"] = request.args.get("treatment")
    if request.method == "POST":
        response = request.form.to_dict()
        if validate_response is not None and validate_response(response):
            response["time_stop"] = time.time()
            response["time_start"] = cookie_obj["time_start"]
            response["time_spent"] = round(response["time_stop"] - response["time_start"])
            response[f"{base}_time_spent"]  = response["time_spent"]
            req_response = make_response(redirect(url_for(f"tasks.{base}.done", **request.args)))
            cookie_obj["response"] = response
            set_cookie_obj(req_response, base, cookie_obj)
            return req_response
        else:
            flash("Please check your fields")
    set_cookie_obj(req_response, base, cookie_obj)
    return req_response


def handle_task_done(base, response_to_result_func=None, response_to_bonus=None, numeric_fields=None, unique_fields=None):
    """
    :param base: (str)
    :param response_to_result_func: (func)
    :param response_to_bonus: (func)
    :param numeric_fields: (None| '*' | list)  if '*' all fields are converted to float
    :param unique_fields: (str|list)
    """
    app.logger.debug(f"handle_task_done: {base}")
    worker_code_key = f"{base}_worker_code"
    worker_bonus_key = f"{base}_worker_bonus"
    cookie_obj = get_cookie_obj(base)
    if response_to_result_func is None:
        response_to_result_func = response_to_result
    if not cookie_obj.get(base):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    if response_to_bonus is None:
        response_to_bonus = lambda args, **kwargs: 0
    if not cookie_obj.get(worker_code_key) or (app.config["DEBUG"] and False):
        job_id = cookie_obj["job_id"]
        worker_code = generate_completion_code(base, job_id)
        response = cookie_obj["response"]
        if numeric_fields is not None:
            if isinstance(numeric_fields, (list, tuple)):
                for field in numeric_fields:
                    try:
                        response[field] = value_to_numeric(response[field])
                    except Exception as err:
                        app.log_exception(err)
            elif numeric_fields == "*":
                for field in response:
                    try:
                        response[field] = value_to_numeric(response[field])
                    except Exception as err:
                        app.log_exception(err)

        worker_id = cookie_obj["worker_id"]
        response["completion_code"] = worker_code
        response_result = response_to_result_func(response, job_id=job_id, worker_id=worker_id)
        worker_bonus = response_to_bonus(response)
        response_result["worker_bonus"] = worker_bonus
        try:
            save_result2file(get_output_filename(base, job_id, is_task=True), response_result)
        except Exception as err:
            app.log_exception(err)
        try:
            #TODO: check later
            save_result2db(get_table(base, job_id=job_id, schema="result", is_task=True), response_result, unique_fields=unique_fields)
            increase_worker_bonus(job_id=job_id, worker_id=worker_id, bonus_cents=worker_bonus)
        except Exception as err:
            app.log_exception(err)
        
        #NOTE: hexaco is the LAST task required from the user!!!
        auto_finalize = cookie_obj.get("auto_finalize")
        if auto_finalize:# and base=="hexaco":
            #NOTE: there is an import here ^_^
            from survey.txx.helpers import finalize_resp
            treatment = cookie_obj.get("treatment")
            finalize_resp(job_id, worker_id, treatment)
            # client = app.test_client()
            # url = url_for(f"{treatment}.webhook", job_id=job_id, worker_id=worker_id, auto_finalize=auto_finalize, _external=False)
            # app.logger.debug(f"WEBHOOK-URL: {url}")
            # response = client.get(url)
            # # response = requests.get(url)
            # # response = make_response(url)
            # if response.status_code != 200:
            #     app.logger.warning(f"handle_task_done: Something went wrong when: auto: {auto_finalize}, base: {base}, resp-status: {response.data}")
        cookie_obj.clear()
        cookie_obj[base] = True
        cookie_obj["worker_id"] = worker_id
        cookie_obj[worker_code_key] = worker_code
        cookie_obj[worker_bonus_key] = worker_bonus
    
    req_response = make_response(render_template("tasks/done.html", worker_code=cookie_obj[worker_code_key], worker_bonus=cents_repr(cookie_obj[worker_bonus_key])))
    set_cookie_obj(req_response, base, cookie_obj)
    return req_response


############################################################
