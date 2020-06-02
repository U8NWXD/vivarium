from __future__ import absolute_import, division, print_function

import copy
import random

from vivarium.utils.units import Quantity


## divider functions
# these functions take in a value, are return two values for each daughter
def default_divide_condition(compartment):
    return False

def divide_set(state):
    return [state, state]

def divide_split(state):
    if isinstance(state, int):
        remainder = state % 2
        half = int(state / 2)
        if random.choice([True, False]):
            return [half + remainder, half]
        else:
            return [half, half + remainder]
    elif state == float('inf') or state == 'Infinity':
        # some concentrations are considered infinite in the environment
        # an alternative option is to not divide the local environment state
        return [state, state]
    elif isinstance(state, (float, Quantity)):
        half = state/2
        return [half, half]
    else:
        raise Exception('can not divide state {} of type {}'.format(state, type(state)))

def divide_zero(state):
    return [0, 0]

def divide_split_dict(state):
    d1 = dict(list(state.items())[len(state) // 2:])
    d2 = dict(list(state.items())[:len(state) // 2])
    return [d1, d2]

divider_library = {
    'set': divide_set,
    'split': divide_split,
    'split_dict': divide_split_dict,
    'zero': divide_zero}
