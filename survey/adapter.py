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
    
    def get_submit_to_kwargs(self, **kwargs):
        raise NotImplementedError
    
    def is_preview(self):
        raise NotImplementedError
    
    def to_dict(self):
        raise NotImplementedError

    @classmethod
    def from_dict(self, dict_obj):
        raise NotADirectoryError


class DefaultAdapter(object):
    def __init__(self):
        self.job_id = request.args.get("job_id", "na")
        self.worker_id = request.args.get("worker_id", "na")
        self.unit_id = request.args.get("unit_id", "na")
        self.submit_to_URL = request.args.get("submit_to_URL")
        self.preview = request.args.get("preview") in {"1", "true"}
        self.submit_to_kwargs = {}

    def get_job_id(self):
        return self.job_id
    
    def get_worker_id(self):
        return self.worker_id
    
    def get_unit_id(self):
        return self.unit_id
    
    def get_submit_to_URL(self):
        return self.submit_to_URL
    
    def get_submit_to_kwargs(self):
        return self.submit_to_kwargs

    def is_preview(self):
        return self.is_preview
    
    def to_dict(self):
        obj_dict = dict(self.__dict__)
        obj_dict["_adapter"] = None
        return obj_dict
    
    @classmethod
    def from_dict(cls, dict_obj):
        adapter_key = dict_obj.get("_adapter")
        adapter_cls = ADAPTERS[adapter_key]
        adapter = adapter_cls()
        adapter.__dict__.update(dict_obj)
        return adapter

class MTurkAdapter(DefaultAdapter):
    def __init__(self):
        self.job_id = request.args.get("hitId")
        self.worker_id = request.args.get("workerId")
        self.unit_id = request.args.get("assignmentId")
        self.submit_to_URL = request.args.get("turkSubmitTo")
        self.preview = request.args.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE"
        self.submit_to_kwargs = {
            "assignmentId": request.args.get("assignmentId")
        }

    def to_dict(self):
        obj_dict = dict(self.__dict__)
        obj_dict["_adapter"] = None
        return obj_dict

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

def get_adapter_from_dict(dict_obj):
    adapter_key = dict_obj.get("_adapter")
    adapter_cls = ADAPTERS[adapter_key]
    adapter = adapter_cls()
    adapter.__dict__.update(dict_obj)
    return adapter
    