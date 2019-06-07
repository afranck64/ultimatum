import os
import sys
sys.path.append(os.path.realpath(os.path.join(os.path.split(__file__)[0], '..', '..')))

def value_repr(amout_in_cents, upper_case=True):
    if amout_in_cents < 100:
        res = f"{amout_in_cents} cents"
    else:
        res = f"{amout_in_cents/100} usd"
    if upper_case:
        return res.upper()
    else:
        return res
