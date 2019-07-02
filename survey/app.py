from flask import render_template

from survey import tasks
from survey import t10
from survey import admin

from survey._app import app

app.register_blueprint(tasks.cg.bp, url_prefix='/tasks')
app.register_blueprint(tasks.crt.bp, url_prefix='/tasks')
app.register_blueprint(tasks.eff.bp, url_prefix='/tasks')
app.register_blueprint(tasks.hexaco.bp, url_prefix='/tasks')
app.register_blueprint(tasks.risk.bp, url_prefix='/tasks')

app.register_blueprint(t10.index.bp, url_prefix='/t10')
app.register_blueprint(t10.prop.bp, url_prefix='/t10')
app.register_blueprint(t10.resp.bp, url_prefix='/t10')
##
app.register_blueprint(admin.bp)

@app.route("/")
def index():
    return render_template("index.html")    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
