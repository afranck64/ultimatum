import numpy as np

MAX_GAIN = 200

# def loss(min_offer, predicted):
#     """
#     Compute loss for the ultimatum game,
#     as the difference between the possible gain and the actual one
#     """
#     min_offer = min_offer.ravel()
#     predicted = predicted.ravel()
#     rejected = min_offer > predicted
#     accepted = min_offer <= predicted
#     res = predicted - min_offer
#     if rejected.sum() != 0:
#         res[rejected] = 0
#     if accepted.sum() != 0:
#         res[accepted] = MAX_GAIN - min_offer[accepted]
#     low_bad_predictions = (predicted < 0)
#     if low_bad_predictions.sum() != 0:
#         res[low_bad_predictions] = 0
#     high_bad_prediction = (predicted > MAX_GAIN)
#     if high_bad_prediction.sum() != 0:
#         res[high_bad_prediction] = 0
#     return res

@np.vectorize
def loss(min_offer, predicted):
    """
    Compute loss for the ultimatum game,
    as the difference between the possible gain and the actual one
    """
    return MAX_GAIN-min_offer if predicted < min_offer else predicted - min_offer

def loss_sum(min_offer, predicted):
    return loss(min_offer.ravel(), predicted.ravel()).sum()

def avg_loss(min_offer, predicted):
    """
    Compute avg loss for the ultimatum game
    """
    return np.mean(loss(min_offer.ravel(), predicted.ravel()))

def mse(min_offer, predicted):
    """
    Compute mse using the loss as error
    """
    min_offer = min_offer.ravel()
    predicted = predicted.ravel()
    return np.mean(np.square(loss(min_offer.ravel(), predicted.ravel())))

def rejection_ratio(min_offer, predicted):
    """
    Compute ratio of rejected proposals without consideration of values
    """
    accepted = (min_offer <= predicted)
    return 1 - np.mean(accepted)

def avg_win_loss(min_offer, predicted):
    """
    Compute avg_loss of accepted proposals
    """
    min_offer = min_offer.ravel()
    predicted = predicted.ravel()
    accepted = (min_offer <= predicted)
    if accepted.sum() == 0:
        return 0
    return avg_loss(min_offer[accepted], predicted[accepted])


# def gain(min_offer, predicted):
#     min_offer = min_offer.ravel()
#     predicted = predicted.ravel()    
#     res = MAX_GAIN - predicted
#     res[predicted < min_offer] = 0
#     return res

@np.vectorize
def gain(min_offer, predicted):
    return 0 if predicted < min_offer else MAX_GAIN - predicted

def avg_loss_ratio(min_offer, predicted):
    """
    Compute the avg gain ratio in relation to the maximal gain
    """
    min_offer = min_offer.ravel()
    predicted = predicted.ravel()
    numerator, denominator = gain(min_offer, predicted), gain(min_offer, min_offer)
    zero_mask = denominator==0
    denominator[zero_mask] = 1  #avoid division by zero
    tmp = numerator / denominator
    tmp[denominator==0] = 1
    return 1 - np.mean(tmp)

def gain_mean(min_offer, predicted):
    min_offer = min_offer.ravel()
    predicted = predicted.ravel()
    return gain(min_offer, predicted).mean()

def avg_gain_ratio(min_offer, predicted):
    min_offer = min_offer.ravel()
    predicted = predicted.ravel()
    numerator, denominator = gain(min_offer, predicted), gain(min_offer, min_offer)
    zero_mask = denominator==0
    denominator[zero_mask] = 1  #avoid division by zero
    tmp = numerator / denominator
    tmp[denominator==0] = 0
    return np.mean(tmp)
    # return np.mean(gain(min_offer, predicted) / gain(min_offer, min_offer))

def cross_compute(min_offer, predicted, metric):
    """
    :param min_offer: responder's minimal acceptable offer
    :param predicted: proposed values
    :metric: (func) computation metric
    """
    res = 0
    for idx in range(predicted.shape[0]):
        sub_predicted = np.ones_like(min_offer) * predicted[idx]
        res += metric(min_offer, sub_predicted)
    return res/predicted.shape[0]

def invariance(min_offer, predicted):
    return 1 / (1 + np.std(predicted)**.5)

__all__ = ['avg_loss', 'mse', 'rejection_ratio', 'avg_win_loss', 'avg_loss_ratio', 'loss_sum', 'MAX_GAIN', 'gain_mean', "cross_compute", "invariance"]