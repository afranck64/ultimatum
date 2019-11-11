"""
Adapter
Transform available request args into known internal value
"""
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from flask import request, current_app as app
from survey.mturk import MTurk

class BaseAdapter(object):
    def get_job_id(self):
        raise NotImplementedError
    
    def get_worker_id(self):
        raise NotImplementedError
    
    def get_assignment_id(self):
        raise NotImplementedError

    def get_submit_to_URL(self):
        raise NotImplementedError
    
    def get_submit_to_kwargs(self, **kwargs):
        raise NotImplementedError
    
    def is_preview(self):
        raise NotImplementedError
    
    def to_dict(self):
        raise NotImplementedError

    @classmethod
    def from_dict(self, dict_obj):
        raise NotImplementedError

    def get_api(self, sandbox=None):
        raise NotImplementedError

    @classmethod
    def has_api(cls):
        raise NotImplementedError

class DefaultAdapter(BaseAdapter):
    def __init__(self):
        self.job_id = request.args.get("job_id", "").strip()
        self.worker_id = request.args.get("worker_id", "").strip()
        self.assignment_id = request.args.get("assignment_id", "").strip()
        self.submit_to_URL = request.args.get("submit_to_URL")
        self.preview = request.args.get("preview") in {"1", "true"} or self.job_id in ("", "na")
        if self.preview:
            self.worker_id = "na"
        self.submit_to_kwargs = {
            "job_id": self.job_id,
            "worker_id": self.worker_id,
            "assignment_id": self.assignment_id
        }

    def get_job_id(self):
        return self.job_id
    
    def get_worker_id(self):
        return self.worker_id
    
    def get_assignment_id(self):
        return self.assignment_id
    
    def get_submit_to_URL(self):
        return self.submit_to_URL
    
    def get_submit_to_kwargs(self):
        return self.submit_to_kwargs

    def is_preview(self):
        return self.preview
    
    def to_dict(self):
        obj_dict = dict(self.__dict__)
        obj_dict["_adapter"] = None
        return obj_dict

    @classmethod
    def has_api(cls):
        return False
    
    @classmethod
    def from_dict(cls, dict_obj):
        adapter_key = dict_obj.get("_adapter")
        adapter_cls = ADAPTERS[adapter_key]
        adapter = adapter_cls()
        adapter.__dict__.update(dict_obj)
        return adapter

class MTurkAdapter(DefaultAdapter):
    def __init__(self):
        referrer = request.headers.get("Referer")
        args_source = request.args
        app.logger.debug(f"adapter: referrer={referrer}")
        if referrer:
            parsed_url = urlparse(referrer)
            query = parse_qs(parsed_url.query)
            query_flat = {k:v[0] for k,v in query.items()}
            args_source = query_flat
        self.job_id = args_source.get("hitId", "").strip()
        self.worker_id = args_source.get("workerId", "").strip()
        self.assignment_id = args_source.get("assignmentId", "NA").strip()
        self.submit_to_URL = args_source.get("turkSubmitTo")
        self.preview = args_source.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE"
        if self.preview:
            self.worker_id = "na"
        self.submit_to_kwargs = {
            "assignmentId": args_source.get("assignmentId")
        }

    def to_dict(self):
        obj_dict = dict(self.__dict__)
        obj_dict["_adapter"] = "mturk"
        return obj_dict
    
    def get_api(self, sandbox=None):
        if sandbox is None:
            sandbox = app.config.get("MTURK_SANDBOX")
        return MTurk(self.get_job_id(), sandbox=sandbox)

    @classmethod
    def has_api(cls):
        return True
    

ADAPTERS = defaultdict(
    lambda: DefaultAdapter,
    mturk= MTurkAdapter,
)


def get_adapter() -> BaseAdapter:
    app.logger.debug("get_adapter")
    adapter_key = request.args.get("adapter")
    adapter_cls = ADAPTERS[adapter_key]
    app.logger.debug(f"get_adapter: {adapter_cls.__name__}")
    return adapter_cls()

def get_adapter_from_dict(dict_obj) -> BaseAdapter:
    adapter_key = dict_obj.get("_adapter")
    adapter_cls = ADAPTERS[adapter_key]
    adapter = adapter_cls()
    adapter.__dict__.update(dict_obj)
    return adapter
    