import json
import os
import warnings
import random
import string
import csv
import time
import datetime

from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect

from survey._app import app
from survey.figure_eight import FigureEight, API_KEY, JOB_ID, RowState
#from survey.unit import HHI_Prop_ADM,  hhi_prop_adm_to_prop_result, save_prop_result
from notebooks.utils.explanation import get_acceptance_propability, get_best_offer_probability
from notebooks.utils import value_repr
from notebooks.models.metrics import gain


############ Consts #################################
TUBE_RES_FILENAME = os.environ.get("TUBE_RES_FILENAME", "./data/HH_SURVEY1/output/hhi_prop_adm.csv")

SURVEY_INFOS_FILENAME = os.environ.get("MODEL_INFOS_PATH", "./data/HH_SURVEY1/UG_HH_NEW.json")

BASE_COMPLETION_CODE = os.environ.get("COMPLETION_CODE", "tTkEnH5A4syJ6N4t")


OFFER_VALUES = {str(val):value_repr(val) for val in range(0, 201, 5)}

DEBUG = True

with open(SURVEY_INFOS_FILENAME) as inp_f:
    MODEL_INFOS = json.load(inp_f)
######################################################



############# HELPERS   ###########################

class HHI_Prop_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["offer"] = None
        self["time_start"] = time.time()
        self["time_stop"] = None
        self["ai_calls_offer"] = []
        self["ai_calls_time"] = []
        self["ai_calls_response"] = []
        self["time_stop"] = None


def hhi_prop_adm_to_prop_result(proposal, job_id=None, worker_id=None, unit_id=None, row_data=None):
    """
    :returns: {
        time: server time when genererting the result
        offer: final proposer offer
        time_spent: whole time spent for the proposal
        ai_nb_calls: number of calls of the ADM system
        ai_call_min_offer: min offer checked on the ADM
        ai_call_max_offer: max offer checked on the ADM
        ai_mean_time: mean time between consecutive calls on to the ADM
        ai_call_offers: ":" separated values
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        unit_id: fig-8 unit/row id
        data__*: base unit data
    }
    """
    if row_data is None:
        row_data = {}
    result = {}
    result["time"] = str(datetime.datetime.now())
    result["offer"] = proposal["offer"]
    result["time_spent"] = proposal["time_stop"] - proposal["time_start"]
    ai_nb_calls = len(proposal["ai_calls_offer"])
    result["ai_nb_calls"] = ai_nb_calls
    if ai_nb_calls > 0:
        result["ai_call_min_offer"] = min(proposal["ai_calls_offer"])
        result["ai_call_max_offer"] = max(proposal["ai_calls_offer"])
    else:
        result["ai_call_min_offer"] = None
        result["ai_call_max_offer"] = None
    if ai_nb_calls == 0:
        result["ai_mean_time"] = 0
    elif ai_nb_calls == 1:
        result["ai_mean_time"] = proposal["ai_calls_time"][0] - proposal["time_start"]
    else:
        ai_times = []
        ai_times.append(proposal["ai_calls_time"][0] - proposal["time_start"])
        for idx in range(1, ai_nb_calls):
            ai_times.append(proposal["ai_calls_time"][idx] - proposal["ai_calls_time"][idx-1])
        result["ai_mean_time"] = sum(ai_times) / ai_nb_calls
    result["ai_call_offers"] = ":".join(str(val) for val in proposal["ai_calls_offer"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["unit_id"] = unit_id
    for k, v in row_data.items():
        result[f"data__{k}"] = v
    return result


def save_prop_result(filename, proposal_result):
    prefix = ""
    if "job_id" in proposal_result:
        folder, fname = os.path.split(filename)
        filename = os.path.join(folder, f"{proposal_result['job_id']}__{fname}")
    file_exists = os.path.exists(filename)
    os.makedirs(os.path.split(filename)[0], exist_ok=True)
    with open(filename, "a") as out_f:

        writer = csv.writer(out_f)
        if not file_exists:
            writer.writerow(proposal_result.keys())
        writer.writerow(proposal_result.values())


def generate_completion_code():

    part1 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    part2 = BASE_COMPLETION_CODE
    part3 = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return "".join([part1, part2, part3])

############################################################


fig8 = FigureEight(job_id=JOB_ID, api_key=API_KEY)

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired(), InputRequired()])
    submit = SubmitField("Submit")


@app.route("/hhi_prop_adm", methods=["GET", "POST"])
def hhi_prop_adm():
    if request.method == "GET":
        session['proposal'] = HHI_Prop_ADM()
        unit_id = request.args.get("unit_id", "")
        worker_id = request.args.get("worker_id", "")
        job_id = request.args.get("job_id", "")
        fig8 = FigureEight(job_id, API_KEY)
        row_info = fig8.row_get(unit_id)
        session["unit_id"] = unit_id
        session["worker_id"] = worker_id
        session["job_id"] = job_id
        data = row_info.get("data", {})
        session["row_info"] = row_info
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
        ##TODO return redirect
        session['proposal'] = proposal
        return redirect(url_for("done"))

    session["hhi_prop_adm"] = True
    return render_template("hhi_prop_adm.html", offer_values=OFFER_VALUES, form=ProposerForm())

import time
import random
@app.route("/hhi_prop_adm/check", methods=["GET", "POST"])
def proposer_check():
    if not session.get("hhi_prop_adm", None):
        return "<h1>Sorry, you are not allowed to use this service. ^_^</h1>"
    if request.method == "POST":
        pass
    
    proposal = session["proposal"]
    offer = int(request.args.get("offer", 0))
    proposal["ai_calls_offer"].append(offer)

    proposal["ai_calls_time"].append(time.time())
    ai_offer = int(session["row_info"]["data"]["ai_offer"])
    acceptance_probability = get_acceptance_propability(offer, MODEL_INFOS["pdf"])
    best_offer_probability = get_best_offer_probability(ai_offer=ai_offer, offer=offer, accuracy=MODEL_INFOS["acc"], train_err_pdf=MODEL_INFOS["train_err_pdf"])

    #TODO: use the model predictions, data distribution to generate the ai_calls_response
    proposal["ai_calls_response"].append([acceptance_probability, best_offer_probability])
    session["proposal"] = proposal
    print("proposal: ", proposal)
    return jsonify({"offer": offer, "acceptance_probability": acceptance_probability, "best_offer_probability": best_offer_probability})
    #return "checked %s - acceptance: %s, best_offer: %s" % (offer, acceptance_probability, best_offer_probability)


@app.route("/hhi_prop_adm/done")
def done():
    if not session.get("hhi_prop_adm", None):
        return "<h1>Sorry, you are not allowed to use this service. ^_^</h1>"
    worker_code = session.get('worker_code', '')
    worker_code = generate_completion_code()
    proposal = session["proposal"]
    row_info = session["row_info"]
    job_id = session["job_id"]
    worker_id = session["worker_id"]
    unit_id = session["unit_id"]
    worker_bonus = gain(int(row_info["data"]["min_offer"]), proposal["offer"])
    prop_result = hhi_prop_adm_to_prop_result(proposal, job_id=job_id, worker_id=worker_id, unit_id=unit_id, row_data=row_info["data"])
    print("RESULT: ", hhi_prop_adm_to_prop_result(proposal))
    save_prop_result(TUBE_RES_FILENAME, prop_result)
    session.clear()
    return render_template("done.html", worker_code=worker_code, worker_bonus=value_repr(worker_bonus))

#app.config["SECRET_KEY"] = SECRET_KEY
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)