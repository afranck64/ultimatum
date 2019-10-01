import os
from flask import (
    render_template, Blueprint
)

from survey._app import app, csrf_protect
from survey.txx.survey import handle_survey, handle_survey_done

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
