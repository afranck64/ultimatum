import json
import os
import warnings
import random
import string
import csv
import time
import datetime
import io
import hashlib

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, url_for, jsonify, Response
)

from survey._app import app, csrf_protect
from survey.db import get_db, table_exists
from survey.txx.index import get_table, handle_webhook, get_previous_worker_code, check_is_proposer_next, BASE, resp_BASE, prop_BASE, handle_index_feedback


#### const
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
BASE_TREATMENT = TREATMENT.split("_")[0]
bp = Blueprint(f"{TREATMENT}", __name__)
############



@bp.route("/")
def index():
    print("INFOS: ", TREATMENT, BASE_TREATMENT)
    return handle_index_feedback(TREATMENT, BASE_TREATMENT)
            


@csrf_protect.exempt
@bp.route("/webhook/", methods=["GET", "POST"])
def webhook():
    return handle_webhook(TREATMENT)
