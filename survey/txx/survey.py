import os
import uuid

import requests
from flask import render_template, request, session, flash, url_for, redirect
from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField

from survey.utils import get_table, save_result2db, save_result2file, get_output_filename, get_latest_treatment, generate_completion_code, save_worker_id
from survey.db import insert, get_db
from survey._app import app
from survey.adapter import get_adapter, get_adapter_from_dict

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
        ("correct", "proposes a division of the 2 USD with the RESPONDER"),
        ("incorrect2", "accepts or rejects the offer made by the RESPONDER")],
        validators=[DataRequired("Please choose a value")]
    )
    responder = RadioField("The RESPONDER...", choices=[
        ("incorrect1", "decides the amount of money that the PROPOSER is paid"),
        ("incorrect2", "proposes a division of the 2 USD with the PROPOSER"),
        ("correct", "accepts or rejects the offer made by the PROPOSER")],
        validators=[DataRequired("Please choose a value")]
    )
    proposer_responder = RadioField("Choose the correct answer", choices=[
        ("correct", "The PROPOSER and the RESPONDER are both humans participating in the task simultaneously."),
        ("incorrect1", "Your matched worker is simulated by the computer and is not a real person."),
        ("incorrect2", "Your decisions do not affect another worker.")],
        validators=[DataRequired()]
    )
    code_resp_prop = StringField("Completion Code: main task", )
    code_effort = StringField("Completion Code: effort task", )
    code_risk = StringField("Completion Code: risk task", )
    code_charitable_giving = StringField("Completion Code: charitable giving", )
    code_crt = StringField("Completion Code: calculus task", )
    code_hexaco = StringField("Completion Code: hexaco task", )
    test = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    please_enter_your_comments_feedback_or_suggestions_below = TextAreaField("Please enter your comments, feedback or suggestions below.")

def handle_survey(treatment=None, template=None):
    if template is None:
        template = "txx/survey.html"
    adapter = get_adapter()
    arg_job_id = adapter.get_job_id()
    arg_worker_id = adapter.get_worker_id()
    job_id = arg_job_id or f"{treatment}_{BASE}"
    worker_id = arg_worker_id or str(uuid.uuid4())
    if treatment is None:
        treatment = get_latest_treatment()
    session["job_id"] = job_id
    session["worker_id"] = worker_id
    session["treatment"] = treatment
    session["adapter"] = adapter.to_dict()
    session[BASE] = True
    form = MainForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        form = MainForm(request.form)
        session["response"] = request.form.to_dict()
        return redirect(url_for("survey_done"))
    return render_template(template, job_id=job_id, worker_id=worker_id, treatment=treatment, form=form)

def handle_survey_done(template=None):
    if template is None:
        template = "txx/info.html"
    if not session.get(BASE):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    worker_code_key = f"{BASE}__worker_code"
    if not session.get(worker_code_key):
        job_id = session["job_id"]
        worker_id = session["worker_id"]
        treatment = session["treatment"]

        worker_code = generate_completion_code(base=treatment, job_id=job_id)
        response = session["response"]
        response["worker_id"] = worker_id
        result = {k:v for k,v in response.items() if k not in {'csrf_token'}}
        try:
            save_result2file(get_output_filename(base=BASE, job_id=job_id, treatment=treatment), result)
        except Exception as err:
            app.log_exception(err)
        try:
            save_result2db(table=get_table(base=BASE, job_id=job_id, schema="result", treatment=treatment), response_result=result, unique_fields=["worker_id"])
        except Exception as err:
            app.log_exception(err)

        adapter = get_adapter_from_dict(session["adapter"])
        app.logger.debug(f"adapter: {adapter} - {session['adapter']}")
        session.clear()
        session[BASE] = True
        session[worker_code_key] = worker_code

        submit_to_URL = adapter.get_submit_to_URL()
        if submit_to_URL is not None:
            try:
                requests.post(submit_to_URL, json=adapter.get_submit_to_kwargs())
            except Exception as err:
                app.logger.warn(f"{err}")
        # save_worker_id(job_id=job_id, worker_id=worker_id)
    return render_template(template, worker_code=session[worker_code_key])
