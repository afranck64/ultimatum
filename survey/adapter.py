"""
Adapter
Transform available request args into known internal value
"""
from collections import defaultdict
from flask import request, current_app as app

class BaseAdapter(object):
    def get_job_id(self):
        raise NotImplementedError
    
    def get_worker_id(self):
        raise NotImplementedError
    
    def get_unit_id(self):
        raise NotImplementedError

    def get_submit_to_URL(self):
        raise NotImplementedError
    
    def is_preview(self):
        return NotImplementedError

class DefaultAdapter(object):
    def __init__(self):
        self.job_id = request.args.get("job_id")
        self.worker_id = request.args.get("worker_id")
        self.unit_id = request.args.get("unit_id")
        self.submit_to_URL = request.args.get("submit_to_URL")
        self.preview = request.args.get("preview") in {"1", "true"}

    def get_job_id(self):
        return self.job_id
    
    def get_worker_id(self):
        return self.worker_id
    
    def get_unit_id(self):
        return self.unit_id
    
    def get_submit_to_URL(self):
        return self.submit_to_URL
    
    def is_preview(self):
        return self.is_preview

class MTurkAdapter(DefaultAdapter):
    def __init__(self):
        self.job_id = request.args.get("hitId")
        self.worker_id = request.args.get("workerId")
        self.unit_id = request.args.get("assignmentId")
        self.submit_to_URL = request.args.get("turkSubmitTo")
        self.preview = request.args.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE"

ADAPTERS = defaultdict(
    lambda: DefaultAdapter,
    mturk= MTurkAdapter,
)


def get_adapter():
    app.logger.debug("get_adapter")
    adapter_key = request.args.get("adapter")
    adapter_cls = ADAPTERS[adapter_key]
    app.logger.debug(f"get_adapter: {adapter_cls.__name__}")
    return adapter_cls()