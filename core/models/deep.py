#keras
import numpy as np
import math
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.layers import multiply
from keras.wrappers.scikit_learn import KerasRegressor
import keras.backend as K
from keras import regularizers
from keras import optimizers
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import tensorflow as tf
import sys

from .metrics import MAX_GAIN

def sigmoid1024_tf(x):
    return (1024.0**x) / (1024.0**x + 1)

def sigmoid_tf(x):
    return K.sigmoid(x)

def gain_tf(y_true, y_pred):
    zero = K.zeros_like(y_true)
    diff = tf.math.subtract(y_pred, y_true)
    diff_gain = tf.math.subtract(K.constant(MAX_GAIN*1.0), y_pred)
    mask_neg = K.less(diff, zero)
    diff_pos = tf.where(mask_neg, zero, diff_gain)
    return K.mean(diff_pos)
    

# def gain_tf(y_true, y_pred):
#     zero = tf.constant(0.0)
#     x0 = tf.math.subtract(y_true, y_pred)
#     mask_neg = K.less(x0, zero)

#     math_pi = tf.constant(math.pi)
#     one = tf.constant(1.0)
#     divider = tf.constant(40.0)
#     x = tf.math.subtract(y_true, y_pred)
#     x = tf.math.truediv(x, divider)
#     left_mul = sigmoid_tf(x)
#     right_mul = tf.math.cos(tf.math.divide(x, math_pi))
#     return tf.math.multiply(left_mul, right_mul)

def loss_tf(y_true, y_pred):
    math_pi = tf.constant(math.pi, dtype=K.floatx())
    one = tf.constant(1.0, dtype=K.floatx())
    # divider = tf.constant(40.0)
    # #x0 = tf.math.subtract(y_true, y_pred)
    # x0 = tf.math.subtract(y_pred, y_true)
    # x = tf.math.truediv(x0, divider)
    # left_mul = sigmoid1024_tf(x)
    # right_mul = tf.math.cos(tf.math.divide(x, math_pi))
    # return tf.math.subtract(one, tf.math.multiply(left_mul, right_mul))
    #return (1 - gain_tf(y_true, y_pred)) * 100

    normalizer = MAX_GAIN / 100.0

    x0 = tf.math.subtract(y_pred, y_true)
    offset = tf.constant(1.0, dtype=K.floatx())
    x1 = (x0 + offset) / K.constant(normalizer * 8.0, dtype=K.floatx())
    x2 = (x0) / K.constant(normalizer * 20.0, dtype=K.floatx())
    left_mul = sigmoid1024_tf(x1)
    right_mul = tf.math.cos(tf.math.divide(x2, math_pi))
    return tf.math.subtract(one, tf.math.multiply(left_mul, right_mul))

def _keras_model(nb_features, loss=None, metrics=None, nb_outputs=1, lr=0.1):
    """
    build a simple regression model
    :param loss: (str|callable, default: loss_tf)
    """
    if loss is None:
        loss = loss_tf
    if metrics is None:
        metrics = [gain_tf]
    model = Sequential()
    model.add(Dense(200, input_dim=nb_features, kernel_initializer='normal', activation='relu'))

    # The Hidden Layers :
    model.add(Dense(275, kernel_initializer='normal',activation="relu"))
    model.add(Dense(100, kernel_initializer='normal',activation="relu",
                kernel_regularizer=regularizers.l2(0.01),
                    activity_regularizer=regularizers.l1(0.01)
                    )
                )
    if nb_outputs <= 1:
        model.add(Dense(1, activation='linear', kernel_initializer='normal'))
    else:
        model.add(Dense(nb_outputs, activation='linear'))
    model.compile(loss=loss, optimizer=optimizers.RMSprop(lr=lr), metrics=metrics)
    return model

def _keras_hiddenless_model(nb_features, loss=None, metrics=None, nb_outputs=1, lr=0.1):
    if loss is None:
        loss = loss_tf
    if metrics is None:
        metrics = [gain_tf] 
    model = Sequential()
    model.add(Dense(1, input_dim=nb_features, kernel_initializer='normal', activation='relu'))
    if nb_outputs <= 1:
        model.add(Dense(1, activation='linear', kernel_initializer='normal'))
    else:
        model.add(Dense(nb_outputs, activation='linear'))
    model.compile(loss=loss, optimizer=optimizers.RMSprop(lr=lr), metrics=metrics)
    return model

def keras_hiddenless_model(nb_features, loss=None, metrics=None, epochs=100, batch_size=32, verbose=False, nb_outputs=1):
    build_fn = lambda : _keras_hiddenless_model(nb_features, loss, metrics, nb_outputs)
    return KerasRegressor(build_fn=build_fn, epochs=epochs, batch_size=batch_size, verbose=verbose)
    
def keras_model(nb_features, loss=None, metrics=None, epochs=100, batch_size=32, verbose=False, nb_outputs=1):
    build_fn = lambda : _keras_model(nb_features, loss, metrics, nb_outputs)
    return KerasRegressor(build_fn=build_fn, epochs=epochs, batch_size=batch_size, verbose=verbose)


class KerasModel(object):
    def __init__(self, loss=None, metrics=None, as_regression=True, epochs=500, batch_size=32, verbose=0, no_hidden_layer=False):
        self.nb_features = None
        self.loss = loss
        self.metrics = metrics
        self._trained = False
        self.model = None
        self.as_regression = as_regression
        self.epochs = epochs
        self.batch_size = batch_size
        self.verbose = verbose
        self.no_hidden_layer = no_hidden_layer

    def fit(self, xTrain, yTrain, **kwargs):
        nb_outputs = 1
        #yTrain = yTrain.ravel()
        xTrain = xTrain.astype(K.floatx())
        yTrain = yTrain.astype(K.floatx())
        model_builder = keras_model
        if self.no_hidden_layer:
            model_builder = keras_hiddenless_model
        if not self.as_regression:
            nb_outputs = np.unique(yTrain).shape[0]
        self.model = model_builder(nb_features=xTrain.shape[1], loss=self.loss, metrics=self.metrics, epochs=self.epochs,
                                 batch_size=self.batch_size, nb_outputs=nb_outputs, verbose=self.verbose)
        return self.model.fit(xTrain, yTrain, **kwargs)
    
    def predict(self, xTest, **kwargs):
        yPred = self.model.predict(xTest, **kwargs)
        #convert predictions into 5x values and clip in the right interval+
        mask = (yPred % 5) != 0
        yPred[mask] = yPred[mask] + 5 - yPred[mask] % 5
        yPred = np.clip(yPred, 0, MAX_GAIN)
        return yPred

    
    def __getattr__(self, name):
        try:
            return getattr(self.model, name)
        except:
            raise AttributeError(name)