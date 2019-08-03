import copy
import numpy as np
from sklearn.cluster import KMeans, MeanShift, DBSCAN, SpectralClustering, Birch, MiniBatchKMeans, AffinityPropagation
from sklearn.mixture import BayesianGaussianMixture

from .featureless import EMModel


class ClusterModel(object):
    MODELS = {
        "kmeans": KMeans,
        "meanshift": MeanShift,
        "birch": Birch,
        "spectral": SpectralClustering,
        "minibatch": MiniBatchKMeans,
        "affinity": AffinityPropagation,
        "bayes": BayesianGaussianMixture,
    }

    def __init__(self, **kwargs):
        """
        Groups the features in clusters. Target values of these clusters are computed as mean+std of the cluster's target values

        :param base_model: (str|Model) name of a clustering algorithm to use or model object. see MODELS for possible value
        """
        if "base_model" in kwargs:
            base_model_ = kwargs.pop("base_model")
            if isinstance(base_model_, str):
                self.base_model = self.MODELS.get(base_model_, MeanShift)(**kwargs)
            else:
                self.base_model = base_model_
        else:
            self.base_model = MeanShift(**kwargs)
        super().__init__()
        self.clustersClasses = None
        self._trained = False
    
    def fit(self, xTrain, yTrain, **kwargs):
        self.base_model.fit(xTrain)
        labels = np.array([item for item in np.unique(self.base_model.labels_) if item >= 0])
        clustersClasses = np.zeros_like(labels)
        for cluster in range(len(labels)):
            values = yTrain[self.base_model.labels_==cluster]
            clustersClasses[cluster] = values.mean() + values.std()
        self.clustersClasses = clustersClasses
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if self._trained is None:
            raise ValueError("Model not trained yet")
        predClusters = self.base_model.predict(xTest)
        return self.clustersClasses[predClusters]

class ClusterExtModel(object):
    MODELS = {
        "kmeans": KMeans,
        "meanshift": MeanShift,
        "birch": Birch,
        "spectral": SpectralClustering,
        "minibatch": MiniBatchKMeans,
        "affinity": AffinityPropagation,
        "bayes": BayesianGaussianMixture,
    }

    def __init__(self, **kwargs):
        """
        Groups the features in clusters.
        Target values of these clusters are computed using the passed sub_model

        :param base_model: (str|Model) name of a clustering algorithm to use or model object. see MODELS for possible value
        :param sub_model: (Model) model to use for inter cluster prediction.
        """
        if "sub_model" in kwargs:
            self.sub_model = kwargs.pop("sub_model")
        else:
            self.sub_model = EMModel()
        if "base_model" in kwargs:
            base_model_ = kwargs.pop("base_model")
            if isinstance(base_model_, str):
                self.base_model = self.MODELS.get(base_model_, MeanShift)(**kwargs)
            else:
                self.base_model = base_model_
        else:
            self.base_model = MeanShift(**kwargs)
        self._trained = False
        self.sub_models = None
        
    def fit(self, xTrain, yTrain, **kwargs):        
        self.base_model.fit(xTrain, yTrain, **kwargs)
        labels = np.array([item for item in np.unique(self.base_model.labels_) if item >= 0])
        clustersClasses = np.zeros_like(labels)
        sub_models = []
        for cluster in range(len(labels)):
            sub_model = copy.deepcopy(self.sub_model)
            mask = self.base_model.labels_==cluster
            sub_model.fit(xTrain[mask], yTrain[mask])
            sub_models.append(sub_model)
        # We use an array instead of a list for better indexing
        #self.clustersClasses = [sub_model.value for sub_model in sub_models]
        self.sub_models = sub_models
        self._trained = True
    
    def predict(self, xTest, **kwargs):
        if self._trained is None:
            raise ValueError("Model not trained yet")
        predClusters = self.base_model.predict(xTest)
        preds = []
        dummy_x = np.array([0])
        for idx in range(xTest.shape[0]):
            pred = self.sub_models[predClusters[idx]].predict(np.array([xTest[idx]]))
            preds.append(pred)
        res = np.array(preds).ravel()
        return res
        #return self.clustersClasses[predClusters]
            