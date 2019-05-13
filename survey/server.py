from flask import Flask
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

app = Flask(__name__)

OFFER_VALUES = [str(val) for val in range(0, 201, 5)]

@app.route('/')
def index():
    return "hello world"

@app.route("/responder")
def responder():
    return render_template("responder.html")


@app.route("/proposer")
def proposer():
    return render_template("proposer.html", offer_values=OFFER_VALUES)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)