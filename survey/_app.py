import os
from flask import (
    Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

csrf = CSRFProtect(app)

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

app.config["SECRET_KEY"] = SECRET_KEY