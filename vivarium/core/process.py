from __future__ import absolute_import, division, print_function

import copy
import random


from vivarium.utils.dict_utils import deep_merge
from vivarium.utils.units import Quantity

# deriver processes
from vivarium.processes.derive_concentrations import DeriveConcentrations
from vivarium.processes.derive_counts import DeriveCounts
from vivarium.processes.derive_globals import DeriveGlobals
from vivarium.processes.tree_mass import TreeMass


## updater functions
# these function take in a variable key, the entire store's dict,
# the variable's current value, the variable's current update,
# and returns a new value, and other updates

def update_merge(current_value, new_value):
    # merge dicts, with new_value replacing any shared keys with current_value
    update = current_value.copy()
    for k, v in current_value.items():
        new = new_value.get(k)
        if isinstance(new, dict):
            update[k] = deep_merge(dict(v), new)
        else:
            update[k] = new
    return update

def update_set(current_value, new_value):
    return new_value

def update_accumulate(current_value, new_value):
    return current_value + new_value

updater_library = {
    'accumulate': update_accumulate,
    'set': update_set,
    'merge': update_merge}

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


# Derivers
deriver_library = {
    'mmol_to_counts': DeriveCounts,
    'counts_to_mmol': DeriveConcentrations,
    'mass': TreeMass,
    'globals': DeriveGlobals,
}
