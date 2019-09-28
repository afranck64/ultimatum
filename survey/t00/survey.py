import os
from flask import (
    render_template, Blueprint
)

from survey._app import app, csrf_protect
from survey.txx.survey import handle_survey, handle_survey_done

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
from survey.db import insert, get_db
from survey._app import app
from survey.adapter import get_adapter, get_adapter_from_dict
from survey.txx.index import check_is_proposer_next, NEXT_IS_PROPOSER_WAITING

BASE = os.path.splitext(os.path.split(__file__)[1])[0]
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]

bp = Blueprint(f"{TREATMENT}.survey", __name__)


@csrf_protect.exempt
@bp.route(f"/", methods=["GET", "POST"])
def survey():
    return handle_survey(treatment=TREATMENT)

@bp.route(f"/done")
def survey_done():
    return handle_survey_done()
