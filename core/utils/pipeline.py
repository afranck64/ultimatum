import os
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, cross_validate
import joblib

from core.models.acceptance import AcceptanceModel
from core.models.cluster import ClusterExtModel
from core.models.metrics import avg_loss_ratio, avg_gain_ratio, MAX_GAIN
from core.utils.preprocessing import df_to_xy, df_to_xydf
from core.utils.explanation import get_pdf, get_bins
from core.utils.benchmark import process_benchmark_cv

DIRS = {
    "T00": ("t00", "t00"),
    "T10": ("t00", "t10"),
    "T11": ("t00", "t10"),
    "T12": ("t00", "t10"),
    "T13": ("t00", "t10"),
    "T20": ("t20", "t20"),
    "T21": ("t20", "t20"),
    "T22": ("t20", "t20"),
}

# sklearn require function's name to end either with error or score
def avg_loss_error(*args, **kwargs):
    return avg_loss_ratio(*args, **kwargs)

def avg_gain_score(*args, **kwargs):
    return avg_gain_ratio(*args, **kwargs)

def train_and_save(data_dir, output_dir, model=None, top_columns=None, shuffle=True, validation_split=0.2, random_state=None, target_column="min_offer", data_dir_filename="data.xls", drop_columns=None):
    if model is None:
        # model = AcceptanceModel()
        model = ClusterExtModel(base_model="affinity")
    if data_dir_filename.endswith(".xls"):
        df = pd.read_excel(os.path.join(data_dir, data_dir_filename))
    else:
        df = pd.read_csv(os.path.join(data_dir, data_dir_filename))
    # columns need to be dropped before using columns as features per default
    if drop_columns is not None:
        df = df[[col for col in df.columns if col not in drop_columns]]

    if top_columns is None:
        top_columns = [col for col in df.columns if col != target_column]
    if shuffle:
        df = df.sample(frac=1.0, random_state=random_state)
    df_min = df[top_columns].min()
    df_max = df[top_columns].max()
    x, y = df_to_xy(df, centered=True, select_columns=top_columns, df_min=df_min, df_max=df_max, drop_columns=drop_columns)

    split = x.shape[0]
    if validation_split is not None:
        split = int(x.shape[0] * (1 - validation_split))
    xTrain, yTrain = x[:split], y[:split]
    xVal, yVal = x[split:], y[split:]
    
    results = process_benchmark_cv(model, xTrain, yTrain, cv=5)
    avg_loss = results["avg_loss_ratio"].mean()
    
    # avg_loss = cross_val_score(model, x, y, scoring=avg_loss_error, error_score=1.0, cv=5)

    model.fit(xTrain, yTrain)
    val_acc = avg_gain_ratio(yVal, model.predict(xVal))
    acc = 1 - np.mean(avg_loss)
    rel_acc_std = np.std(avg_loss) / np.mean(avg_loss)
    yPred = model.predict(xTrain)
    unique_preds = np.unique(yPred)
    err = yPred.ravel() - yTrain.ravel()
    train_err_pdf, bins_train_err_pdf = np.histogram(err, bins=get_bins(is_symmetric=True, is_histogram=True), density=True)


    pdf, bins_pdf = get_pdf(df["min_offer"].values)
    infos = {
        "test_gain_mean": 0,
        "test_avg_loss_ratio": 0,
        "val_gain_main": 0,
        "val_avg_loss_ratio": 0,
        "top_columns": top_columns,
        "pdf": pdf.tolist(),
        "bins_pdf": bins_pdf.tolist(),
        "acc": acc,
        "val_acc": val_acc,
        "rel_acc_std": rel_acc_std,
        "train_err_pdf": train_err_pdf.tolist(),
        "bins_train_err_pdf": bins_train_err_pdf.tolist(),
        "unique_preds": unique_preds.tolist(),
        "df_min": df_min.to_dict(),
        "df_max": df_max.to_dict(),
    }

    with open(os.path.join(output_dir, "model.json"), "w") as out_file:
        json.dump(infos, out_file)
    
    joblib.dump(model, os.path.join(output_dir, "model.pkl"))
    return model, infos