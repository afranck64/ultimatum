from flask import Blueprint
from survey.tasks import (cg, crt, eff, hexaco, risk)

bp = Blueprint("tasks", __name__)



# bp.register_blueprint(hexaco.bp)
# bp.register_blueprint(cg.bp)
# bp.register_blueprint(crt.bp)
# bp.register_blueprint(eff.bp)
# bp.register_blueprint(risk.bp)