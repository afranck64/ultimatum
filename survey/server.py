from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.exceptions import abort

app = Flask(__name__)

OFFER_VALUES = [str(val) for val in range(0, 201, 5)]


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


@app.route("/done")
def done():
    worker_code = session.get('worker_code', '')
    return render_template("done.html", worker_code=worker_code)

if __name__ == "__main__":
    app.config['SECRET_KEY'] = "You will never guess"
    app.run(host='0.0.0.0', port=8000)