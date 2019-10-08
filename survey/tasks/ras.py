## Rathus Assertiveness Schedule
from flask import (
    Blueprint, render_template
)
import datetime
from survey._app import csrf_protect
from survey.tasks.task import handle_task_done, handle_task_index


#### const
bp = Blueprint("tasks.ras", __name__)

FIELDS = {f"q{i}" for i in range(1, 31)}
SCALAS = {
    -3: "very much like me",
    -2: "rather like me",
    -1: "slightly like me",
    1: "slightly unlike me",
    2: "rather unlike me",
    3: "very much unlike me"
}

# Items containing a star at the end are reversed items
AFFIRMATIONS = """1. Most people seem to be more aggressive and assertive than I am.*
2. I have hesitated to make or accept dates because of “shyness.”*
3. When the food served at a restaurant is not done to my satisfaction, I complain about it to the waiter or waitress.
4. I am careful to avoid hurting other people’s feelings, even when I feel that I have been injured.*
5. If a salesperson has gone to considerable trouble to show me merchandise that is not quite suitable, I have a difficult time saying “No.”*
6. When I am asked to do something, I insist upon knowing why.
7. There are times when I look for a good, vigorous argument.
8. I strive to get ahead as well as most people in my position.
9. To be honest, people often take advantage of me.*
10. I enjoy starting conversations with new acquaintances and strangers.
11. I often don’t know what to say to people I find attractive.*
12. I will hesitate to make phone calls to business establishments and institutions.*
13. I would rather apply for a job or for admission to a college by writing letters than by going through with personal interviews.*
14. I find it embarrassing to return merchandise.*
15. If a close and respected relative were annoying me, I would smother my feelings rather than express my annoyance.*
16. I have avoided asking questions for fear of sounding stupid.*
17. During an argument, I am sometimes afraid that I will get so upset that I will shake all over.*
18. If a famed and respected lecturer makes a comment which I think is incorrect, I will have the audience hear my point of view as well.
19. I avoid arguing over prices with clerks and salespeople.*
20. When I have done something important or worthwhile, I manage to let others know about it.
21. I am open and frank about my feelings.
22. If someone has been spreading false and bad stories about me, I see him or her as soon as possible and “have a talk” about it.
23. I often have a hard time saying “No.”*
24. I tend to bottle up my emotions rather than make a scene.*
25. I complain about poor service in a restaurant and elsewhere.
26. When I am given a compliment, I sometimes just don’t know what to say.*
27. If a couple near me in a theater or at a lecture were conversing rather loudly, I would ask them to be quiet or to take their conversation elsewhere.
28. Anyone attempting to push ahead of me in a line is in for a good battle.
29. I am quick to express an opinion.
30. There are times when I just can’t say anything.*""".splitlines()

AFFIRMATIONS_NO_STARS = [affirmation.replace("*", "") for affirmation in AFFIRMATIONS]

REVERSED_ITEMS = {f"q{idx+1}" for idx, affirmation in enumerate(AFFIRMATIONS) if affirmation[-1]=="*"}
FEATURES = {
    "ras_assertiveness",
    "ras_time_spent"
}
MAX_BONUS = 0

def validate_response(response):
    for field in FIELDS:
        if field not in response:
            return False
    return True


def response_to_result(response, job_id=None, worker_id=None):
    """
    The questions are saved "as-it" prior to reverserving questions scores to compute emotional traits
    :returns: {
        Honesty_Humility:
        Extraversion:
        Agreeableness:
        timestamp: server time when genererting the result
        job_id: fig-8 job id
        worker_id: fig-8 worker id
        *: response's keys
    }
    """
    result = dict(response)
    assertiveness = 0
    for item in FIELDS:
        scala = int(response[item])
        if item in REVERSED_ITEMS:
            assertiveness += (0 - scala)
        else:
            assertiveness += scala
    result["ras_assertiveness"] = assertiveness
    result["timestamp"] = str(datetime.datetime.now())
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["worker_bonus"] = response_to_bonus(response)
    return result

def response_to_bonus(response):
    return MAX_BONUS
############

@csrf_protect.exempt
@bp.route("/ras/", methods=["GET", "POST"])
def index():
    return handle_task_index("ras", validate_response, template_kwargs={"affirmations": AFFIRMATIONS_NO_STARS, "scalas": SCALAS})


@bp.route("/ras/done")
def done():
    return handle_task_done("ras", unique_fields=["worker_id"], response_to_result_func=response_to_result, numeric_fields="*")