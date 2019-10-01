from flask import Blueprint
from survey.tasks import (cg, crt, eff, hexaco, risk, cpc, exp, goat)
from survey._app import app
bp = Blueprint("tasks", __name__)

MAX_BONUS = cg.MAX_BONUS + crt.MAX_BONUS + eff.MAX_BONUS + hexaco.MAX_BONUS + risk.MAX_BONUS
