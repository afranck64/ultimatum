import numpy as np
import pandas as pd

from .metrics import avg_loss_ratio, MAX_GAIN
from ..utils import randn_skew_fast

class EMModel(object):
    def __init__(self, max_value=MAX_GAIN, loss=None, step=5):
        self.value = None
        self.max_value = max_value
        self.loss = loss or avg_loss_ratio
        self._trained = False
        self.step = step
    
    def fit(self, xTrain, yTrain, **kwargs):
        min_loss = float('inf')
        best_value = 0
        for value in np.arange(0, self.max_value+self.step, self.step):
            fixedPredict = np.ones_like(yTrain) * value
            loss = self.loss(yTrain, fixedPredict)
            if loss < min_loss:
                min_loss = loss
                best_value = value
        self._trained = True
        self.value = best_value
    
    def predict(self, xTrain, **kwargs):
        if not self._trained:
            raise ValueError("The model first need to be trained!!!")
        res = np.ones((xTrain.shape[0], 1) ) * self.value
        return res

class RandomModel(object):
    def __init__(self, max_value=MAX_GAIN):
        self.max_value = max_value
        self._trained = False
        self.mean = 0
        self.std = 0
        self.skew = 0

    def fit(self, xTrain, yTrain, **kwargs):
        self.mean = np.mean(yTrain)
        self.std = np.std(yTrain)
        self.skew = pd.DataFrame(data=yTrain).skew()[0]
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if not self._trained:
            raise ValueError("The model should first be trained")
        res = randn_skew_fast(xTest.shape[0], self.skew, self.mean, self.std)
        return np.clip(0, res, self.max_value)


class ConservativeModel(object):
    def __init__(self, max_value=MAX_GAIN, step=5):
        self.value = MAX_GAIN - step
        self.max_value = max_value
        self._trained = False

    def fit(self, xTrain, yTrain, **kwargs):
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if not self._trained:
            raise ValueError("The model should first be trained")
        return np.ones((xTest.shape[0], 1)) * self.value