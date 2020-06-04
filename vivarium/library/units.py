
import pint

units = pint.UnitRegistry()
from pint.quantity import _Quantity as Quantity

def remove_units(dict_in):
    dict_out = {}
    for key, value in dict_in.items():
        if isinstance(value, dict):
            dict_out[key] = remove_units(value)
        else:
            if isinstance(value, Quantity):
                dict_out[key] = value.magnitude
            elif isinstance(value, list):
                dict_out[key] = [n.magnitude if isinstance(n, Quantity) else n for n in value]
            else:
                dict_out[key] = value
    return dict_out
