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


def get_pdf(data, max_gain=None, step=None):
    """
    :param data: (array) offers
    :param max_gain:
    :param step:
    :returns: (array) the pdf for offers contained in data
    """
    counts, bins = np.histogram(data, bins=get_bins(max_gain=max_gain, step=step), density=True)
    return counts, bins

def get_err_pdf(min_offer, offer, max_gain=None, step=None):
    """
    :param min_offer: (array)
    :param offer: (array)
    :param max_gain: (int)
    :param step: (int)
    """
    counts, bins = np.histogram(offer - min_offer, bins=get_bins(max_gain=max_gain, step=step), density=True)
    return counts, bins

def get_bins(max_gain=None, step=None, is_histogram=True, is_symmetric=False):
    """
    :param max_gain:
    :param step:
    :param  is_histogram: (bool) if True add one more bin to make shore <max_gain> will be included when using the bins to generate an histogram
    :param is_symmetric: (bool) if True, bins are in the range [-max_gain, max_gain] otherwhise [0, max_gain] (is_histogram is considered False in the example)
    :returns: (array)
    """
    if step is None:
        step = STEP
    if max_gain is None:
        max_gain = MAX_GAIN
    if is_symmetric:
        if is_histogram:
            return np.arange(-max_gain, max_gain+step+1, step)
        else:
            return np.arange(-max_gain, max_gain+step, step)
    else:
        if is_histogram:
            return np.arange(0, max_gain+step+1, step)
        else:
            return np.arange(0, max_gain+step, step)

def offer_to_bin(offer, is_symmetric=False, max_gain=None, step=None):
    """
    :param offer: (int) if is_symmetric is True,  offer is expected to be an offer difference, e.g. offer - min_offer
    :param is_symmetric: (bool) if True, expects offer to be an offer difference, e.g. offer-min_offer or offer-ai_offer
    :param max_gain: (int)
    :param step: (int)
    :returns: an index corresponding to a bin
    """
    if max_gain is None:
        max_gain = MAX_GAIN
    if step is None:
        step = STEP
    if offer >= max_gain:
        idx = -1
    elif offer <= 0 and not is_symmetric:
        idx = 0
    else:
        idx = int(offer // step)
    if is_symmetric:
        return idx + max_gain//step
    else:
        return idx


def get_acceptance_probability(offer, train_pdf):
    """
    :param offer: Human's offer to a given responder
    :param train_pdf: pdf of the training's target for the bins [0, 5, 10, ..., MAX_GAIN]
    :returns: probability of the human's offer to be accepted
    """
    n_train_df = np.array(train_pdf) / np.max(train_pdf)

    # We enforce increasing probability with increasing offer, taking into consideration
    # the fact that the data may be sparse
    corrected_pdf = n_train_df + 1e-3
    cum_train_pdf = np.cumsum(corrected_pdf)
    idx = offer_to_bin(offer)
    n_cum_train_pdf = cum_train_pdf / cum_train_pdf.max()
    
    return n_cum_train_pdf[idx]

def get_best_offer_probability(ai_offer, offer, accuracy, train_err_pdf, step=None, uncertainty=None, experiment_mode=True):
    """
    :param ai_offer: (int 0..MAX_GAIN) AI's offer to a given responder
    :param offer: (int 0..MAX_GAIN) Human's offer to a given responder
    :param accuracy: (float: 0..1) Model's accuracy
    :param train_err_pdf: (array) Model's training error pdf [from -MAX_GAIN to MAX_GAIN with steps 5]
    :param step: (int) step for bins values, default: 5
    :param uncertainty: (array|list<float>)
    :param experiment_mode: (bool) if True, enforce ai_offer to have the highest probability otherwhise
           takes training error into consideration
    :returns: probability of the human's offer being the best one
    """
    if step is None:
        step = 5
    if uncertainty is None:
        uncertainty = [0.02, 0.03, 0.04, 0.9, 0.005, 0.003, 0.002]
        # uncertainty = train_err_pdf
    # Scale values from
    train_err_pdf = np.array(train_err_pdf)
    # redistribute the probabilities to the neighbours to make the distribution more human intuitive
    train_err_pdf = np.convolve(train_err_pdf, uncertainty, mode="same")
    if experiment_mode:
        idx_zero = offer_to_bin(0, is_symmetric=True)
        idx_top = np.argmax(train_err_pdf)
        top_prob = train_err_pdf[idx_top]
        zero_prob = train_err_pdf[idx_zero]
        if zero_prob < top_prob:
            diff_prob = abs(top_prob - zero_prob)
            zero_prob += 1.5 * diff_prob
            top_prob -=  diff_prob
            train_err_pdf[idx_zero] = zero_prob
            train_err_pdf[idx_top] = top_prob
    n_train_err_pdf = np.array(train_err_pdf) / np.max(train_err_pdf)
    # the uncertainty is equi-probabily shared between all values
    n_train_err_pdf += (1 - accuracy) / (MAX_GAIN * 2)
    n_train_err_pdf /= np.max(n_train_err_pdf)
    estimated_err = (offer - ai_offer)
    idx = offer_to_bin(estimated_err, is_symmetric=True)
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
