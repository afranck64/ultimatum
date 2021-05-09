from flask import (
    Blueprint, render_template
)

from survey._app import app, csrf_protect
from survey.db import get_db, table_exists


bp = Blueprint(__name__, __name__)


###### helpers #####

def get_treaments_infos(con, treatments):
    all_infos = {}
    for treatment in treatments:
        infos = {}
        table_survey = f"result__{treatment}_survey"
        if table_exists(con, table_survey):
            sql_completed_surveys = f"""select
                r.job_id,
                count(*) count,
                (select count(*) from {table_survey}  where job_id==r.job_id and completion_code=='dropped') dropped
            FROM {table_survey} r
            GROUP BY job_id;
            """

            res = con.execute(sql_completed_surveys).fetchall()
            res = [{'job_id':item[0], 'count' : item[1], "dropped":item[2]} for item in res]
            infos["survey"] =res
        else:
            infos["survey"] = None
        
        table_resp = f"result__{treatment}_resp"
        if table_exists(con, table_resp):
            sql_completed_resp = f"""
            SELECT
                job_id,
                count(*)
            FROM {table_resp}
            GROUP BY job_id
            """
            completed_resp = dict(con.execute(sql_completed_resp).fetchall())
            infos["resp"] = completed_resp
        else:
            infos["resp"] = None

        table_prop = f"result__{treatment}_prop"
        if table_exists(con, table_prop):
            sql_completed_prop = f"""
            SELECT
                job_id,
                count(*)
            FROM {table_prop}
            GROUP BY job_id
            """
            completed_prop = dict(con.execute(sql_completed_prop).fetchall())
            infos["prop"] = completed_prop
        else:
            infos["prop"] = None

        all_infos[treatment] = infos
    return all_infos

####################


@csrf_protect.exempt
@bp.route("/dashboard", methods=["GET", "POST"])
def index():
    app.logger.debug(f"dashboard.index")
    treatments = [treatment.lower() for treatment in reversed(app.config["TREATMENTS"])]
    infos = get_treaments_infos(get_db('DB'), treatments)
    return render_template("dashboard.html", treatments=treatments, infos=infos)

