import os
import time
import unittest
from unittest import mock
import requests
import random
from multiprocessing.pool import Pool, ThreadPool
from tests.test_survey import txx
from survey._app import app


TREATMENT = os.path.splitext(os.path.split(__file__)[1])[0][-3:]
NB_WORKERS = 4
NB_WORKER_TASKS = 4

def run_worker(prefix, treatment, client=None):
    # txx.test_index(client, TREATMENT, prefix=prefix)
    txx.test_index_auto(client, treatment.lower(), prefix=prefix)



def test_concurrency_thread():
    pool = ThreadPool(NB_WORKERS)
    for treatment in app.config["TREATMENTS"]:
        pool.starmap(run_worker, [(f"thread-{treatment}-{i+1}_", treatment) for i in range(NB_WORKER_TASKS)])


def test_concurrency_process():
    pool = Pool(NB_WORKERS)
    for treatment in app.config["TREATMENTS"]:
        pool.starmap(run_worker, [(f"process-{treatment}-{i+1}_", treatment) for i in range(NB_WORKER_TASKS)])
