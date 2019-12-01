import os
import sys

import pandas as pd
import boto3

import argparse


def get_parser():
    parser = argparse.ArgumentParser(description='Add a qualification to users')
    parser.add_argument('--silent', action='store_true',help="do not send a notificaition")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--worker-id', help='')
    group.add_argument('--file', type=argparse.FileType('r'),
                        help='csv file with a column <worker_id>')
    parser.add_argument('subject', help='subject of the notification')
    parser.add_argument('message', help='content of the notification to send to workers')
    return parser

def _env2bool(env_value):
    if env_value is None:
        return False
    return env_value.upper() in {"YES", "TRUE", "ENABLED"}

MTURK_SANDBOX = _env2bool(os.getenv("MTURK_SANDBOX"))

def get_client(sandbox=MTURK_SANDBOX):
    endpoint_url = None
    if sandbox:
        endpoint_url = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
    client = boto3.client(
        'mturk',
        region_name="us-east-1",
        endpoint_url=endpoint_url
    )
    return client



def notify_workers(client, subject, message, worker_ids):
    return client.notify_workers(
        Subject=subject,
        MessageText=message,
        WorkerIds=worker_ids
    )


def main():
    client = get_client()
    parser = get_parser()
    args = parser.parse_args()

    if args.worker_id is None and args.file is None:
        sys.exit("You should either pass worker_id or file")
    
    if args.worker_id is not None:
        workers_ids = [args.worker_id]
    else:
        workers_ids = list(pd.read_csv(args.file)["worker_id"])
    
    for worker_id in workers_ids:
        try:
            res = notify_workers(client, args.subject, args.message, [worker_id])
            if res.get("NotifyWorkersFailureStatuses"):
                print(f"worker_id: {worker_id} - {res['NotifyWorkersFailureStatuses'][0]['NotifyWorkersFailureMessage']}")
        except Exception as err:
            print(f"worker_id: {worker_id} - {err}")

if __name__ == "__main__":
    main()
    