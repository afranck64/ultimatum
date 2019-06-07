import os
import csv
import time
import datetime


class HHI_Prop_ADM(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["offer"] = None
        self["time_start"] = time.time()
        self["time_stop"] = None
        self["ai_calls_offer"] = []
        self["ai_calls_time"] = []
        self["ai_calls_response"] = []
        self["time_stop"] = None


def hhi_prop_adm_to_prop_result(proposal, job_id=None, worker_id=None, unit_id=None, row_data=None):
    """
    :returns: {
        offer: final proposer offer
        time_spent: whole time spent for the proposal
        ai_nb_calls: number of calls of the ADM system
        ai_call_min_offer: min offer checked on the ADM
        ai_call_max_offer: max offer checked on the ADM
        ai_mean_time: mean time between consecutive calls on to the ADM
        ai_call_offers: ":" separated values
    }
    """
    if row_data is None:
        row_data = {}
    result = {}
    result["time"] = str(datetime.datetime.now())
    result["offer"] = proposal["offer"]
    result["time_spent"] = proposal["time_stop"] - proposal["time_start"]
    ai_nb_calls = len(proposal["ai_calls_offer"])
    result["ai_nb_calls"] = ai_nb_calls
    if ai_nb_calls > 0:
        result["ai_call_min_offer"] = min(proposal["ai_calls_offer"])
        result["ai_call_max_offer"] = max(proposal["ai_calls_offer"])
    else:
        result["ai_call_min_offer"] = None
        result["ai_call_max_offer"] = None
    if ai_nb_calls == 0:
        result["ai_mean_time"] = 0
    elif ai_nb_calls == 1:
        result["ai_mean_time"] = proposal["ai_calls_time"][0] - proposal["time_start"]
    else:
        ai_times = []
        ai_times.append(proposal["ai_calls_time"][0] - proposal["time_start"])
        for idx in range(1, ai_nb_calls):
            ai_times.append(proposal["ai_calls_time"][idx] - proposal["ai_calls_time"][idx-1])
        result["ai_mean_time"] = sum(ai_times) / ai_nb_calls
    result["ai_call_offers"] = ":".join(str(val) for val in proposal["ai_calls_offer"])
    result["job_id"] = job_id
    result["worker_id"] = worker_id
    result["unit_id"] = unit_id
    for k, v in row_data.items():
        result[f"data__{k}"] = v
    return result


def save_prop_result(filename, proposal_result):
    file_exists = os.path.exists(filename)
    with open(filename, "a") as out_f:

        writer = csv.writer(out_f)
        if not file_exists:
            writer.writerow(proposal_result.keys())
        writer.writerow(proposal_result.values())