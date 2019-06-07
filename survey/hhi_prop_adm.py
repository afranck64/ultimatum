import json
import os
import warnings
import random
import string

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect

from survey.figure_eight import FigureEight, API_KEY, JOB_ID, RowState
from survey.unit import Proposal,  proposal_to_proposal_result
from notebooks.utils.explanation import get_acceptance_propability, get_best_offer_probability
from notebooks.utils import value_repr
from notebooks.models.metrics import gain

SURVEY_INFOS_FILENAME = os.environ.get("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE_COMPLETION_CODE = os.environ.get("COMPLETION_CODE", "tTkEnH5A4syJ6N4t")

with open(SURVEY_INFOS_FILENAME) as inp_f:
    model_infos = json.load(inp_f)

fig8 = FigureEight(job_id=JOB_ID, api_key=API_KEY)
app = Flask(__name__)

csrf = CSRFProtect(app)

OFFER_VALUES = [str(val) for val in range(0, 201, 5)]

DEBUG = True

def generate_completion_code():
    part1 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    part2 = BASE_COMPLETION_CODE
    part3 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return "".join([part1, part2, part3])

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    final_offer = StringField("Final Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")


@app.route("/hhi_prop_adm", methods=["GET", "POST"])
def proposer_interactive():
    if request.method == "GET":
        session['proposal'] = Proposal()
        unit_id = request.args.get("unit_id", "")
        worker_id = request.args.get("worker_id", "")
        job_id = request.args.get("job_id", "")
        fig8 = FigureEight(job_id, API_KEY)
        row_info = fig8.row_get(unit_id)
        data = row_info.get("data", {})
        session["row_info"] = row_info
        print("Row info: ", row_info)
        #TODO: check if worker_id has started answering this unit
        #TODO: break
        if not row_info or row_info["state"] != RowState.JUDGABLE:
            warnings.warn(f"ERROR: The row can no longer be processed. unit_id: {unit_id} - worker_id: {worker_id}")
    if request.method == "POST":
        proposal = session["proposal"]
        proposal["time_stop"] = time.time()
        offer = request.form["offer"]
        try:
            offer = int(offer)
        except ValueError as err:
            offer = None
        proposal["offer"] = offer
        print("Done...", proposal)
        ##TODO return redirect
        #return redirect("/done")
        session['proposal'] = proposal
        return redirect("/done")

    session["proposer_interactive"] = True
    return render_template("hhi_prop_adm.html", offer_values=OFFER_VALUES, form=ProposerForm())

import time
import random
@app.route("/proposer_interactive/check", methods=["GET", "POST"])
def proposer_check():
    print(request.args)
    if not session.get("proposer_interactive", None):
        return "Sorry, you are not allowed to use this service. ^_^"
    if request.method == "POST":
        pass
    
    proposal = session["proposal"]
    offer = int(request.args.get("offer", 0))
    proposal["ai_calls_offer"].append(offer)

    proposal["ai_calls_time"].append(time.time())
    ai_offer = int(session["row_info"]["data"]["ai_offer"])
    print("proposal: ", offer)
    acceptance_probability = get_acceptance_propability(offer, model_infos["pdf"])
    best_offer_probability = get_best_offer_probability(ai_offer=ai_offer, offer=offer, accuracy=model_infos["acc"], train_err_pdf=model_infos["train_err_pdf"])

    #TODO: use the model predictions, data distribution to generate the ai_calls_response
    proposal["ai_calls_response"].append([acceptance_probability, best_offer_probability])
    session["proposal"] = proposal
    print("proposal: ", proposal)
    return jsonify({"offer": offer, "acceptance_probability": acceptance_probability, "best_offer_probability": best_offer_probability})
    #return "checked %s - acceptance: %s, best_offer: %s" % (offer, acceptance_probability, best_offer_probability)


@app.route("/done")
def done():
    worker_code = session.get('worker_code', '')
    worker_code = generate_completion_code()
    proposal = session["proposal"]
    row_info = session["row_info"]
    worker_bonus = gain(int(row_info["data"]["min_offer"]), proposal["offer"])
    print("RESULT: ", proposal_to_proposal_result(proposal))
    session.clear()
    return render_template("done.html", worker_code=worker_code, worker_bonus=value_repr(worker_bonus))

if __name__ == "__main__":
    app.config['SECRET_KEY'] = "You will never guess"
    app.run(host='0.0.0.0', port=8000)