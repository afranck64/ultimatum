import numpy as np
import os
import sys
import sqlite3

import pandas as pd


sys.path.append(os.path.abspath(".."))

from core.models.metrics import gain, MAX_GAIN
from survey._app import CODE_DIR, app
from survey.db import get_db


def get_data(data):
    return data[np.invert(np.isnan(data) | np.isinf(data))]

def get_mean(data):
    return data[np.invert(np.isnan(data) | np.isinf(data))].mean()

def get_std(data):
    return data[np.invert(np.isnan(data) | np.isinf(data))].std()

def get_woa_df(df):
    return woa(df['offer_final'], df['offer'], df['ai_offer'])


def woa(offer_final, offer, ai_offer):
    res = (abs(offer_final - offer) ) / (abs(ai_offer - offer ))
    # res = res[np.invert(np.isnan(res) | np.isinf(res))]
    # res = 100 * abs(res).mean()

    #res *= 100


    # return f"{res.mean():.2f} % +/-{ res.std():.2f}"
    return res


def mard(reference, new_value):
    res = abs(new_value - reference) / reference
    # res = res[np.invert(np.isnan(res) | np.isinf(res))]
    return abs(res)


def ard(reference, new_value):
    res = abs(new_value - reference) / reference
    # res = res[np.invert(np.isnan(res) | np.isinf(res))]
    return abs(res)

def get_proposer_mard_df(df):
    return mard(df["offer"], df["offer_final"])
    
def get_rel_gain(df_infos):
    acc = df_infos['avg_gain_ratio']['Proposer']
    acc_dss = df_infos['avg_gain_ratio']['Proposer + DSS']
    return 100 * abs(acc - acc_dss) / acc

def get_dss_usage(df_full):
    return (df_full.ai_nb_calls > 0) * 1
    #.mean()

def get_dss_average_unique_calls(df_full):
    return (df_full.ai_calls_count_repeated).mean()


def gain_responder(min_offer, offer):
    res = gain(min_offer, offer)
    mask = (res!= 0)
    res[mask] = MAX_GAIN - res[mask]
    return res

def get_gain_responder_df(df_full):
    return 


def get_rel_responder_abs_df(df_full):
    return mard(gain_responder(df_full["min_offer"], df_full["offer"]), gain_responder(df_full["min_offer_final"], df_full["offer_final"]))

def get_rel_min_offer_df(df):
    return ard(df["min_offer"], df["min_offer_dss"])
    #return (df["min_offer_dss"] - df["min_offer"]) / df["min_offer"]



def get_rel_gain_responder(min_offer, min_offer_dss, offer):
    gain_base = gain_responder(min_offer, offer)
    gain_dss = gain_responder(min_offer_dss, offer)
    res =  abs(gain_dss - gain_base) / gain_base

    # res = res[np.invert(np.isnan(res) | np.isinf(res))]
    
    # return f"{res.mean():.2f} % +/-{ res.std():.2f}"
    return res

def gain_proposer(min_offer, offer):
    return gain(min_offer, offer)

def get_proposer_gain_df(df):
    return gain_proposer(df["min_offer_final"], df["offer_final"])

def get_proposer_gain_no_dss_df(df):
    return gain_proposer(df["min_offer_final"], df["offer"])


def get_rel_gain_proposer(min_offer, offer, offer_dss):
    gain_base = gain_proposer(min_offer, offer)
    gain_dss = gain_proposer(min_offer, offer_dss)
    res = abs(gain_dss - gain_base) / gain_base

    # res = res[np.invert(np.isnan(res) | np.isinf(res))]
    
    # return f"{res.mean():.2f} % +/-{ res.std():.2f}"
    return res

def get_rel_gain_proposer_df(df):
    return get_rel_gain_proposer(df["min_offer_final"], df["offer"], df["offer_dss"])

def get_rel_gain_responder_df(df):
    return get_rel_gain_responder(df["min_offer"], df["min_offer_final"], df["offer_dss"])

def get_responder_min_offer(df):
    return df["min_offer_final"]

def get_proposer_offer(df):
    return df["offer_final"]
# print("rel_gain: ", round(get_rel_gain(df_infos), 2), "%")
# print("dss_usage: ", round(get_dss_usage(df_full), 2), "%")    
# print("woa: ", round(woa(df_full['offer_final'], df_full['offer'], df_full['ai_offer']), 2), "%")
# print("mard: ", round(mard(df_full['offer_final'], df_full['offer']),2), "%")




# def cronbach_alpha(itemscores):
#     itemvars = [svar(item) for item in itemscores]
#     tscores = [0] * len(itemscores[0])
#     for item in itemscores:
#        for i in range(len(item)):
#           tscores[i]+= item[i]
#     nitems = len(itemscores)
#     print("total scores=", tscores, 'number of items=', nitems)

#     Calpha=nitems/(nitems-1.) * (1-sum(itemvars)/ svar(tscores))

#     return Calpha
    # print(items)
    # items = pd.DataFrame(items)
    # items_count = items.shape[1]
    # variance_sum = float(items.var(axis=0, ddof=1).sum())
    # total_var = float(items.sum(axis=1).var(ddof=1))
    # print("VAR: ", total_var, items_count - 1)
    
    # return (items_count / float(items_count - 1) *
    #         (1 - variance_sum / total_var))