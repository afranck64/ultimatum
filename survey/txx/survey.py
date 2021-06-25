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


class MultiCheckboxField(SelectMultipleField):
    # Thanks: https://snipnyet.com/adierebel/59f46bff77da1511c3503532/multiple-checkbox-field-using-wtforms-with-flask-wtf/
	widget			= ListWidget(prefix_label=False)
	option_widget	= CheckboxInput()

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
    ethnicity = MultiCheckboxField("What is the ethnicity with which you most closely identify? You may choose multiple options.", choices=[
        ("american_indian_or_alaska_native", "American Indian or Alaska Native"),
        ("asian", "Asian"),
        ("black_or_african_american", "Black or African American"),
        ("hispanic_latino", "Hispanic/Latino"),
        ("hawaiian_or_pacific_islander", "Native Hawaiian or Pacific Islander"),
        ("white", "White/Caucasian"),
        ("other", "Other")], validators=[DataRequired("Please choose a value")]
    )
    income = RadioField("Which of the following describes the income you earn from crowdsourced microtasks?", choices=[
        ("Primary source of income", "Primary source of income"),
        ("Secondary source of income", "Secondary source of income"),
        ("I earn nearly equal incomes from crowdsourced microtasks and other job(s)", "I earn nearly equal incomes from crowdsourced microtasks and other job(s)")],
        validators=[DataRequired("Please choose a value")]
    )
    education =  RadioField("What is the highest degree or level of school you have completed?", choices=[
        ("less_than_high_school_diploma", "Less than a high school diploma"),
        ("high_school_degree", "High school graduate, diploma or the equivalent"),
        ("bachelor_degree", "Bachelor's degree"),
        ("master_degree", "Master's degree"),
        ("doctorate_degree", "Doctorate degree"),
        ("other", "Other")],
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
    money_division = RadioField("If the RESPONDER accepts the PROPOSER's offer...", choices=[
        ("incorrect1", "the money is divided 50/50 between the RESPONDER and the PROPOSER"),
        ("incorrect2", "the money is divided according to the RESPONDER's minimum offer"),
        ("correct", "the money is divided according to the PROPOSER's offer")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    code_resp_prop = StringField("Completion Code of the main task:", validators=[DataRequired(), Regexp(regex=r" *prop:\w*| *resp:\w*| *respNF:\w*")])
    code_cpc = StringField("Completion Code of the choice task:", validators=[Optional()])
    code_risk = StringField("Completion Code of the risk task:", validators=[Optional()])
    code_exp = StringField("Completion Code of the experience task:", validators=[Optional()])
    code_cc = StringField("Completion Code of the letters selection task:", validators=[Optional()])
    code_ras = StringField("Completion Code of the assertiveness task:", validators=[Optional()])
    test = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    feedback = TextAreaField("Please enter your comments, feedback or suggestions below.")

class MainFormFeeback(FlaskForm):
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
    money_division = RadioField("If the RESPONDER accepts the PROPOSER's offer...", choices=[
        ("incorrect1", "the money is divided 50/50 between the RESPONDER and the PROPOSER"),
        ("incorrect2", "the money is divided according to the RESPONDER's minimum offer"),
        ("correct", "the money is divided according to the PROPOSER's offer")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )
    code_resp_prop = StringField("Completion Code of the main task:", validators=[DataRequired(), Regexp(regex=r" *prop:\w*| *resp:\w*| *respNF:\w*")])
    test = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    feedback = TextAreaField("Please enter your comments, feedback or suggestions below.")

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

def handle_survey(treatment=None, template=None, code_prefixes=None, form_class=None, overview_url=None, resp_only=None, prop_only=None):
    app.logger.info("handle_survey")
    if code_prefixes is None:
        code_prefixes = {"code_cpc": "cpc:", "code_exp": "exp:", "code_risk": "risk:", "code_cc": "cc:", "code_ras": "ras:"}
    if form_class is None:
        form_class = MainForm
    if template is None:
        template = "txx/survey.html"
    if overview_url is None:
        overview_url = url_for("overview")
    cookie_obj = get_cookie_obj(BASE)
    
    adapter = select_adapter()

    app.logger.debug(f"adapter: {adapter.to_dict()}")
    worker_code_key = f"{BASE}_worker_code"

    arg_job_id = adapter.get_job_id()
    arg_worker_id = adapter.get_worker_id()
    job_id = arg_job_id or f"na"
    worker_id = arg_worker_id
    if worker_id in {"", "na", None}:
        worker_id = str(uuid.uuid4())
        adapter.worker_id = worker_id

    max_judgments = 0 #not set
    if adapter.has_api():
        api = adapter.get_api()
        max_judgments = api.get_max_judgments()
    else:
        try:
            max_judgments = int(request.args.get("max_judgments", max_judgments))
        except:
            pass
    job_config = get_job_config(get_db(), job_id)
    max_judgments = max(max_judgments, job_config.expected_judgments)
    next_player = check_is_proposer_next(job_id, worker_id, treatment, max_judgments=max_judgments, resp_only=resp_only, prop_only=prop_only)


    table_all = get_table("txx", "all", schema=None)
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key):        
        req_response = make_response(redirect(url_for(f"{treatment}.survey.survey_done", **request.args)))
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
                flash(f"You already took part on this survey.")
                flash("You can just ignore this HIT for the assignment to be RETURNED later to another worker.")
                req_response = make_response(render_template("error.html", worker_code=WORKER_CODE_DROPPED))
                return req_response

    #The next player should be a proposer but some responders may still be processing data
    if next_player == NEXT_IS_WAITING:
        resp_table = get_table(base="resp", job_id=job_id, schema="result", treatment=treatment)
        prop_table = get_table(base="prop", job_id=job_id, schema="result", treatment=treatment)
        # We make sure the user didn't accidentaly refreshed the page after processing the main task
        if (not is_worker_available(worker_id, resp_table) and not is_worker_available(worker_id, prop_table)):
            flash("Unfortunately there is no task available right now. Please check again in 15 minutes. Otherwise you can just ignore this HIT for the assignment to be RETURNED later to another worker or you can submit right now for a REJECTION using the survey code provided.")
            return render_template("error.html", worker_code=WORKER_CODE_DROPPED)

    if adapter.is_preview() or job_id=="na":
        flash("Please do note that you are currently in the preview mode of the survey. You SHOULD NOT FILL NEITHER SUBMIT the survey in this mode. Please go back to Mturk and read the instructions about how to correctly start this survey.")

    if request.method == "POST" and (drop=="1" or form.validate_on_submit()):
        # Makes sure all fields are available, not only the one with value submitted!!!
        response = {k:None for k in form._fields}
        form = form_class(request.form)
        response.update(request.form.to_dict())
        response["ethnicity"] = VALUES_SEPARATOR.join(sorted(request.form.getlist(form.ethnicity.name)))
        response["timestamp"] = str(datetime.datetime.now())
        cookie_obj["response"] = response        
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
            req_response = make_response(redirect(url_for(f"{treatment}.survey.survey_done", **request.args)))
            set_cookie_obj(req_response, BASE, cookie_obj)
            return req_response
        elif is_codes_valid:
            flash("Your data was submitted and validated but not save as you are currently in the preview mode of the survey. Please go back to Mturk and read the instructions about how to correctly start this survey.")
    elif request.method == "POST":
        response = request.form.to_dict()
        # Responders have to fill and submit tasks
        if "resp:" in response.get("code_resp_prop", ""):
            for fieldname, prefix in code_prefixes.items():
                if not response.get(fieldname) or not prefix in response[fieldname]:
                    field = getattr(form, fieldname)
                    # Non validated forms have errors as lists
                    field.errors = field.errors + ["Invalid code"]
                    is_codes_valid = False

    req_response = make_response(render_template(template, job_id=job_id, worker_id=worker_id, treatment=treatment, form=form, max_judgments=max_judgments, max_gain=MAX_GAIN, maximum_control_mistakes=MAXIMUM_CONTROL_MISTAKES, overview_url=overview_url, tasks=app.config["TASKS"]))
    set_cookie_obj(req_response, BASE, cookie_obj)
    return req_response



def handle_survey_feedback(treatment=None, template=None, code_prefixes=None, form_class=None, overview_url=None):
    app.logger.info("handle_survey_feedback")
    if code_prefixes is None:
        code_prefixes = {"code_cpc": "cpc:", "code_exp": "exp:", "code_risk": "risk:", "code_cc": "cc:", "code_ras": "ras:"}
    if form_class is None:
        form_class = MainFormFeeback
    if template is None:
        template = "txx/survey_feedback.html"
    if overview_url is None:
        if treatment and treatment.upper() in TREATMENTS_AUTO_DSS:
            overview_url = url_for("overview_auto_prop_feedback")
        else:
            overview_url = url_for("overview_feedback")
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

    app.logger.debug(f"adapter: {adapter.to_dict()}")
    worker_code_key = f"{BASE}_worker_code"

    arg_job_id = adapter.get_job_id()
    arg_worker_id = adapter.get_worker_id()
    job_id = arg_job_id or f"na"
    worker_id = arg_worker_id
    if worker_id in {"", "na", None}:
        worker_id = str(uuid.uuid4())
        adapter.worker_id = worker_id

    max_judgments = 0 #not set
    if adapter.has_api():
        api = adapter.get_api()
        max_judgments = api.get_max_judgments()
    else:
        try:
            max_judgments = int(request.args.get("max_judgments", max_judgments))
        except:
            pass
    job_config = get_job_config(get_db(), job_id)
    max_judgments = max(max_judgments, job_config.expected_judgments)
    next_player = check_is_proposer_next(job_id, worker_id, treatment, max_judgments=max_judgments)


    table_all = get_table("txx", "all", schema=None)
    # The task was already completed, so we skip to the completion code display
    if cookie_obj.get(BASE) and cookie_obj.get(worker_code_key):        
        req_response = make_response(redirect(url_for(f"{treatment}.survey.survey_done", **request.args)))
        set_cookie_obj(req_response, BASE, cookie_obj)
        return req_response
    if treatment is None:
        treatment = get_latest_treatment()
    cookie_obj["job_id"] = job_id
    cookie_obj["worker_id"] = worker_id
    cookie_obj["assignment_id"] = adapter.get_assignment_id()
    cookie_obj["treatment"] = treatment
    cookie_obj["adapter"] = adapter.to_dict()
    cookie_obj[BASE] = True
    form = form_class(request.form)
    drop = request.form.get("drop")
    con = get_db()
    # if table_exists(con, table_all):
    #     with con:
    #         res = con.execute(f"SELECT * from {table_all} WHERE worker_id=?", (worker_id,)).fetchone()
    #         if res:
    #             flash(f"You already took part on this survey. You can just ignore this HIT for the assignment to be RETURNED later to another worker or you can submit right now for a REJECTION using the survey code provided.")
    #             req_response = make_response(render_template("error.html", worker_code=WORKER_CODE_DROPPED))
    #             return req_response

    #The next player should be a proposer but some responders may still be processing data
    ## Should not matter in feedback surveys
    if next_player == NEXT_IS_WAITING:
        resp_table = get_table(base="resp", job_id=job_id, schema="result", treatment=treatment)
        prop_table = get_table(base="prop", job_id=job_id, schema="result", treatment=treatment)
        # We make sure the user didn't accidentaly refreshed the page after processing the main task
        if (not is_worker_available(worker_id, resp_table) and not is_worker_available(worker_id, prop_table)):
            flash("Unfortunately there is no task available right now. Please check again in 15 minutes. Otherwise you can just ignore this HIT for the assignment to be RETURNED later to another worker or you can submit right now for a REJECTION using the survey code provided.")
            return render_template("error.html", worker_code=WORKER_CODE_DROPPED)

    if adapter.is_preview() or job_id=="na":
        flash("Please do note that you are currently in the preview mode of the survey. You SHOULD NOT FILL NEITHER SUBMIT the survey in this mode. Please go back to Mturk and read the instructions about how to correctly start this survey.")

    if request.method == "POST" and (drop=="1" or form.validate_on_submit()):
        form = form_class(request.form)
        response = request.form.to_dict()
        response["timestamp"] = str(datetime.datetime.now())
        cookie_obj["response"] = response        
        is_codes_valid = True
        # Responders have to fill and submit tasks
        if is_codes_valid and job_id != "na" and worker_id != "na":
            cookie_obj["response"] = response
            #NOTE: the url should be pointing to handle_survey_feedback_done
            req_response = make_response(redirect(url_for(f"{treatment}.survey.survey_done", **request.args)))
            set_cookie_obj(req_response, BASE, cookie_obj)
            return req_response
        elif is_codes_valid:
            flash("Your data was submitted and validated but not save as you are currently in the preview mode of the survey. Please go back to Mturk and read the instructions about how to correctly start this survey.")

    req_response = make_response(render_template(template, job_id=job_id, worker_id=worker_id, treatment=treatment, form=form, max_judgments=max_judgments, max_gain=MAX_GAIN, maximum_control_mistakes=MAXIMUM_CONTROL_MISTAKES, overview_url=overview_url, tasks=app.config["TASKS"]))
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
            flash(f"You have been disqualified as you made more than {MAXIMUM_CONTROL_MISTAKES} mistakes on the control questions. Close this window and don't submit any completion on MTurk to avoid getting a REJECTION.")
        response["worker_id"] = worker_id
        response["job_id"] = job_id
        response["completion_code"] = worker_code
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

        save_worker_id(job_id=job_id, worker_id=worker_id, worker_code=worker_code, assignment_id=adapter.assignment_id)
        app.logger.debug(f"request-args: {request.args}, adapter: {adapter.to_dict()} ")
        try:
            expected_max_judgments = request.args.get("expected_max_judgments")
            if expected_max_judgments is not None:
                expected_max_judgments = int(expected_max_judgments)
                api = adapter.get_api()
                max_judgments = api.get_max_judgments()
                app.logger.debug(f"survey.done: max_judgments: {max_judgments} - {type(max_judgments)}, expected_max_judgments: {expected_max_judgments} - {type(expected_max_judgments)}")
                if max_judgments < expected_max_judgments:
                    app.logger.debug(f"try create new assignments")
                    create_res = api.create_additional_assignments(1)
                    app.logger.debug(f"post assignment creation: new-max: {api.get_max_judgments()} , mturk-api-res: {create_res}")
        except Exception as err:
            app.log_exception(err)
        app.logger.info(f"handle_survey_done: saved new survey - job_id: {job_id}, worker_id: {worker_id}")
    req_response = make_response(render_template(template, worker_code=worker_code, dropped=True))
    set_cookie_obj(req_response, BASE, cookie_obj)
    for cookie in session.get(ALL_COOKIES_KEY, []):
        req_response.set_cookie(cookie, expires=0)
    session[ALL_COOKIES_KEY] = []
    return req_response


def handle_survey_feedback_done(template=None):
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
        assignment_id = cookie_obj.get("assignment_id")

        worker_code = generate_completion_code(base=treatment, job_id=job_id)
        response = cookie_obj["response"]
        app.logger.debug("DONE_response: {response}")
        dropped = response.get("drop")
        if dropped=="1":
            worker_code = WORKER_CODE_DROPPED
            flash(f"You have been disqualified as you made more than {MAXIMUM_CONTROL_MISTAKES} mistakes on the control questions. Close this window and don't submit any completion on MTurk to avoid getting a REJECTION.")
        response["worker_id"] = worker_id
        response["job_id"] = job_id
        response["assignment_id"] = assignment_id
        response["completion_code"] = worker_code
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

        #save_worker_id(job_id=job_id, worker_id=worker_id, worker_code=worker_code, assignment_id=adapter.assignment_id)

        app.logger.debug(f"request-args: {request.args}, adapter: {adapter.to_dict()} ")
        try:
            expected_max_judgments = request.args.get("expected_max_judgments")
            if expected_max_judgments is not None:
                expected_max_judgments = int(expected_max_judgments)
                api = adapter.get_api()
                max_judgments = api.get_max_judgments()
                app.logger.debug(f"survey.done: max_judgments: {max_judgments} - {type(max_judgments)}, expected_max_judgments: {expected_max_judgments} - {type(expected_max_judgments)}")
                if max_judgments < expected_max_judgments:
                    app.logger.debug(f"try create new assignments")
                    create_res = api.create_additional_assignments(1)
                    app.logger.debug(f"post assignment creation: new-max: {api.get_max_judgments()} , mturk-api-res: {create_res}")
        except Exception as err:
            app.log_exception(err)

        # directly reply to AWS as the survey should be served as an external question!
        try:

            adapter = select_adapter()
            assignment_id = adapter.get_assignment_id()
            submit_to_kwargs = adapter.get_submit_to_kwargs()
            submit_to_url = adapter.get_submit_to_URL()

            url = os.path.join(submit_to_url, f"mturk/externalSubmit")
            payload = dict(submit_to_kwargs)
            res = requests.post(url, data=payload)
            app.logger.debug(f"submitted assignment to AWS: {res}")
        except Exception as err:
            app.log_exception(err)
        app.logger.info(f"handle_survey_done: saved new survey - job_id: {job_id}, worker_id: {worker_id}")
    req_response = make_response(render_template(template, worker_code=worker_code, dropped=True))
    set_cookie_obj(req_response, BASE, cookie_obj)
    for cookie in session.get(ALL_COOKIES_KEY, []):
        req_response.set_cookie(cookie, expires=0)
    session[ALL_COOKIES_KEY] = []
    return req_response