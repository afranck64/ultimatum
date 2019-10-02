import os
import uuid

import requests
from flask import render_template, request, flash, url_for, redirect, make_response, session
from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired, Optional, Regexp
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField

from survey.utils import (
    get_table, save_result2db, save_result2file, get_output_filename, get_latest_treatment, generate_completion_code, save_worker_id,
    get_cookie_obj, set_cookie_obj, table_exists, WORKER_CODE_DROPPED, ALL_COOKIES_KEY)

from core.models.metrics import MAX_GAIN
from survey.db import insert, get_db
from survey._app import app
from survey.adapter import get_adapter, get_adapter_from_dict
from survey.txx.index import check_is_proposer_next, NEXT_IS_PROPOSER_WAITING

BASE = os.path.splitext(os.path.split(__file__)[1])[0]

class MainForm(FlaskForm):
    gender = RadioField("What is your gender?", choices=[
        ("female", "Female"),
        ("male", "Male"),
        ("other", "Other")],
        validators=[DataRequired("Please choose a value")]
        )
    age = RadioField("What is your age?", choices=[
        ("1825_years", "18-25 Years"),
        ("2635_years", "26-35 Years"),
        ("3645_years", "36-45 Years"),
        ("4655_years", "46-55 Years"),
        ("5665_years", "56-65 Years"),
        ("older_than_65_years", "Older than 65 Years")],
        validators=[DataRequired("Please choose a value")]
    )
    ethnicity = RadioField("What is your ethnicity?", choices=[
        ("african_american", "African American"),
        ("american_indian", "American Indian"),
        ("asian", "Asian"),
        ("hispanic", "Hispanic/Latino"),
        ("pacific_islander", "Pacific Islander"),
        ("white", "White/Caucasian"),
        ("other", "Other")], validators=[DataRequired("Please choose a value")])
    income = RadioField("Which of the following describes the income you earn from crowdsourced microtasks?", choices=[
        ("Primary source of income", "Primary source of income"),
        ("Secondary source of income", "Secondary source of income"),
        ("I earn nearly equal incomes from crowdsourced microtasks and other job(s)", "I earn nearly equal incomes from crowdsourced microtasks and other job(s)")],
        validators=[DataRequired("Please choose a value")]
    )
    proposer = RadioField("The PROPOSER...", choices=[
        ("incorrect1", "decides the amount of money that the RESPONDER is paid"),
        ("correct", f"proposes a division of the {MAX_GAIN / 100:.2f} USD with the RESPONDER"),
        ("incorrect2", "accepts or rejects the offer made by the RESPONDER")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    responder = RadioField("The RESPONDER...", choices=[
        ("incorrect1", "decides the amount of money that the PROPOSER is paid"),
        ("incorrect2", f"proposes a division of the {MAX_GAIN / 100:.2f} USD with the PROPOSER"),
        ("correct", "accepts or rejects the offer made by the PROPOSER")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    proposer_responder = RadioField("Choose the correct answer", choices=[
        ("correct", "The PROPOSER and the RESPONDER are both humans participating in the task simultaneously."),
        ("incorrect1", "Your matched worker is simulated by the computer and is not a real person."),
        ("incorrect2", "Your decisions do not affect another worker.")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    money_division = RadioField("Choose the correct answer", choices=[
        ("incorrect1", "The money is divided 50/50 between the RESPONDER and the PROPOSER"),
        ("incorrect2", "The money is divided according to the RESPONDER's minimum offer"),
        ("correct", "The money is divided according to the PROPOSER's offer")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    code_resp_prop = StringField("Completion Code: main task", validators=[DataRequired(), Regexp(regex="prop:|resp:")])
    code_cpc = StringField("Completion Code: choice task", validators=[Optional()])
    code_risk = StringField("Completion Code: risk task", validators=[Optional()])
    code_exp = StringField("Completion Code: experience task", validators=[Optional()])
    code_cc = StringField("Completion Code: cognitive task", validators=[Optional()])
    test = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    please_enter_your_comments_feedback_or_suggestions_below = TextAreaField("Please enter your comments, feedback or suggestions below.")

def handle_survey(treatment=None, template=None, code_prefixes=None, form_class=None):
    app.logger.info("handle_survey")
    if code_prefixes is None:
        code_prefixes = {"code_cpc": "cpc:", "code_exp": "exp:", "code_risk": "risk:", "code_cc": "cc:"}
    if form_class is None:
        form_class = MainForm
    if template is None:
        template = "txx/survey.html"
    cookie_obj = get_cookie_obj(BASE)
    
    adapter_cookie = get_adapter_from_dict(cookie_obj.get("adapter", {}))
    adapter_referrer = get_adapter()
    
    if adapter_referrer.worker_id not in {"", "na", None}:
        adapter = adapter_referrer
    else:
        adapter = adapter_cookie

    app.logger.debug(f"adapter: {adapter.to_dict()}")
    worker_code_key = f"{BASE}_worker_code"

    arg_job_id = adapter.get_job_id()
    arg_worker_id = adapter.get_worker_id()
    job_id = arg_job_id or f"na"
    worker_id = arg_worker_id or str(uuid.uuid4())

    max_judgments = 0 #not set
    if adapter.has_api():
        api = adapter.get_api()
        max_judgments = api.get_max_judgments()
    next_player = check_is_proposer_next(job_id, worker_id, treatment, max_judgments=max_judgments)
    #The next player should be a proposer but some responders may still be processing data
    if next_player == NEXT_IS_PROPOSER_WAITING:
        flash("Unfornately there is no available HIT right now. Please check again in 15 minutes. Otherwise you can submit right now using the survey code provided")
        return render_template("error.html", worker_code=WORKER_CODE_DROPPED)


    table_all = get_table("txx", "all", schema=None)
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key):        
        req_response = make_response(redirect(url_for("survey_done")))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response
    if treatment is None:
        treatment = get_latest_treatment()
    cookie_obj["job_id"] = job_id
    cookie_obj["worker_id"] = worker_id
    cookie_obj["treatment"] = treatment
    cookie_obj["adapter"] = adapter.to_dict()
    cookie_obj[BASE] = True
    form = form_class(request.form)
    drop = request.form.get("drop")
    con = get_db()
    if table_exists(con, table_all):
        with con:
            res = con.execute(f"SELECT * from {table_all} WHERE worker_id=?", (worker_id,)).fetchone()
            if res:
                flash(f"You already took part on this survey. Thank you for your participation")
                req_response = make_response(render_template("error.html", worker_code=WORKER_CODE_DROPPED))
                return req_response

    if request.method == "POST" and (drop=="1" or form.validate_on_submit()):
        form = form_class(request.form)
        cookie_obj["response"] = request.form.to_dict()
        response = request.form.to_dict()
        is_codes_valid = True
        # Responders have to fill and submit tasks
        if "resp:" in response.get("code_resp_prop", ""):
            for fieldname, prefix in code_prefixes.items():
                if not prefix in response[fieldname] or not response[fieldname]:
                    field = getattr(form, fieldname)
                    # Validated forms have errors as tuples
                    field.errors = field.errors + ("Invalid code",)
                    is_codes_valid = False
        if is_codes_valid and job_id != "na" and worker_id != "na":
            cookie_obj["response"] = response
            req_response = make_response(redirect(url_for("survey_done")))
            set_cookie_obj(req_response, BASE, cookie_obj)
            app.logger.debug(f"RESPONSE: {response}")
            return req_response
        elif is_codes_valid:
            flash("Your data was validated and submitted. But not saved as this is a test task")
    else:
        response = request.form.to_dict()
        if "resp:" in response.get("code_resp_prop", ""):
            for fieldname, prefix in code_prefixes.items():
                if not response.get(fieldname) or not prefix in response[fieldname]:
                    field = getattr(form, fieldname)
                    # Non validated forms have errors as lists
                    field.errors = field.errors + ["Invalid code"]
                    is_codes_valid = False

    req_response = make_response(render_template(template, job_id=job_id, worker_id=worker_id, treatment=treatment, form=form, max_judgments=max_judgments, max_gain=MAX_GAIN))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response


def handle_survey_done(template=None):
    if template is None:
        template = "txx/survey.done.html"
    cookie_obj = get_cookie_obj(BASE)
    if not cookie_obj.get(BASE):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    worker_code_key = f"{BASE}_worker_code"
    worker_code = WORKER_CODE_DROPPED
    if True or not cookie_obj.get(worker_code_key):
        job_id = cookie_obj["job_id"]
        worker_id = cookie_obj["worker_id"]
        treatment = cookie_obj["treatment"]

        worker_code = generate_completion_code(base=treatment, job_id=job_id)
        response = cookie_obj["response"]
        app.logger.debug("DONE_response: {response}")
        dropped = response.get("drop")
        if dropped=="1":
            worker_code = WORKER_CODE_DROPPED
            flash("You have been disqualified as failed 3 times to correctly answer the control questions.")
        response["worker_id"] = worker_id
        response["job_id"] = job_id
        result = {k:v for k,v in response.items() if k not in {'csrf_token', 'drop'}}
        try:
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=treatment), result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=result, unique_fields=["worker_id"])
        except Exception as err:
            app.log_exception(err)

        adapter = get_adapter_from_dict(cookie_obj["adapter"])
        #adapter = get_adapter()
        app.logger.debug(f"adapter: {cookie_obj['adapter']}")
        cookie_obj.clear()
        # cookie_obj[BASE] = True
        # cookie_obj["worker_id"] = worker_id
        # cookie_obj[worker_code_key] = worker_code
        # cookie_obj.clear()

        # submit_to_URL = adapter.get_submit_to_URL()
        # if submit_to_URL is not None:
        #     try:
        #         response = requests.post(submit_to_URL, json=adapter.get_submit_to_kwargs())
        #         app.logger.debug
        #     except Exception as err:
        #         app.logger.warn(f"{err}")
        save_worker_id(job_id=job_id, worker_id=worker_id, worker_code=worker_code, assignment_id=adapter.assignment_id)
        app.logger.info(f"handle_survey_done: saved new survey - job_id: {job_id}, worker_id: {worker_id}")
    req_response = make_response(render_template(template, worker_code=worker_code, dropped=True))
    set_cookie_obj(req_response, BASE, cookie_obj)
    for cookie in session.get(ALL_COOKIES_KEY, []):
        req_response.set_cookie(cookie, expires=0)
    session[ALL_COOKIES_KEY] = []
    return req_response
