import os
import sys

import pandas as pd
import boto3

import argparse


def get_parser():
    parser = argparse.ArgumentParser(description='Add a qualification to users')
    parser.add_argument('--silent', action='store_true',help="do not send a notificaition")

    group = parser.add_mutually_exclusive_group()
    group2 = group.add_argument_group()
    group2.add_argument('--worker-id', help='')
    group2.add_argument('--worker-bonus', help='')
    group2.add_argument('--assignment-id', help='')
    group.add_argument('--file', type=argparse.FileType('r'),
                        help='csv file with a column <worker_id>')
    parser.add_argument('--reason', help='Thank you for your work. ^_^')
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



def pay_worker_bonus(client, worker_id, bonus_cents, assignment_id, reason=None):
    client.send_bonus(
        WorkerId=str(worker_id),
        BonusAmount=str(bonus_cents/100),
        AssignmentId=str(assignment_id),
        Reason= reason or "Thank you for your work. ^_^",
        #UniqueRequestToken=unique_token
    )


def main():
    client = get_client()
    print("Balance: ", client.get_account_balance()['AvailableBalance'])
    parser = get_parser()
    args = parser.parse_args()

    if args.worker_id is None and args.file is None:
        sys.exit("You should either pass worker_id or file")
    
    if args.worker_id is not None:
        workers_ids = [args.worker_id]
        bonuses_cents = [args.worker_bonus]
        assignments_ids = [args.assignment_id]
    else:
        df = pd.read_csv(args.file)
        workers_ids = df["worker_id"]
        bonuses_cents = df["worker_bonus"]
        assignments_ids = df["assignment_id"]
    
    for worker_id, bonus_cents, assignment_id in zip(workers_ids, bonuses_cents, assignments_ids):
        try:
            pay_worker_bonus(client, worker_id, bonus_cents, assignment_id, args.reason)
        except Exception as err:
            print(f"worker_id: {worker_id} - {err}")

    print("Final Balance: ", client.get_account_balance()['AvailableBalance'])

if __name__ == "__main__":
    main()
    