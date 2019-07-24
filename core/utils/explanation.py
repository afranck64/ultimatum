import itertools
import numpy as np
import pandas as pd

MAX_GAIN = 200
STEP = 5

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


def get_pdf(data, step=None):
    """
    """
    if step is None:
        step = 5
    counts, bins = np.histogram(np.append(data, MAX_GAIN), bins=np.arange(0, MAX_GAIN+1, step), density=True)
    return counts, bins

def get_err_pdf(min_offer, offer, step=None):
    if step is None:
        step = 5
    counts, bins = np.histogram(offer - min_offer, bins=np.arange(0, MAX_GAIN+1, step), density=True)
    return counts, bins


def offer_to_bin(offer):
    if offer >= MAX_GAIN:
        idx = -1
    elif offer <= 0:
        idx = 0
    else:
        idx = int(offer / 5)
    return idx


def get_acceptance_propability(offer, train_pdf):
    """
    :param offer: Human's offer to a given responder
    :param train_pdf: pdf of the training's target for the bins [0, 5, 10, ..., MAX_GAIN]
    :returns: probability of the human's offer to be accepted
    """
    n_train_df = np.array(train_pdf) / np.max(train_pdf)

    # We enforce increasing probability with increasing offer, taking into consideration
    # the fact that the data may be sparse
    corrected_pdf = n_train_df + np.arange(0, MAX_GAIN, STEP) / (MAX_GAIN * 100)

    cum_train_pdf = np.cumsum(corrected_pdf)
    idx = offer_to_bin(offer)
    n_cum_train_pdf = cum_train_pdf / cum_train_pdf.max()
    
    
    return n_cum_train_pdf[idx]

def get_best_offer_probability(ai_offer, offer, accuracy, train_err_pdf, step=None, uncertainty=None):
    """
    :param ai_offer: (int 0..MAX_GAIN) AI's offer to a given responder
    :param offer: (int 0..MAX_GAIN) Human's offer to a given responder
    :param accuracy: (float: 0..1) Model's accuracy
    :param train_err_pdf: (array) Model's training error pdf [from -MAX_GAIN to MAX_GAIN with steps 5]
    :param step: (int) step for bins values, default: 5
    :param uncertainty: (array|list<float>) 
    :returns: probability of the human's offer being the best one
    """
    if step is None:
        step = 5
    if uncertainty is None:
        uncertainty = [0.1, 0.02, 0.03, 0.9, 0.01, 0.01, 0.1]
    #NOTE: TODO: check ai_offer - offer vs offer - ai_offer + comment
    # Scale values from
    train_err_pdf = np.array(train_err_pdf)
    # redistribute the probabilities to the neighbours as they are
    train_err_pdf = np.convolve(train_err_pdf, uncertainty, mode="same")
    train_err_pdf /= train_err_pdf.sum()
    n_train_err_pdf = np.array(train_err_pdf) / np.max(train_err_pdf)
    # the uncertainty is equi-probabily shared between all values
    n_train_err_pdf += (1 - accuracy) / (MAX_GAIN * 2)
    n_train_err_pdf /= np.max(n_train_err_pdf)
    estimated_err = (offer - ai_offer)
    idx = int((estimated_err + MAX_GAIN)/step)
    idx = min(max(idx, 0), n_train_err_pdf.shape[0]-1)
    print(idx, n_train_err_pdf.shape)
    return accuracy * n_train_err_pdf[idx]
    



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
