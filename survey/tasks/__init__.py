from flask import Blueprint
from survey.tasks import (cg, crt, eff, hexaco, risk, cpc, exp, goat, cc)
from survey._app import app
bp = Blueprint("tasks", __name__)

# MAX_BONUS = cg.MAX_BONUS + crt.MAX_BONUS + eff.MAX_BONUS + hexaco.MAX_BONUS + risk.MAX_BONUS
MAX_BONUS = 100

TASKS_FEATURES = {
    "cg": cg.FEATURES,
    "cpc": cpc.FEATURES,
    "crt": crt.FEATURES,
    "exp": exp.FEATURES,
    "eff": eff.FEATURES,
    "hexaco": hexaco.FEATURES,
    "goat": goat.FEATURES,
    "risk": risk.FEATURES,
    "cc": cc.FEATURES,
}

app.config["TASKS_FEATURES"] = TASKS_FEATURES