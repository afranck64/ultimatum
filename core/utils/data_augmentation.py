import numpy as np
import pandas as pd
from . import *

from core.models.metrics import MAX_GAIN
from core.utils import randn_skew_fast
import sys

class DACombine(object):
    def __init__(self, size=None, max_gain=MAX_GAIN):
        self.size = size
        self.max_gain = max_gain
    
    def fit_predict(self, xTrain, yTrain, size=None, distance=10, upsample=True, include_xy=False, retarget=False, distribution=False, combine=False):
        """
        :param size: (int) size of the new generated dataset
        :param distance: (int) distance between parents or similar items
        :param upsample: (bool) if True, try balance the dataset
        :param include_xy: (bool) if True, include xTrain and yTrain to the data (on top of size items)
        :param retarget: (bool) if True, set all targets to the nearest higher multiple of distance without generating new samples
        :param distribution: (bool) if True, create new sample based on percentiles of features's std
        :param combine: (bool) if True: combine different methods (dist + retarget)
        """
        
        size = size or self.size or len(xTrain) * 4
        if combine:
            if distribution:
                xTrain, yTrain = self.dist_resample(xTrain, yTrain, size)
        else:
            if retarget:
                return self.retarget(xTrain, yTrain, distance)

            if distribution:
                return self.dist_resample(xTrain, yTrain, size)
    
        nb_features = xTrain.shape[1]
        indices = np.arange(nb_features)
        np.random.shuffle(indices)
        targets = yTrain.ravel()
        if upsample:
            targets, counts = np.unique(yTrain, return_counts=True)
            #NOTE: minimize selection of target with only one sample
            probs = (1 - counts/counts.sum())**2
            probs[counts==1] = probs.min()
            probs /= probs.sum()
        else:
            targets = yTrain.ravel()
            probs = None
        xRes = []
        yRes = []
        if include_xy:
            xRes.extend(xTrain)
            yRes.extend(yTrain.ravel())
        for _ in range(size):
            target = np.random.choice(targets, p=probs)
            target_mask = (yTrain.ravel()<target+distance) & (yTrain.ravel()>=(target))
            xTrain_target = xTrain[target_mask]
            i = np.random.randint(xTrain_target.shape[0])
            j = np.random.randint(xTrain_target.shape[0])
            x = np.zeros_like(xTrain_target[0])
            np.random.shuffle(indices)
            split = np.random.randint(nb_features)
            mask_i = indices[:split]
            mask_j = indices[split:]
            x[mask_i] = xTrain_target[i, mask_i]
            x[mask_j] = xTrain_target[j, mask_j]
            xRes.append(x)
            yRes.append(target)
        xRes = np.array(xRes)
        yRes = np.array(yRes)
        if combine and retarget:
            return self.retarget(xRes, yRes, distance)
        return np.array(xRes), np.array(yRes)

    def retarget(self, xTrain, yTrain, distance=10):
        yNew = yTrain.ravel().copy()
        for y in np.arange(self.max_gain, 0, -distance):
            mask = (yNew <= y) & (yNew > y-distance)
            yNew[mask] = y + distance    # np.random.randint(0, distance, mask.shape)[mask]
        yNew = np.array(yNew)
        yNew[yNew > self.max_gain] = self.max_gain
        return xTrain, yNew
    
    def dist_resample(self, xTrain, yTrain, size=None, std_ratio=0.1):
        size = size or self.size or len(xTrain) * 4
        xTrain_std = xTrain.std()
        xNew = []
        yNew = []
        for _ in range(size):
            idx = np.random.randint(0, xTrain.shape[0])
            x = np.random.normal(xTrain[idx], xTrain_std*std_ratio)
            y = yTrain[idx]
            xNew.append(x)
            yNew.append(y)
        return np.array(xNew), np.array(yNew)
            

    def fit_resample(self, xTrain, yTrain, size=None, distance=5, include_xy=True):
        return self.fit_predict(xTrain, yTrain, size=size, distance=distance, include_xy=include_xy)


class DASampling(object):
    def __init__(self, size=None):
        """
        Generate new data by randomly combining attributes of different features.
        """
        self.size = size
    
    def fit_transform(self, *args, **kwargs):
        return self.generate_data(*args, **kwargs)

    def generate_data(self, xTrain, yTrain, size=None, pseudo_random_values=True, skewed=True):
        size = size or self.size or len(xTrain) * 4
        size += size % 2
        xMean = xTrain.mean(axis=0)
        xStd = xTrain.std(axis=0)
        yMean = yTrain.mean()
        yStd = yTrain.std()
        xValues = np.empty((size, xTrain.shape[1]))
        yValues = np.empty((size, ) + yTrain.shape[1:])
        if pseudo_random_values:
            loopsize = size//2
        else:
            loopsize = size
        
        for idx in range(loopsize):
            selected_rows = np.random.randint(0, xTrain.shape[0], xTrain.shape[1])
            x_row = []
            for colid, rowid in enumerate(selected_rows):
                x_row.append(xTrain[rowid][colid])
            y_row = [yTrain[np.random.choice(selected_rows)]]
            xValues[idx, :] = x_row
            yValues[idx, :] = y_row
        if pseudo_random_values:
            if skewed:
                xSkew = pd.DataFrame(data=xTrain).skew()[0]
                ySkew = pd.DataFrame(data=yTrain).skew()[0]
                xVals = randn_skew_fast((loopsize, xTrain.shape[1]), xSkew, xMean, xStd)
                yVals = randn_skew_fast((loopsize, yTrain.shape[1]), ySkew, yMean, yStd)
            else:
                xVals = np.random.normal(xMean, xStd, (loopsize, xTrain.shape[1]))
                yVals = np.random.normal(yMean, yStd, (loopsize, 1))
            yVals += 5 - yVals % 5
            xValues[loopsize:2*loopsize+1, :] = xVals
            yValues[loopsize:2*loopsize+1, :] = np.clip(yVals, 0, MAX_GAIN)
        return xValues, yValues.astype(int)

    
    

