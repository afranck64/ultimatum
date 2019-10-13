from flask import Blueprint
from survey.tasks import (cg, crt, eff, hexaco, risk, cpc, exp, goat, cc, ras)
from survey._app import app
bp = Blueprint("tasks", __name__)

# MAX_BONUS = cg.MAX_BONUS + crt.MAX_BONUS + eff.MAX_BONUS + hexaco.MAX_BONUS + risk.MAX_BONUS
MAX_BONUS = 0

if "cc" in app.config["TASKS"]:
    MAX_BONUS += cc.MAX_BONUS
if "cg" in app.config["TASKS"]:
    MAX_BONUS += cg.MAX_BONUS
if "cpc" in app.config["TASKS"]:
    MAX_BONUS += cpc.MAX_BONUS
if "crt" in app.config["TASKS"]:
    MAX_BONUS += crt.MAX_BONUS
if "eff" in app.config["TASKS"]:
     MAX_BONUS += eff.MAX_BONUS
if "goat" in app.config["TASKS"]:
     MAX_BONUS += goat.MAX_BONUS
if "hexaco" in app.config["TASKS"]:
     MAX_BONUS += hexaco.MAX_BONUS
if "risk" in app.config["TASKS"]:
     MAX_BONUS += risk.MAX_BONUS
if "exp" in app.config["TASKS"]:
     MAX_BONUS += exp.MAX_BONUS
if "ras" in app.config["TASKS"]:
     MAX_BONUS += ras.MAX_BONUS

_TASKS_FEATURES = {
    "cg": cg.FEATURES,
    "cpc": cpc.FEATURES,
    "crt": crt.FEATURES,
    "exp": exp.FEATURES,
    "eff": eff.FEATURES,
    "hexaco": hexaco.FEATURES,
    "goat": goat.FEATURES,
    "risk": risk.FEATURES,
    "cc": cc.FEATURES,
    "ras": ras.FEATURES,
}

TASKS_FEATURES = {k:(v if k in app.config["TASKS"] else []) for k,v in _TASKS_FEATURES.items()}

app.config["TASKS_FEATURES"] = TASKS_FEATURES