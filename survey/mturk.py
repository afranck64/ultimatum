import math
import os
import requests
import warnings
import boto3
from botocore.exceptions import ClientError


class Status(object):
    SUCCESS = 200
    ACCEPTED = 202
    REDIRECT = 302
    BAD_REQUEST = 400
    UNAUTHENTICATED = 401
    PAYMENT_REQUIRED = 402
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    UNIT_LIMIT_REACHED = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500

class RowState(object):
    NEW = "new"
    JUDGEABLE = "judgeable"
    JUDGING = "judging"
    JUDGED = "judged"
    ORDERED = "ordered"
    FINALIZED = "finalized"
    GOLDEN = "golden"
    HIDDEN_GOLD = "hidden_gold"
    CANCELED = "canceled"

class MTurk(object):
    def __init__(self, job_id, api_key=None, api_version=None, sandbox=True, *args, **kwargs):
        """
        Interface to the mturk api
        :param api_version: (str, default: "v1" )
        """
        endpoint_url = None
        if sandbox:
            endpoint_url = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
        self.client = boto3.client(
            'mturk',
            region_name="us-east-1",
            endpoint_url=endpoint_url
            )
        self.job_id = job_id
        self.api_key = api_key
        self.api_version = api_version

        # client_sts = boto3.client("sts")
        # account_id = client_sts.get_caller_identity()["Account"]
        # print(account_id)
    
    # def post(self, url, data=None, params=None, headers=None):
    #     if headers is None:
    #         pass
    
    # def get_url(self, worker_id=None, unit_id=None, endpoint=None, api_format="json"):
    #     """
    #     Build the required url
    #     worker_id and unit_id are mutually exclusive: they can't both appear in an url.
    #     If both are passed worker_id has priority over unit_id.
    #     :param worker_id: Worker/Contributor's id has
    #     :param unit_id: Row/Question's id
    #     :param endpoint: API path termination
    #     :param api_format: (json|csv, default: json)
    #     :returns: str
    #     """
    #     if worker_id is None and unit_id is None:
    #         if endpoint is not None:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/{endpoint}.{api_format}?key={self.api_key}"
    #         else:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}.{api_format}?key={self.api_key}"
    #     elif worker_id is not None:
    #         if endpoint is not None:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/workers/{worker_id}/{endpoint}.{api_format}?key={self.api_key}"
    #         else:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/workers/{worker_id}.{api_format}?key={self.api_key}"
    #     elif unit_id is not None:
    #         if endpoint is not None:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/units/{unit_id}/{endpoint}.{api_format}?key={self.api_key}"
    #         else:
    #             return f"https://api.figure-eight.com/{self.api_version}/jobs/{self.job_id}/units/{unit_id}.{api_format}?key={self.api_key}"



    # #### Job related actions
    # def job_upload(self, job_json, job_id=None):
    #     if job_id is None:
    #         url = f"https://api.figure-eight.com/{self.api_version}/jobs/upload.json?key={self.api_key}"
    #     else:
    #         url = self.get_url()
    #     return requests.post(url, json=job_json)
        


    # def job_pause(self):
    #     """Pauses a Job that is currently running."""
    #     url = self.get_url(endpoint="pause")
    #     return requests.get(url)
    
    # def job_resume(self):
    #     """Resumes a Job that had been paused"""
    #     url = self.get_url(endpoint="resume")
    #     return requests.get(url)

    # def job_cancel(self):
    #     url = self.get_url(endpoint="cancel")
    #     return requests.get(url)
    
    # def job_status(self):
    #     """
    #     :returns: json
    #     """
    #     url = self.get_url(endpoint="ping")
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}

    
    # def job_get(self):
    #     """
    #     :returns: json
    #     """
    #     url = self.get_url()
    #     return requests.get(url).json()
    

    # def job_report(self, report_type):
    #     """
    #     Generates job's report
    #     :param report_type:
    #     """
    #     url = self.get_url(endpoint="regenerate")  + f"&report={report_type}"
    #     return requests.post(url)
    
    # def job_report_save(self, report_type, filename):
    #     """
    #     Saves report
    #     :param report_type: (full|aggregated|json|gold_report|workset|source)
    #     :param filename: (str) filename path to a zip file where to save the report
    #     """
    #     url = self.get_url(api_format="csv") + f"&type={report_type}"
    #     resp = requests.post(url)
    #     if resp.status_code == Status.SUCCESS:
    #         with open(filename, "wb") as out_f:
    #             out_f.write(resp.content)
    #     else:
    #         warnings.warn("Something went wrong: %s" % resp)
    
    # def job_rows(self, page=None):
    #     page = page or "1"
    #     url = self.get_url(endpoint="units") + f"&page={page}&uni_id=2314014348" 
    #     rows_count = self.job_rows_count()
    #     if rows_count is None:
    #         resp = requests.get(url)
    #         if resp.status_code == Status.SUCCESS:
    #             return resp.json()
    #     else:
    #         err = 0
    #         result = dict()
    #         nb_pages = math.ceil(rows_count/1000)
    #         for page in range(1, rows_count+1):
    #             url = self.get_url(endpoint="units") + f"&page={page}&uni_id=2314014348" 
    #             resp = requests.get(url)
    #             if resp.status_code == Status.SUCCESS:
    #                 result.update(resp.json())
    #             else:
    #                 err = 1
    #                 break
    #         if err == 0:
    #             return result
    #     warnings.warn(resp.text)
    #     return {}
    
    # def job_rows_count(self):
    #     url = self.get_url(endpoint="units/ping")
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()["count"]
    #     warnings.warn(resp.text)
    #     return None
    
    # def jobs_user(self, page=None):
    #     """
    #     Queries all jobs under the account related to the API key
    #     :param page: 
    #     :returns: latest 10 jobs if page is None otherwise shifted job by page x 10
    #     """
    #     url = f"https://api.figure-eight.com/{self.api_version}/jobs.json?key={self.api_key}"
    #     if page:
    #         url += f"&page={page}"
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}
    
    # def jobs_team(self, team_id, page=None):
    #     """
    #     Queries for all Jobs under the team specified as a parameter.
    #     The API key used to make the call should belong to a user on the team.
    #     :param team_id:
    #     :param page: 
    #     :returns: latest 10 jobs if page is None otherwise shifted job by page x 10
    #     """
    #     url = f"https://api.figure-eight.com/{self.api_version}/jobs.json?key={self.api_key}&team_id={team_id}"
    #     if page:
    #         url += f"&page={page}"
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}
    

    # def account_info(self):
    #     url = f"https://api.figure-eight.com/{self.api_version}/jobs.json?key={self.api_key}"
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}

    
    
    # ### Row/Question related action
    # def row_get(self, unit_id):
    #     """
    #     Returns informations about a row
    #     """
    #     url = self.get_url(unit_id=unit_id)
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}
    
    # def row_get_data(self, unit_id):
    #     return self.row_get(unit_id).get("data", {})

    # def row_disable(self, unit_id):
    #     """
    #     Disable a question/row
    #     :param unit_id: Question/Row's id
    #     """
    #     url = self.get_url(unit_id=unit_id)
    #     return requests.put(url, json={"unit[state]":"hidden_gold"})
    
    # def row_judgments(self, unit_id):
    #     """
    #     Get all jugdments for the indicated row
    #     :param unit_id: Question/Row's id
    #     """
    #     url = self.get_url(unit_id=unit_id, endpoint="judgments")
    #     return requests.get(url)
    
    # def row_all_jugdments(self):
    #     """
    #     Get all rows and their jugdments
    #     """
    #     url = self.get_url(endpoint="judgments")
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}
    
    # def row_result(self, unit_id):
    #     """
    #     Get source data, all judgments and aggregate result for the indicated row
    #     :param unit_id: Question/Row's id
    #     """
    #     url = self.get_url(unit_id=unit_id)
    #     resp = requests.get(url)
    #     if resp.status_code == Status.SUCCESS:
    #         return resp.json()
    #     warnings.warn(resp.text)
    #     return {}


    ### Contributor related actions

    def contributor_pay(self, worker_id, amount_in_cents, assignment_id):
        """
        Pay a contributor bonus
        :param worker_id: Contributor/Worker's id
        :param amount_in_cents: USD amount in cents
        :param assignment_id:
        """

        #unique_token = f"{assignment_id}"
        try:
            bonus_amount_dollars = amount_in_cents / 100
            response = self.client.send_bonus(
                WorkerId=str(worker_id),
                BonusAmount=str(bonus_amount_dollars),
                AssignmentId=str(assignment_id),
                Reason=f"Thank you for your work. ^_^",
                #UniqueRequestToken=unique_token
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'RequestError':
                warnings.warn(f"{e}")
            else:
                raise e
        return False


    def contributor_notify(self, worker_id, message):
        """
        Sends a notification to a contributor
        :param worker_id:
        :param message: message to the worker
        """
        subject = f"Task - {self.job_id}"

        try:
            response = self.client.notify_workers(
                Subject=subject,
                MessageText=message,
                WorkerIds=[
                    worker_id
                ]
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'RequestError':
                warnings.warn(f"{e}")
            else:
                raise e
        return False

    def approve_assignment(self, assignment_id, message):
        try:
            response = self.client.approve_assignment(
                AssignmentId=assignment_id,
                RequesterFeedback=message,
                OverrideRejection=False
            )
            if len(response)==1 and response.get('ResponseMetadata'):
                return True
            else:
                warnings.warn(str(response))
                return False
        except ClientError as e:
            if e.response['Error']['Code'] == 'RequestError':
                warnings.warn(f"{e}")
            else:
                raise e
        return False

    def reject_assignment(self, assignment_id, message):
        try:
            response = self.client.reject_assignment(
                AssignmentId=assignment_id,
                RequesterFeedback=message
            )
            if not response:
                return True
            else:
                warnings.warn(str(response))
                return False
        except ClientError as e:
            if e.response['Error']['Code'] == 'RequestError':
                warnings.warn(f"{e}")
            else:
                raise e
        return False

    def get_account_balance(self):
        return self.client.get_account_balance()
    
    def get_max_judgments(self):
        try:
            response = self.client.get_hit(
                HITId=self.job_id
            )
            max_judgments = response['HIT']['MaxAssignments']
            return max_judgments
        except ClientError as e:
            warnings.warn(f"{e}")
        return 0
    
    def get_expected_judgments(self):
        try:
            response = self.client.get_hit(
                HITId=self.job_id
            )
            max_judgments = response['HIT']['MaxAssignments']
            return max_judgments
        except ClientError as e:
            warnings.warn(f"{e}")
        return 0

    def create_additional_assignments_for_hit(self, number_of_additional_assignments=1):
        
        try:
            self.client.get_hit(
                HITId=self.job_id,
                NumberOfAdditionalAssignments=number_of_additional_assignments
            )
            return True
        except ClientError as e:
            warnings.warn(f"{e}")
        return False
        
    # def contributor_flag(self, worker_id, reason):
    #     """
    #     Flag a contributor for the current job
    #     :param worker_id: Contributor/Worker's id
    #     :param reason: Reason for flagging the contributor
    #     """
    #     url = self.get_url(worker_id=worker_id)
    #     return requests.put(url=url, json={'flag': reason})
    
    # def contributor_flag_overall(self, worker_id, reason):
    #     """
    #     Flag a contributor overall
    #     :param worker_id: Contributor/Worker's id
    #     :param reason: Reason for flagging the contributor
    #     """
    #     url = self.get_url(worker_id=worker_id) + "&persist=true"
    #     return requests.put(url=url, json={'flag': reason})
    
    # def contributor_unflag(self, worker_id, reason):
    #     """
    #     Unflag a contributor
    #     :param worker_id: Contributor/Worker's id
    #     :param reason: Reason for unflagging the contributor
    #     """
    #     url = self.get_url(worker_id=worker_id)
    #     return requests.put(url=url, json={'unflag': reason})
    
    # def contributor_reject(self, worker_id, reason):
    #     """
    #     Reject a contributor
    #     :param worker_id: Contributor/Worker's id
    #     :param reason: Reason for rejecting the contributor
    #     """
    #     url = self.get_url(worker_id=worker_id, endpoint="reject")
    #     return requests.put(url=url, json={'reason': reason, 'manual': True})
