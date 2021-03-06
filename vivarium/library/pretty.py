import inspect
import json
import numpy as np
import re

from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.process import Process


def _json_serialize(elem):
    if isinstance(elem, np.int64):
        return int(elem)
    if inspect.isfunction(elem):
        return '<function {}>'.format(elem.__name__)
    if inspect.isclass(elem):
        return str(elem)
    if isinstance(elem, (Compartment, Process)):
        to_strip_regex = ' at 0x[0-9a-f]+>$'
        return re.sub(to_strip_regex, '>', repr(elem))
    if type(elem) == type(1 * units.fg):
        return str(elem)
    if type(elem) == type(units.fg):
        return repr(elem)
    return repr(elem)

def format_dict(d, sort_keys=True):
    '''Format a dict as a pretty string

    Aside from the normal JSON-serializable data types, data of type
    ``numpy.int64`` are supported.

    For example:

    >>> import numpy as np
    >>> d = {
    ...     'foo': {
    ...         'bar': 1,
    ...         '3.0': np.int64(5),
    ...     },
    ...     'a': 'hi!',
    ... }
    >>> print(format_dict(d))
    {
        "a": "hi!",
        "foo": {
            "3.0": 5,
            "bar": 1
        }
    }

    Arguments:
        d: The dictionary to format
        sort_keys: Whether to sort the dictionary keys. This is useful
            for reproducible output.

    Returns:
        A string of the prettily-formatted dictionary

    '''
    return json.dumps(
        d, indent=4, default=_json_serialize, sort_keys=sort_keys)
