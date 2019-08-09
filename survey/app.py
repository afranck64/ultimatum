from flask import render_template
import warnings
import importlib

from survey import tasks
from survey import t10
from survey.txx import handle_survey, handle_survey_done
from survey import admin

from survey._app import app, csrf_protect

app.register_blueprint(tasks.cg.bp, url_prefix='/tasks')
app.register_blueprint(tasks.crt.bp, url_prefix='/tasks')
app.register_blueprint(tasks.eff.bp, url_prefix='/tasks')
app.register_blueprint(tasks.hexaco.bp, url_prefix='/tasks')
app.register_blueprint(tasks.risk.bp, url_prefix='/tasks')

for treatment in app.config["TREATMENTS"]:
    if app.config.get(treatment):
        try:
            txx = importlib.import_module(f"survey.{treatment.lower()}")
            app.register_blueprint(txx.index.bp, url_prefix=f"/{treatment.lower()}")
            app.register_blueprint(txx.prop.bp, url_prefix=f"/{treatment.lower()}")
            app.register_blueprint(txx.resp.bp, url_prefix=f"/{treatment.lower()}")
        except ImportError as err:
            #app.log_exception(err)
            warnings.warn(str(err))
            pass

app.register_blueprint(admin.bp)


@app.route("/")
def index():
    return render_template("home.html")

@csrf_protect.exempt
@app.route("/survey/", methods=["GET", "POST"])
def survey():
    return handle_survey()

@app.route("/survey/done")
def survey_done():
    return handle_survey_done()

@app.route("/survey/overview")
def overview():
    return render_template("overview.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
