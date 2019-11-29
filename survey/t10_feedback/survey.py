import os
from flask import (
    render_template, Blueprint, url_for
)

from flask_wtf.form import FlaskForm
from wtforms.validators import DataRequired, Optional, Regexp
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, BooleanField, RadioField, TextAreaField, SelectMultipleField, SelectField
from wtforms.widgets import ListWidget, CheckboxInput

from core.models.metrics import MAX_GAIN
from survey._app import app, csrf_protect
from survey.txx.survey import handle_survey_feedback, handle_survey_feedback_done

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]

bp = Blueprint(f"{TREATMENT}.survey", __name__)


@csrf_protect.exempt
@bp.route(f"/", methods=["GET", "POST"])
def survey():
    return handle_survey_feedback(treatment=TREATMENT)

@bp.route(f"/done")
def survey_done():
    return handle_survey_feedback_done()
