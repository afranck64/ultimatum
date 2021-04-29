import os
from flask import Blueprint
from . import index, prop, resp, survey


TREATMENT = os.path.split(os.path.split(__file__)[0])[1]

bp = Blueprint(TREATMENT, __name__)
