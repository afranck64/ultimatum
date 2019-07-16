import unittest

import pandas as pd
import numpy as np

from core.models.acceptance import AcceptanceModel
from core.models.cluster import ClusterModel, ClusterExtModel
from core.models.deep import KerasModel
from core.models.featureless import ConservativeModel, EMModel, RandomModel

def get_xy(N=100, M=8):
    X = np.random.random((N, M))
    y = np.random.randint(low=0, high=200, size=N)
    return X, y

class Test_acceptance(unittest.TestCase):
    def test_acceptance(self):
        model = AcceptanceModel()
        X, y = get_xy()
        model.fit(X, y)
        model.predict(X)

class Test_cluster(unittest.TestCase):
    def test_cluster(self):
        X, y = get_xy()
        model = ClusterModel()
        model.fit(X, y)
        model.predict(X)
    
    def test_cluster_ext(self):
        X, y = get_xy()
        model = ClusterExtModel()
        model.fit(X, y)
        model.predict(X)

class Test_deep(unittest.TestCase):
    def test_deep(self):
        X, y = get_xy()
        model = KerasModel(epochs=8)
        model.fit(X, y)
        model.predict(X)

class Test_featureless(unittest.TestCase):
    def test_em(self):
        X, y = get_xy()
        model = EMModel()
        model.fit(X, y)
        model.predict(X)
    
    def test_conservative(self):
        X, y = get_xy()
        model = ConservativeModel()
        model.fit(X, y)
        model.predict(X)
    
    def test_random(self):
        X, y = get_xy()
        model = RandomModel()
        model.fit(X, y)
        model.predict(X)