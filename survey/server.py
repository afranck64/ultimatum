from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from wtforms.widgets import html5
from flask_wtf.csrf import CSRFProtect

from survey.figure_eight import FigureEight
from survey.unit import HHI_Prop_ADM as Proposal

app = Flask(__name__)

csrf = CSRFProtect(app)

OFFER_VALUES = [str(val) for val in range(0, 201, 5)]
OFFER_VALUES.insert(0, None)

class ProposerCheckForm(FlaskForm):
    #offer = IntegerField("Offer", validators=[DataRequired, NumberRange(min=0, max=200)])
    offer = IntegerField("Offer: ", validators=[DataRequired, NumberRange(min=0, max=200)], widget=html5.NumberInput(5, 0, 200))
    submit = SubmitField("Submit to AI")

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired()])
    final_offer = StringField("Final Offer", validators=[DataRequired()])
    submit = SubmitField("Submit")

class ProposerForm(FlaskForm):
    offer = StringField("Offer", validators=[DataRequired()])
    submit = SubmitField("Submit")


class ProposerFinalForm(FlaskForm):
    final_offer = StringField("Final Offer", validators=[DataRequired()])
    submit = SubmitField("Submit")

class ResponderForm(FlaskForm):
    min_offer = StringField("Minimum offer", validators=[DataRequired()])
    submit = SubmitField("Submit")


class ResponderFinalForm(FlaskForm):
    final_min_offer = StringField("Final minimum offer", validators=[DataRequired()])
    submit = SubmitField("Submit")



@app.route('/')
def index():
    return "hello world"

@app.route("/responder", methods=["GET", "POST"])
def responder():
    return redirect("/responder/min_offer")

@app.route("/responder/min_offer", methods=["GET", "POST"])
def responder_min_offer():
    if request.method == "POST":
        min_offer = request.form["min_offer"]
        session["min_offer"] = min_offer
        return redirect("responder/final_min_offer")
    return render_template("responder_min_offer.html", offer_values=OFFER_VALUES, form=ResponderForm())

@app.route("/responder/final_min_offer", methods=["GET", "POST"])
def responder_final_min_offer():
    if request.method == "POST":
        final_min_offer = request.form["final_min_offer"]
        session["final_min_offer"] = final_min_offer
        session["worker_code"] = "done_r0000"
        return redirect("done")
    return render_template("responder_final_min_offer.html", offer_values=OFFER_VALUES, form=ResponderFinalForm())


@app.route("/proposer/offer", methods=["GET", "POST"])
def proposer_offer():
    if request.method == "POST":
        offer = request.form["offer"]
        session["offer"] = offer
        return redirect("proposer/final_offer")
    
    return render_template("proposer_offer.html", offer_values=OFFER_VALUES, form=ProposerForm())


@app.route("/proposer/final_offer", methods=["GET", "POST"])
def proposer_final_offer():
    if request.method == "POST":
        final_offer = request.form["final_offer"]
        session["final_offer"] = final_offer
        session["worker_code"] = "done_p0000"
        return redirect("done")
    
    return render_template("proposer_final_offer.html", offer_values=OFFER_VALUES, form=ProposerForm())


@app.route("/proposer", methods=["GET", "POST"])
@app.route("/proposer/", methods=["GET", "POST"])
def proposer():
    return redirect("proposer/offer")


@app.route("/proposer_interactive", methods=["GET", "POST"])
def proposer_interactive():
    if request.method == "GET":
        session['proposal'] = Proposal()
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
        session['proposal'] = Proposal()

    session["proposer_interactive"] = True
    return render_template("proposer_interactive.html", offer_values=OFFER_VALUES, form=ProposerForm())

import time
import random
@app.route("/proposer_interactive/check", methods=["GET", "POST"])
def check():
    print(request.args)
    if not session.get("proposer_interactive", None):
        return "Sorry, you are not allowed to use this service. ^_^"
    if request.method == "POST":
        pass
    
    proposal = session["proposal"]
    proposal["ai_calls_offer"].append(request.args.get("offer", None))

    proposal["ai_calls_time"].append(time.time())

    #TODO: use the model predictions, data distribution to generate the ai_calls_response
    proposal["ai_calls_response"].append(random.random())
    session["proposal"] = proposal
    print("proposal: ", proposal)
    return "checked %s - %s" % (request.args.get("offer", None), time.time())


@app.route("/done")
def done():
    worker_code = session.get('worker_code', '')
    return render_template("done.html", worker_code=worker_code)

if __name__ == "__main__":
    app.config['SECRET_KEY'] = "You will never guess"
    app.run(host='0.0.0.0', port=8000)