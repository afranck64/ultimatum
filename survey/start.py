import requests
import json

API_KEY = "Your_Figure Eight_API_Key"
job_id = "Your_Job_ID_or_Alias"

data = {'column1': 'helloworld', 'column2': 'helloworld2'}

request_url = "https://api.figure-eight.com/v1/jobs/{}/units.json".format(job_id)
headers = {'content-type': 'application/json'}

payload = {
    'key': API_KEY,
    'unit': {
    'data': data
    }
}

requests.post(request_url, data=json.dumps(payload), headers=headers)