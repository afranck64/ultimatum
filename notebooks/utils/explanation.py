import itertools
import numpy as np
import pandas as pd


def generate_decision_area(model, features_df, target_label='offer'):
    """
    :param model: Trained model
    :param features_df: (DataFrame) features
    :param target_label: (str) name of the predicted column
    """
    data = features_df.values
    offer = model.predict(data)
    out_df = features_df.copy()
    out_df[target_label] =  offer
    return out_df


def generate_features_space_df(nb_features=2, nb_values=50, labels=None):
    """
    Generates normalized features spaces
    :param nb_features: (int) number of features
    :param nb_values: (int|list) number of values for each features. if int, the same value is used for every features.
    :param labels: features names
    :returns: DataFrame
    """
    
    if labels is None:
        labels = [f"x{idx}" for idx in range(1, nb_features+1)]
    features = [np.linspace(0, 1, nb_values) for _ in range(nb_features)]
    data = np.array(list(itertools.product(*features)))
    df_dict = {}
    for idx in range(nb_features):
        df_dict[labels[idx]] = data[:, idx]
    return pd.DataFrame(df_dict)

def explain(features, labels=None):
    if labels is None:
        labels = [f'x{idx+1}' for idx in range(len(features))]
    personas = {
        'optimist',
        'pessimist',
        'envious',
        'trustful',
        'undefined'
    }

    infos = {
        0.0: 'very low',
        0.2: 'very low',
        0.4: 'low',
        0.6: 'average',
        0.8: 'high',
        1.0: 'very high',
    }

    res_parts =  []
    for idx in range(len(features)):
        for base_val, val_label in infos.items():
            if base_val >= features[idx]:
                res_parts.append(f'{val_label} {labels[idx]}')
                break
    return res_parts
