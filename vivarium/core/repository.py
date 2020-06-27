"""
==============================================
Repository of Updaters, Dividers, and Derivers
==============================================

You should interpret words and phrases that appear fully capitalized in
this document as described in :rfc:`2119`. Here is a brief summary of
the RFC:

* "MUST" indicates absolute requirements. Vivarium may not work
  correctly if you don't follow these.
* "SHOULD" indicates strong suggestions. You might have a valid reason
  for deviating from them, but be careful that you understand the
  ramifications.
* "MAY" indicates truly optional features that you can include or
  exclude as you wish.

--------
Updaters
--------

Each :term:`updater` is defined as a function whose name begins with
``update_``. Vivarium uses these functions to apply :term:`updates` to
:term:`variables`. Updater names are defined in
:py:data:`updater_library`, which maps these names to updater functions.

Updater API
===========

An updater function MUST have a name that begins with ``update_``. The
function MUST accept exactly two positional arguments: the first MUST be
the current value of the variable (i.e. before applying the update), and
the second MUST be the value associated with the variable in the update.
The function SHOULD not accept any other parameters. The function MUST
return the updated value of the variable only.

--------
Dividers
--------

Each :term:`divider` is defined by a function that follows the API we
describe below. Vivarium uses these dividers to generate daughter cell
states from the mother cell's state. Divider names are defined in
:py:data:`divider_library`, which maps these names to divider functions.

Divider API
===========

Each divider function MUST have a name prefixed with ``_divide``. The
function MUST accept a single positional argument, the value of the
variable in the mother cell. It SHOULD accept no other arguments. The
function MUST return a :py:class:`list` with two elements: the values of
the variables in each of the daughter cells.

.. note:: Dividers MAY not be deterministic and MAY not be symmetric.
    For example, a divider splitting an odd, integer-valued value may
    randomly decide which daughter cell receives the remainder.

--------
Derivers
--------

Each :term:`deriver` is defined as a separate :term:`process`, but here
deriver names are mapped to processes by :py:data:`deriver_library`. The
available derivers are:

* **mmol_to_counts**: :py:class:`vivarium.processes.derive_counts.DeriveCounts`
* **counts_to_mmol**:
  :py:class:`vivarium.processes.derive_concentrations.DeriveConcentrations`
* **mass**: :py:class:`vivarium.processes.tree_mass.TreeMass`
* **globals**:
  :py:class:`vivarium.processes.derive_globals.DeriveGlobals`

See the documentation for each :term:`process class` for more details on
that deriver.
"""


from __future__ import absolute_import, division, print_function

import copy
import random

import numpy as np

from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import Quantity

# deriver processes
from vivarium.processes.derive_concentrations import DeriveConcentrations
from vivarium.processes.derive_counts import DeriveCounts
from vivarium.processes.derive_globals import DeriveGlobals
from vivarium.processes.tree_mass import TreeMass


## updater functions

def update_merge(current_value, new_value):
    """Merge Updater

    Arguments:
        current_value (dict):
        new_value (dict):

    Returns:
        dict: The merger of ``current_value`` and ``new_value``. For any
        shared keys, the value in ``new_value`` is used.
    """
    update = current_value.copy()
    for k, v in current_value.items():
        new = new_value.get(k)
        if isinstance(new, dict):
            update[k] = deep_merge(dict(v), new)
        else:
            update[k] = new
    return update

def update_set(current_value, new_value):
    """Set Updater

    Returns:
        The value provided in ``new_value``.
    """
    return new_value

def update_accumulate(current_value, new_value):
    """Accumulate Updater

    Returns:
        The sum of ``current_value`` and ``new_value``.
    """
    return current_value + new_value

#: Maps updater names to updater functions
updater_library = {
    'accumulate': update_accumulate,
    'set': update_set,
    'merge': update_merge}

## divider functions
def divide_set(state):
    """Set Divider

    Returns:
        A list ``[state, state]``. No copying is performed.
    """
    return [state, state]

def divide_split(state):
    """Split Divider

    Arguments:
        state: Must be an :py:class:`int`, a :py:class:`float`, or a
            :py:class:`str` of value ``Infinity``.

    Returns:
        A list, each of whose elements contains half of ``state``. If
        ``state`` is an :py:class:`int`, the remainder is placed at
        random in one of the two elements. If ``state`` is infinite, the
        return value is ``[state, state]`` (no copying is done).

    Raises:
        Exception: if ``state`` is of an unrecognized type.
    """
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
    """Zero Divider

    Returns:
        ``[0, 0]`` regardless of input
    """
    return [0, 0]

def divide_split_dict(state):
    """Split-Dictionary Divider

    Returns:
        A list of two dictionaries. The first dictionary stores the
        first half of the key-value pairs in ``state``, and the second
        dictionary stores the rest of the key-value pairs.

        .. note:: Since dictionaries are unordered, you should avoid
            making any assumptions about which keys will be sent to
            which daughter cell.
    """
    if state is None:
        state = {}
    d1 = dict(list(state.items())[len(state) // 2:])
    d2 = dict(list(state.items())[:len(state) // 2])
    return [d1, d2]

#: Maps divider names to divider functions
divider_library = {
    'set': divide_set,
    'split': divide_split,
    'split_dict': divide_split_dict,
    'zero': divide_zero}

def default_divide_condition(compartment):
    return False

# Derivers

#: Maps deriver names to :term:`process classes`
deriver_library = {
    'mmol_to_counts': DeriveCounts,
    'counts_to_mmol': DeriveConcentrations,
    'mass': TreeMass,
    'globals': DeriveGlobals,
}


# Serializers
class Serializer(object):
    def serialize(self, data):
        return data

    def deserialize(self, data):
        return data

class NumpySerializer(Serializer):
    def serialize(self, data):
        return data.tolist()

    def deserialize(self, data):
        return np.array(data)

serializer_library = {
    'numpy': NumpySerializer(),
}
