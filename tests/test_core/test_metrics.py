import unittest
import random

import pandas as pd
import numpy as np

from core.models.metrics import (loss, loss_sum, avg_loss, mse, rejection_ratio, avg_win_loss, gain, 
    gain_mean, avg_gain_ratio, cross_compute, MAX_GAIN)

def get_y_ypred(N=100, mode="random"):
    """
    :param mode: (random|full|null)
    """
    y = np.random.randint(5, MAX_GAIN-5, size=N)
    if mode == "full":
        ypred = y
    elif mode == "null":
        ypred = np.ones(shape=N)
    else:
        ypred = np.random.randint(0, MAX_GAIN, size=N)
    return y, ypred

class Test_metrics(unittest.TestCase):
    def test_loss(self):
        y, ypred = get_y_ypred(mode="full")
        np.testing.assert_almost_equal(loss(y, ypred), np.zeros(y.shape))
        y, ypred = get_y_ypred(mode="null")
        np.testing.assert_almost_equal(loss(y, ypred), (MAX_GAIN-y))
    
    def test_loss_sum(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(loss_sum(y, ypred), 0)

        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(loss_sum(y, ypred), (MAX_GAIN-y).sum())
    
    def test_avg_loss(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(avg_loss(y, ypred), 0)

        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(avg_loss(y, ypred), (MAX_GAIN-y).mean())
    
    def test_mse(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(mse(y, ypred), 0)
        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(mse(y, ypred), ((MAX_GAIN-y)**2).mean())
    
    def test_rejection_ratio(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(rejection_ratio(y, ypred), 0)

        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(rejection_ratio(y, ypred), 1)
    
    def test_avg_win_loss(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(avg_win_loss(y, ypred), 0)

        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(avg_win_loss(y, ypred), 0)
    
    def test_gain(self):
        y, ypred = get_y_ypred(mode="full")
        np.testing.assert_almost_equal(gain(y, ypred), (200-ypred))
        y, ypred = get_y_ypred(mode="null")
        np.testing.assert_almost_equal(gain(y, ypred), (0))
    
    def test_gain_mean(self):
        y, ypred = get_y_ypred(mode="full")
        np.testing.assert_almost_equal(gain_mean(y, ypred), (200-ypred).mean())
        y, ypred = get_y_ypred(mode="null")
        np.testing.assert_almost_equal(gain_mean(y, ypred), (0))
    
    def test_avg_gain_ratio(self):
        y, ypred = get_y_ypred(mode="full")
        self.assertAlmostEqual(rejection_ratio(y, ypred), 0)

        y, ypred = get_y_ypred(mode="null")
        self.assertAlmostEqual(rejection_ratio(y, ypred), 1)
    
    def test_cross_compute(self):
        self.skipTest("Not implemented")
