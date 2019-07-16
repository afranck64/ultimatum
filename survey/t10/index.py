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
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify, Response
)

import random

from survey.figure_eight import FigureEight

from core.models.metrics import MAX_GAIN
from survey._app import app, csrf_protect
from survey.admin import get_job_config
from survey.db import get_db, table_exists
from survey.figure_eight import RowState
from survey.utils import get_table, increase_worker_bonus
from survey.txx.prop import BASE as prop_BASE, finalize_round, JUDGING_TIMEOUT_SEC, LAST_MODIFIED_KEY, STATUS_KEY
from survey.txx.resp import BASE as resp_BASE, finalize_resp
from survey.txx.index import handle_index, handle_webhook


#### const
TREATMENT = os.path.split(os.path.split(__file__)[0])[1]
bp = Blueprint(f"{TREATMENT}", __name__)
############



@bp.route("/")
def index():
    return handle_index(TREATMENT)


@csrf_protect.exempt
@bp.route("/webhook/", methods=["GET", "POST"])
def webhook():
    return handle_webhook(TREATMENT)
