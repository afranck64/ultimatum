from copy import deepcopy
import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.tree import DecisionTreeClassifier
from scipy.stats import mode


from .metrics import avg_loss_ratio, MAX_GAIN
from ..utils import randn_skew_fast


class SplitModel(object):
    class SubSplitModel(object):
        def __init__(self, base_model, idx):
            self.base_model = deepcopy(base_model)
            self.X_selector = [idx]

        def fit(self, X, y):
            sub_X = X[:, self.X_selector]
            self.base_model.fit(sub_X, y)

        def predict(self, X):
            sub_X = X[:, self.X_selector]
            return self.base_model.predict(sub_X)

    def __init__(self, max_value=MAX_GAIN, base_model=None):
        if base_model is None:
            base_model = DecisionTreeClassifier()
        self.base_model = base_model
        self.max_value = max_value
        self._trained = False
        self.mean = 0
        self.std = 0
        self.skew = 0
        self.main_model = None
        self.estimators = []

    def fit(self, xTrain, yTrain, **kwargs):
        # self.estimators = [(f"clf_{idx}", SplitModel.SubSplitModel(self.base_model, idx)) for idx in range(xTrain.shape[1])]
        self.estimators = [SplitModel.SubSplitModel(deepcopy(self.base_model), idx) for idx in range(xTrain.shape[1])]
        for clf in self.estimators:
            clf.fit(xTrain, yTrain)
        # self.main_model  = VotingClassifier(estimators)
        # self.main_model.fit(xTrain, yTrain)
    
    def predict(self, xTest, **kwargs):
        preds = [clf.predict(xTest) for clf in self.estimators]
        return mode(preds)[0].ravel()
        # return max(set(preds), key=preds.count)