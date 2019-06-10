
from survey import hhi_prop_adm

from survey._app import app

app.register_blueprint(hhi_prop_adm.bp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
