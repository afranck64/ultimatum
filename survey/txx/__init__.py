import uuid

import requests
from flask import render_template, request, session, flash, url_for, redirect
from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField

from survey.utils import get_table, save_result2db, save_result2file, get_output_filename, get_latest_treatment
from survey.db import insert, get_db
from survey._app import app

BASE = "home"


class MainCPCForm(FlaskForm):
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
    code_cpc = StringField("Completion Code: Choices task", )
    test = RadioField("This is an attention check question. Please select the option 'BALL'", choices=[("apple", "APPLE"), ("ball", "BALL"), ("cat", "CAT")], validators=[DataRequired()])
    please_enter_your_comments_feedback_or_suggestions_below = TextAreaField("Please enter your comments, feedback or suggestions below.")

def handle_survey_cpc():
    job_id = f"{BASE}_cpc"
    worker_id = str(uuid.uuid4())
    treatment = get_latest_treatment()
    session["job_id"] = job_id
    session["worker_id"] = worker_id
    session["treatment"] = treatment
    session["txx"] = True
    form = MainCPCForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        form = MainCPCForm(request.form)
        session["response"] = request.form.to_dict()
        return redirect(url_for("survey_cpc_done"))
    return render_template("survey_cpc.html", job_id=job_id, worker_id=worker_id, treatment=treatment, form=form)


def handle_survey_cpc_done():
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
        save_result2file(get_output_filename(base="survey_cpc", job_id=job_id, treatment=treatment), result)
    except Exception as err:
        app.log_exception(err)
    try:
        save_result2db(table=get_table(base="survey_cpc", job_id=job_id, schema="result", treatment=treatment), response_result=result, unique_fields=["worker_id"])
    except Exception as err:
        app.log_exception(err)
    return render_template("info.html", job_id=job_id)