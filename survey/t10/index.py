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

from survey._app import app, csrf_protect
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
