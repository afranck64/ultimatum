import pandas as pd
import numpy as np

from core.models.metrics import MAX_GAIN
# #TODO: check later (import from models.metrics?)
# MAX_GAIN = 200

def df_to_xy(df, normalize=True, centered=False, fuse_risk=False, drop_columns=None, select_columns=None, normalize_target=False, min_target=None, max_target=None, df_min=None, df_max=None):
    """
    :param df:  DataFrame with features and target (min_offer is expected to be the target col)
    :param normalize: (bool) if True, features are normalized
    :param centered: (bool) if True, feature are shifted to have a 0 mean
    :param fuse_risk (bool) if True, fuse count_effort and cells into a new columns <effort> while dropping both cells and count_effort
    :param drop_columns: (list) list of features to drop from the dataset
    :param select_columns: (list) list of columns to select if availabe, drop_columns isn't considered
    :param normalize_target: (bool) if True, target columns is divided by 200
    :param min_target: min target prior to target normalization
    :param max_target: max target prior to target normalization
    :param df_min: DataFrame, if available will be used as min for data normalization
    :param df_max: DataFrame, if available will be used as max for data normalization
    """
    df_features, df_target = df_to_xydf(df=df, normalize=normalize, centered=centered, fuse_risk=fuse_risk, drop_columns=drop_columns, select_columns=select_columns, normalize_target=normalize_target, min_target=min_target, max_target=max_target, df_min=df_min, df_max=df_max)
    return df_features.values, df_target.values
        

def df_to_xydf(df, normalize=True, centered=False, fuse_risk=False, drop_columns=None, select_columns=None, normalize_target=False, min_target=None, max_target=None, df_min=None, df_max=None):
    """
    :param df:  (DataFrame) with features and target (min_offer is expected to be the target col)
    :param normalize: (bool) if True, features are normalized
    :param centered: (bool) if True, feature are shifted to have a 0 mean
    :param fuse_risk (bool) if True, fuse time_spent_risk and cells into a new columns <risk> while dropping both cells and time_spent_risk
    :param drop_columns: (list) list of features to drop from the dataset
    :param select_columns: (list) list of columns to select if availabe, drop_columns isn't considered
    :param normalize_target: (bool) if True, target columns is divided by 200
    :param min_target: (float) min target prior to target normalization
    :param max_target: (float) max target prior to target normalization
    :param df_min: DataFrame, if available will be used as min for data normalization
    :param df_max: DataFrame, if available will be used as max for data normalization
    """
    if "min_offer" not in df.columns:
        df["min_offer"] = np.nan
    if df_min is None:
        df_min = pd.Series(data={col:0 for col in df.columns})
    if df_max is None:
        df_max = pd.Series(data={col:0 for col in df.columns})
        df_max["cells"] = 50
        df_max["Honesty_Humility"] = 5.0
        df_max["Extraversion"] = 5.0
        df_max["Agreeableness"] = 5.0
        df_max["selfish"] = 60
        df_max["time_spent_risk"] = 152000.0
        df_max["time_spent_prop"] = 269000.0
        df_max["min_offer"] = 200
        import warnings

    if fuse_risk:
        risk_cols = ['cells', 'time_spent_risk']
        df_risk = df[risk_cols]
        df_risk = (df_risk - df_risk.min()) / (df_risk.max() - df_risk.min())
        df_risk['risk'] = df_risk['cells'] * df_risk['time_spent_risk']
        df = df[[col for col in df if col not in risk_cols]]    

        df_features = df[[col for col in df if col != 'min_offer']].copy()
        df_features['risk'] = df_risk['risk']
        df_target = df[['min_offer']].copy()
    
    else:
        df_features = df[[col for col in df if col != 'min_offer']].copy()
        df_target = df[['min_offer']].copy()


    cols = [col for col in df_features]
    if select_columns is not None:
        cols = select_columns
    elif drop_columns is not None:
        cols = [col for col in df_features if col not in drop_columns]
    df_features = df_features[cols]


    x = df.values[:, :-1]
    y = df.values[:, -1:]

    if normalize:
        f_min = df_features.min()
        f_max = df_features.max()
        if df_min is not None and df_max is not None:
            for col in f_min.index:
                if col in df_min and col in df_max:
                    f_min[col] = df_min[col]
                    f_max[col] = df_max[col]
        # make sure we don't have to divide by zero
        f_max[f_min==f_max] = 1.0
        df_features = (df_features - f_min) / (f_max - f_min)
    if centered:
        df_features -= df_features.mean()
    
    if min_target is not None:
        df_target[df_target < min_target] = min_target
     
    if max_target is not None:
        df_target[df_target > max_target] = max_target
    
    if normalize_target:
        df_target /= MAX_GAIN
    return df_features, df_target