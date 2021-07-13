import os
from flask import (
    Blueprint
)
from survey._app import csrf_protect
from survey.txx.start import handle_start

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]

bp = Blueprint(f"{TREATMENT}.start", __name__)



@csrf_protect.exempt
@bp.route(f"/", methods=["GET"])
def survey():
    return handle_start(treatment=TREATMENT)#, overview_url=url_for("overview_auto_prop"))
