import numpy as np
from sklearn.svm import SVC, SVR, LinearSVR
from sklearn.linear_model import LogisticRegression

from .metrics import MAX_GAIN

def ultimatum_score(y_true, y_pred):
    res = MAX_GAIN - y_pred
    res[y_pred < y_true] = 0
    return res.mean()
    

class AcceptanceModel(object):
    def __init__(self, base_model=None, max_gain=MAX_GAIN, step=5, zero_one=True, metric=None):
        """
        Convert the multiclass regression/classification problem into a binary regression/classification problem
        by extending the features with possible target values and using as new target value a vector  target==all_new_possible_targets
        Once trained, an optimal decision line is searched using the given metric and predictions on a 
        validation set (taken from the training set prior to training)

        :param base_model: a model with fit/predict functions (classification)
        :param max_gain: (int) the maximum possible offer/gain
        :param step: (int) band width for categorizing the possible values inteval
        :zero_one: (bool) if True use the classes 0/1 else -1/1
        :param metric: (function|callable) with two parameters (y_true, y_pred) returns the score of a prediction
        """
        self.base_model = base_model
        if base_model is None:
            #self.base_model = LogisticRegression(penalty='l1', solver='liblinear')
            self.base_model = LinearSVR()
        self.max_gain = max_gain
        self.zero_one = zero_one
        if self.zero_one:
            self.classes = [0, 1]
        else:
            self.classes = [-1, 1]
        self.offers = np.arange(0, max_gain, step)
        self.decision_line = 0
        if metric is None:
            metric = ultimatum_score
        self.metric = metric
        self._trained = False
    
    def _transform_train(self, x, y):
        """
        :param x:
        :param y:
        :returns: x_, y_ with x is extended with a new feature, y_ is an array with two values
        """
        xNew = []
        yNew = []
        for idx in np.arange(0, x.shape[0]):
            base = np.zeros((self.offers.shape[0], x.shape[1] + 1))
            base[:, :-1] = x[idx]
            base[:, -1] = self.offers / self.max_gain
            xNew.extend(base)
            base_y = (base[:, -1] >= (y[idx] / self.max_gain)).astype(int) #TODO #NOTE check
            if self.zero_one:
                base_y[base_y < 1] = -1
            yNew.extend(base_y)
        xNew = np.array(xNew)
        yNew = np.array(yNew)
        return xNew, yNew
    
    def _transform_predict(self, x):
        xNew = []
        for idx in np.arange(0, x.shape[0]):
            base = np.zeros((self.offers.shape[0], x.shape[1] + 1))
            base[:, :-1] = x[idx]
            base[:, -1] = self.offers / self.max_gain
            xNew.extend(base)
        xNew = np.array(xNew)
        return xNew        
    
    def fit(self, xTrain, yTrain, **kwargs):
        xTrain_, yTrain_ = xTrain, yTrain
        split = int(xTrain.shape[0] * 0.75)
        xTrain_only, yTrain_only = xTrain[:split], yTrain[:split]
        xVal_only, yVal_only = xTrain[split:], yTrain[split:].ravel()
        
        xTrain_only, yTrain_only = self._transform_train(xTrain_only, yTrain_only)
        self.base_model.fit(xTrain_only, yTrain_only)

        # optimization for the decision_line
        top_decision_line = None
        top_score = float('-inf')
        xVal_only_ext = self._transform_predict(xVal_only)
        for decision_line in np.linspace(self.classes[0], self.classes[1]):
            yPred = self._predict(self.base_model, xVal_only, decision_line)
            score = self.metric(yVal_only, yPred)
            if score > top_score:
                top_score = score
                top_decision_line = decision_line
        self.decision_line = top_decision_line
            
        self._trained = True
    
    def _predict(self, model, xTest, decision_line, **kwargs):
        xShape = xTest.shape
        xTest = self._transform_predict(xTest)
        
        y_pred = model.predict(xTest)
        res = []
        for idx in np.arange(0, xShape[0]):
            mask = np.arange(idx*self.offers.shape[0], (idx+1)*self.offers.shape[0])
            group_y = y_pred[mask]
            group_x = xTest[mask]
            target = group_x[(group_y > decision_line).argmax()][-1]
            res.append(target * self.max_gain)
        return np.array(res)
        
    def predict(self, xTest, **kwargs):
        return self._predict(self.base_model, xTest, self.decision_line)