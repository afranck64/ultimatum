import requests
import warnings

JOB_ID = "1377208"
API_KEY = "buCrBzWBggATJVyu5bzW"

class Status(object):
    SUCCESS = 200
    ACCEPTED = 202
    REDIRECT = 302
    BAD_REQUEST = 400
    UNAUTHENTICATED = 401
    PAYMENT_REQUIred = 402
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    UNIT_LIMIT_REACHED = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500

class FigureEight(object):
    def __init__(self, job_id, api_key, api_version="v1", *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        Interface to the figure eight api
        :param api_version: (str, default: "v1" )
        """
        self.job_id = job_id
        self.api_key = api_key
        self.api_version = api_version
    
    def get_url(self, worker_id=None, unit_id=None, endpoint=None, api_format="json"):
        """
        Build the required url
        worker_id and unit_id are mutually exclusive: they can't both appear in an url.
        If both are passed worker_id has priority over unit_id.
        :param worker_id: Worker/Contributor's id has
        :param unit_id: Row/Question's id
        :param endpoint: API path termination
        :param api_format: (json|csv, default: json)
        :returns: str
        """
        if worker_id is None and unit_id is None:
            if endpoint is not None:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/{endpoint}.{api_format}?key={self.api_key}"
            else:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}.{api_format}?key={self.api_key}"
        elif worker_id is not None:
            if endpoint is not None:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/workers/{worker_id}/{endpoint}.{api_format}?key={self.api_key}"
            else:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/workers/{worker_id}.{api_format}?key={self.api_key}"
        elif unit_id is not None:
            if endpoint is not None:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/units/{unit_id}/{endpoint}.{api_format}?key={self.api_key}"
            else:
                return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/units/{unit_id}.{api_format}?key={self.api_key}"



    #### Job related actions
    def job_pause(self):
        """Pauses a Job that is currently running."""
        url = self.get_url(endpoint="pause")
        return requests.get(url)
    
    def job_resume(self):
        """Resumes a Job that had been paused"""
        url = self.get_url(endpoint="resume")
        return requests.get(url)

    def job_cancel(self):
        url = self.get_url(endpoint="cancel")
        return requests.get(url)
    
    def job_status(self):
        """
        :returns: json
        """
        url = self.get_url(endpoint="ping")
        resp = requests.get(url)
        if resp.status_code == Status.SUCCESS:
            return resp.json()
    
    def job_get(self):
        """
        :returns: json
        """
        url = self.get_url()
        return requests.get(url).json()
    

    def job_report(self, report_type):
        """
        Generates job's report
        :param report_type:
        """
        url = self.get_url(endpoint="regenerate")  + f"&report={report_type}"
        return requests.post(url)
    
    def job_report_save(self, report_type, filename):
        """
        Saves report
        :param report_type: (full|aggregated|json|gold_report|workset|source)
        :param filename: (str) filename path to a zip file where to save the report
        """
        url_enable = self.get_url(api_format="csv") + f"&type={report_type}"
        resp = requests.post(url_enable)
        if resp.status_code == Status.SUCCESS:
            with open(filename, "wb") as out_f:
                out_f.write(resp.content)
        else:
            warnings("Something went wrong: %s" % resp)

    
    
    ### Row/Question related action
    def row_disable(self, unit_id):
        """
        Disable a question/row
        :param unit_id: Question/Row's id
        """
        url = self.get_url(unit_id=unit_id)
        return requests.put(url, json={"unit[state]":"hidden_gold"})
    
    def row_judgments(self, unit_id):
        """
        Get all jugdments for the indicated row
        :param unit_id: Question/Row's id
        """
        url = self.get_url(unit_id=unit_id, endpoint="judgments")
        return requests.get(url)
    
    def row_all_jugdments(self):
        """
        Get all rows and their jugdments
        """
        url = self.get_url(endpoint="judgments")
        return requests.get(url).json
    
    def row_result(self, unit_id):
        """
        Get source data, all judgments and aggregate result for the indicated row
        :param unit_id: Question/Row's id
        """
        url = self.get_url(unit_id=unit_id)
        return requests.get(url).json


    ### Contributor related actions

    def contributor_pay(self, worker_id, amout_in_cents):
        """
        Pay a contributor bonus
        :param worker_id: Contributor/Worker's id
        :amount_in_cents: USD amount in cents
        """
        url = self.get_url(worker_id=worker_id, endpoint="bonus")
        requests.post(url=url, json={"amount":amout_in_cents})

    def contributor_notify(self, worker_id, message):
        """
        Sends a notification to a contributor
        :param worker_id:
        :param message: message to the worker
        """
        url = self.get_url(worker_id=worker_id, endpoint="notify")
        requests.post(url=url, json={'message':message})
    
    def contributor_flag(self, worker_id, reason):
        """
        Flag a contributor for the current job
        :param worker_id: Contributor/Worker's id
        :param reason: Reason for flagging the contributor
        """
        url = self.get_url(worker_id=worker_id)
        requests.put(url=url, json={'flag': reason})
    
    def contributor_flag_overall(self, worker_id, reason):
        """
        Flag a contributor overall
        :param worker_id: Contributor/Worker's id
        :param reason: Reason for flagging the contributor
        """
        url = self.get_url(worker_id=worker_id) + "&persist=true"
        requests.put(url=url, json={'flag': reason})
    
    def contributor_unflag(self, worker_id, reason):
        """
        Unflag a contributor
        :param worker_id: Contributor/Worker's id
        :param reason: Reason for unflagging the contributor
        """
        url = self.get_url(worker_id=worker_id)
        requests.put(url=url, json={'unflag': reason})
    
    def contributor_reject(self, worker_id, reason):
        """
        Reject a contributor
        :param worker_id: Contributor/Worker's id
        :param reason: Reason for rejecting the contributor
        """
        url = self.get_url(worker_id=worker_id, endpoint="reject")
        requests.put(url=url, json={'reason': reason, 'manual': True})
    
    

    
if __name__ == "__main__":
    fig8 = FigureEight(api_key=API_KEY, job_id=JOB_ID)
    print(fig8.job_status())