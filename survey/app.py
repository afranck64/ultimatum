from flask import render_template

from survey import hhi_prop_adm
from survey import admin

from survey._app import app

app.register_blueprint(hhi_prop_adm.bp)
app.register_blueprint(admin.bp)

@app.route("/")
def index():
    return render_template("index.html")    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
