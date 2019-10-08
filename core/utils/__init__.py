import os
import sys
sys.path.append(os.path.realpath(os.path.join(os.path.split(__file__)[0], '..', '..')))

import numpy as np

def cents_repr(amout_in_cents, upper_case=True):
    if amout_in_cents < 100:
        res = f"{amout_in_cents} USD CENTS"
    else:
        res = f"{amout_in_cents/100} USD"
    if upper_case:
        return res.upper()
    else:
        return res


def randn_skew_fast(shape, alpha=0.0, loc=0.0, scale=1.0):
    # Taken from: https://stackoverflow.com/questions/36200913/generate-n-random-numbers-from-a-skew-normal-distribution-using-numpy
    if not isinstance(shape, (list, tuple)):
        shape = (shape,)
    sigma = alpha / np.sqrt(1.0 + alpha**2) 
    u0 = np.random.randn(*shape)
    v = np.random.randn(*shape)
    u1 = (sigma*u0 + np.sqrt(1.0 - sigma**2)*v) * scale
    u1[u0 < 0] *= -1
    u1 = u1 + loc
    return u1