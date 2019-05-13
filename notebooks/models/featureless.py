import numpy as np
from .metrics import avg_loss_ratio, MAX_GAIN

class FeaturelessModel(object):
    def __init__(self, max_value=MAX_GAIN, loss=None):
        self.value = None
        self.max_value = max_value
        self.loss = loss or avg_loss_ratio
        self._trained = False
    
    def fit(self, xTrain, yTrain, **kwargs):
        min_loss = float('inf')
        best_value = 0
        for value in np.arange(self.max_value):
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
        self.value = max_value
        self._trained = False

    def fit(self, xTrain, yTrain, **kwargs):
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if not self._trained:
            raise ValueError("The model should first be trained")
        return np.random.random((xTest.shape[0], 1)) * self.value


class ConservativeModel(object):
    def __init__(self, max_value=MAX_GAIN):
        self.value = None
        self.max_value = max_value
        self._trained = False

    def fit(self, xTrain, yTrain, **kwargs):
        self.value = self.max_value - 1
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if not self._trained:
            raise ValueError("The model should first be trained")
        return np.ones((xTest.shape[0], 1)) * self.value