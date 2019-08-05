
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.base import BaseEstimator

from core.models.metrics import avg_gain_ratio
from core.utils.data_augmentation import DASampling


class OracleModel(object):
    def __init__(self, model=None, oracle_model=None):
        if model is None:
            model = RandomForestClassifier()
        if oracle_model is None:
            oracle_model = MLPClassifier((1000,))

        self.model = model
        self.oracle_model = oracle_model
        self.acc_ = None
        self.val_acc_ = None
        # print(f"model: {self.model}, oracle: {self.oracle_model}")
    
    def fit(self, xTrain, yTrain, model_fit_kwargs=None, oracle_fit_kwargs=None, oracle_split=0.5, size=None):
        """
        :param xTrain:
        :param yTrain:
        :param model_fit_kwargs:
        :param oracle_fit_kwargs:
        :param oracle_split:
        :param size:
        """
        if size is None:
            size = xTrain.shape[0] * 50
        xTrain_ = xTrain
        yTrain_ = yTrain
        xTrain, xVal, yTrain, yVal = train_test_split(xTrain, yTrain, test_size = 1/5)
        da = DASampling()
        split = int(oracle_split * xTrain.shape[0])
        xTrain_o_base, yTrain_o_base = xTrain[:split], yTrain[:split]
        xTrain_a_base, yTrain_a_base = xTrain[split:], yTrain[split:]
        xTrain_o, yTrain_o = da.fit_transform(xTrain_o_base, yTrain_o_base, pseudo_random_values=False)
        xTrain_o, yTrain_o = np.append(xTrain_o, xTrain_o_base, axis=0), np.append(yTrain_o, yTrain_o_base, axis=0)
        self.oracle_model.fit(xTrain_o, yTrain_o)

        xTrain_a, yTrain_a = da.fit_transform(xTrain_a_base, yTrain_a_base)
        yTrain_a = self.oracle_model.predict(xTrain_a).astype(int)

        if hasattr(self.model, "partial_fit"):
            try:
                self.model.partial_fit(xTrain_a[:2], yTrain_a[:2], classes=np.unique(np.append(yTrain_a, yTrain, axis=0)))
            except Exception as err:
                print(err)
            self.model.partial_fit(xTrain_a, yTrain_a)
            self.model.partial_fit(xTrain, yTrain)
        else:
            xTrain_a = np.append(xTrain_a, xTrain, axis=0)
            if len(yTrain_a.shape) < len(yTrain.shape):
                yTrain_a = yTrain_a.reshape(yTrain_a.shape + (1,))
            yTrain_a = np.append(yTrain_a, yTrain, axis=0)
            self.model.fit(xTrain_a, yTrain_a)
        yPred = self.model.predict(xTrain)
        self.acc_ = avg_gain_ratio(yTrain, yPred)
        yPred = self.model.predict(xVal)
        self.val_acc_ = avg_gain_ratio(yVal, yPred)
    
    def predict(self, xTest):
        return self.model.predict(xTest)
    
    def score(self, yTest, yPred):
        return avg_gain_ratio(yTest, yPred)
    
