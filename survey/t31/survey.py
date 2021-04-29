import os
from flask import (
    render_template, Blueprint, url_for
)
from wtforms.validators import DataRequired, Optional, Regexp
from wtforms import StringField, IntegerField, BooleanField, RadioField, TextAreaField, SelectMultipleField, SelectField

from survey._app import app, csrf_protect
from survey.txx.survey import handle_survey, handle_survey_done, MainForm

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]

bp = Blueprint(f"{TREATMENT}.survey", __name__)

class AutoPropSurveyMainForm(MainForm):
    proposer_responder = RadioField("Choose the correct answer", choices=[
        ("correct", "The PROPOSER and the Responder are both humans"),
        ("incorrect1", "Your matched worker is not a real person"),
        ("incorrect2", "Your decisions do not affect another worker")],
        validators=[DataRequired("Please choose a value"), Regexp(regex="correct")]
    )


@csrf_protect.exempt
@bp.route(f"/", methods=["GET", "POST"])
def survey():
    return handle_survey(treatment=TREATMENT, form_class=AutoPropSurveyMainForm)

@bp.route(f"/done")
def survey_done():
    return handle_survey_done()
