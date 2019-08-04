from copy import deepcopy
from sklearn.model_selection import KFold
import numpy as np
import pandas as pd

from .data_augmentation import DACombine
from core.models.metrics import avg_loss, mse, rejection_ratio, avg_win_loss, avg_loss_ratio, loss_sum, invariance


benchmark_functions = [avg_loss, mse, rejection_ratio, avg_win_loss, avg_loss_ratio, loss_sum, invariance]

def process_model(model, xTrain, yTrain, xTest, yTest, fit_kwargs=None, predict_kwargs=None, metrics=None):
    if metrics is None:
        metrics = benchmark_functions
    fit_kwargs = {} if fit_kwargs is None else fit_kwargs
    predict_kwargs = {} if predict_kwargs is None else predict_kwargs
    model.fit(xTrain, yTrain, **fit_kwargs)
    yPredict = model.predict(xTest, **predict_kwargs)
    results = {func.__name__: func(yTest, yPredict) for func in metrics}
    return results
    
def process_benchmark_cv(model, X, y, cv=5, fit_kwargs=None, predict_kwargs=None, augment_data=None, metrics=None):
    """
    :param model: model with fit/predict methods
    :param X: features
    :param y: target
    :param cv: (int) cross validation splits
    :param fit_kwargs: (dict) kwargs for fit
    :param predict_kwargs: (dict) kwargs for predict
    :param augment_data: (None|1|2) 1: random, 2: upsample    
    """
    # We make sure original values aren't modified, even by mistake
    X = np.copy(X)
    y = np.copy(y)
    
    kf = KFold(n_splits=cv)
    results = []
    for train_index, test_index in kf.split(X):
        xTrain, yTrain = X[train_index], y[train_index]
        if augment_data:
            upsample = augment_data==2
            xTrain, yTrain = DACombine().fit_predict(xTrain, yTrain, upsample=upsample)
        xTest, yTest = X[test_index], y[test_index]
        benchmark_result = process_model(deepcopy(model), xTrain, yTrain, xTest, yTest, fit_kwargs, predict_kwargs, metrics)
        results.append(benchmark_result)
    return pd.DataFrame(results)

def process_benchmarks(models_dict, X, y, cv=5, fit_kwargs=None, predict_kwargs=None, augment_data=None, shuffle=False, metrics=None):
    """
    Benchmark multiple models using the same augmented data to spare time from data augmentation
    :param models_dict: {key:model} dict of models with fit/predict methods
    :param X: features
    :param y: target
    :param cv: (int) cross validation splits
    :param fit_kwargs: (dict) kwargs for fit
    :param predict_kwargs: (dict) kwargs for predict
    :param augment_data: (None|1|2|list) None: no data-augmentation, 1: random, 2: upsample  
    :param shuffle: if True, shuffle data
    :returns: dict of dataframe results
    """
    X = np.copy(X)
    y = np.copy(y)
    if shuffle:
        mask = np.arange(0, X.shape[0])
        np.random.shuffle(mask)
        X = X[mask]
        y = y[mask]
    if not isinstance(augment_data, (list, tuple)):
        augment_data = [augment_data]
    benchmark_results = {key:[] for key in models_dict}
    kf = KFold(n_splits=cv)
    for train_index, test_index in kf.split(X):
        xTrain, yTrain = X[train_index], y[train_index]
        for augment_data_step in augment_data:
            if augment_data_step:
                upsample = augment_data_step==2
                xTrain, yTrain = DACombine().fit_predict(xTrain, yTrain, upsample=upsample)
            xTest, yTest = X[test_index], y[test_index]
            for key, model in models_dict.items():
                benchmark_result = process_model(deepcopy(model), xTrain, yTrain, xTest, yTest, fit_kwargs, predict_kwargs, metrics)
                nKey = key
                if augment_data_step:
                    nKey += "_da" + str(augment_data_step)
                nKey_results = benchmark_results.get(nKey, [])
                nKey_results.append(benchmark_result)
                benchmark_results[nKey] = nKey_results
    return {key: pd.DataFrame(results) for key, results in benchmark_results.items()}
        