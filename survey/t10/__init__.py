from flask import Blueprint
from . import index, prop, resp

bp = Blueprint("t10", __name__)
