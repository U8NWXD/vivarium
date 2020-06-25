from __future__ import absolute_import, division, print_function

import copy

from vivarium.library.dict_utils import deep_merge

DEFAULT_TIME_STEP = 1.0


class Process(object):

    defaults = {}

    def __init__(self, parameters=None):
        if parameters is None:
             parameters = {}
        self.parameters = copy.deepcopy(self.defaults)
        deep_merge(self.parameters, parameters)

    def ports(self):
        ports_schema = self.ports_schema()
        return {
            port: list(states.keys())
            for port, states in ports_schema.items()}

    def local_timestep(self):
        '''
        Returns the favored timestep for this process.
        Meant to be overridden in subclasses, unless 1.0 is a happy value.
        '''
        return self.parameters.get('time_step', DEFAULT_TIME_STEP)

    def default_state(self):
        '''
        ports_schema returns a dictionary that declares which states are expected by the processes,
        and how each state will behave.

        state keys can be assigned properties through schema_keys declared in Store:
            '_default'
            '_updater'
            '_divider'
            '_value'
            '_properties'
            '_emit'
            '_serializer'
        '''

        schema = self.ports_schema()
        state = {}
        for port, states in schema.items():
            for key, value in states.items():
                if '_default' in value:
                    if port not in state:
                        state[port] = {}
                    state[port][key] = value['_default']
        return state

    def is_deriver(self):
        return False

    def derivers(self):
        return {}

    def pull_data(self):
        return {}

    def ports_schema(self):
        return {}

    def or_default(self, parameters, key):
        return parameters.get(key, self.defaults[key])

    def derive_defaults(self, original_key, derived_key, f):
        source = self.parameters.get(original_key)
        self.parameters[derived_key] = f(source)
        return self.parameters[derived_key]

    def next_update(self, timestep, states):
        '''
        Find the next update given the current states this process cares about.
        This is the main function a new process would override.'''

        return {
            port: {}
            for port, values in self.ports.items()}


class Deriver(Process):
    def is_deriver(self):
        return True
