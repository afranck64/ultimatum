import os
import time
import datetime
import pandas as pd

from flask import (
    Blueprint, redirect, request, url_for
)
from survey._app import app, csrf_protect
from survey.txx.resp import handle_done, handle_index_dss, handle_feedback
from survey.txx.resp import handle_done, handle_index, handle_index_dss, handle_feedback
from survey.globals import AI_SYSTEM_DESCRIPTION_BRIEF_STANDALONE_RESPONDER
from survey.globals import AI_SYSTEM_AUTO_DESCRIPTION_BRIEF_RESPONDER, AI_SYSTEM_AUTO_DESCRIPTION_EXTENDED_RESPONDER

############ Consts #################################

TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE = os.path.splitext(os.path.split(__file__)[1])[0]

bp = Blueprint(f"{TREATMENT}.resp", __name__)
######################################################



############# HELPERS   ###########################


@bp.route("/resp/", methods=["GET", "POST"])
def index():
    messages = None
    return handle_index(TREATMENT, messages=messages, has_dss_component=True)

@csrf_protect.exempt
@bp.route("/resp_dss/", methods=["GET", "POST"])
def index_dss():
    #messages = [AI_SYSTEM_AUTO_DESCRIPTION_BRIEF_RESPONDER]
    messages = [
        "Thank you for your minimum offer. You will now make another decision as a RESPONDER. An AI Machine-Learning System actually autonomously make an offer to you on behalf of a human PROPOSER. The human PROPOSER does not make any decisions, they only receives whatever money the system earns from this task.",
        AI_SYSTEM_AUTO_DESCRIPTION_EXTENDED_RESPONDER,
    ]
    return handle_index_dss(TREATMENT, messages=messages)

@csrf_protect.exempt
@bp.route("/resp_feedback/", methods=["GET", "POST"])
def feedback():
    return handle_feedback(TREATMENT, template="txx/resp_dss_feedback_t2x.html")


@bp.route("/resp/done")
def done():
    return handle_done(TREATMENT, no_features=True)
