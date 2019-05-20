import itertools
import numpy as np
import pandas as pd
from notebooks.models.metrics import gain_mean, avg_loss_ratio


def generate_decision_area(model, features_df, target_label='offer'):
    data = features_df.values
    offer = model.predict(data)
    out_df = features_df.copy()
    out_df[target_label] =  offer
    return out_df


def generate_features_space_df(nb_features=2, nb_values=50, labels=None):
    if labels is None:
        labels = [f"x{idx}" for idx in range(1, nb_features+1)]
    features = [np.linspace(0, 1, nb_values) for _ in range(nb_features)]
    data = np.array(list(itertools.product(*features)))
    df_dict = {}
    for idx in range(nb_features):
        df_dict[labels[idx]] = data[:, idx]
    return pd.DataFrame(df_dict)
    