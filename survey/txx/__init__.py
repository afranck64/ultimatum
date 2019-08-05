import uuid

import requests
from flask import render_template, request, session, flash, url_for
from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField

from .index import check_is_proposer_next
from survey.utils import get_table, save_result2db, save_result2file, get_output_filename
from survey.db import insert, get_db
from survey._app import app

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
        ("65+_years", "Older than 65 Years")],
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
    code_resp_prop = StringField("Completion Code", )
    code_effort = StringField("Completion Code", )
    code_risk = StringField("Completion Code", )
    code_charitable_giving = StringField("Completion Code", )
    code_crt = StringField("Completion Code", )
    code_hexaco = StringField("Completion Code", )
    attention = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    comment = TextAreaField("Please enter your comments, feedback or suggestions below.")

def handle_survey():
    job_id = "home"
    worker_id = str(uuid.uuid4())
    treatment = "t10"
    session["job_id"] = job_id
    session["worker_id"] = worker_id
    session["treatment"] = treatment
    session["txx"] = True
    form = MainForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        print("SUBMITED BACK", request.form)
        #TODO: process and save form data
        form = MainForm(request.form)
        session["response"] = request.form.to_dict()
        return handle_survey_done()
    is_responder = not check_is_proposer_next(job_id, worker_id, treatment)
    return render_template("survey.html", job_id=job_id, worker_id=worker_id, treatment=treatment, form=form, is_responder=is_responder)

def handle_survey_done():
    if not session.get("txx"):
        flash("Sorry, you are not allowed to use this service. ^_^")
        return render_template("error.html")
    job_id = session["job_id"]
    worker_id = session["worker_id"]
    treatment = session["treatment"]

    response = session["response"]
    response["worker_id"] = worker_id
    result = {k:v for k,v in response.items() if k not in {'csrf_token'}}
    try:
        save_result2file(get_output_filename(base="survey", job_id=job_id, treatment=treatment), result)
    except Exception as err:
        app.log_exception(err)
    try:
        save_result2db(table=get_table(base="survey", job_id=job_id, schema="result", treatment=treatment), response_result=result, unique_fields=["worker_id"])
    except Exception as err:
        app.log_exception(err)
    # webhook_url = url_for(f"{treatment}.webhook", job_id=job_id, worker_id=worker_id)
    # requests.get(webhook_url)
    return render_template("info.html", job_id=job_id)
