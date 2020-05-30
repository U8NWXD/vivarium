from __future__ import absolute_import, division, print_function

import copy

from vivarium.utils.dict_utils import deep_merge
from vivarium.core.process import Process
from vivarium.core.tree import Compartment


class Timeline(Process):

    def __init__(self, initial_parameters={}):
        self.timeline = copy.deepcopy(initial_parameters['timeline'])

        # get ports
        ports = {'global': ['time']}
        for event in self.timeline:
            for state in list(event[1].keys()):
                port = {state[0]: [state[1]]}
                ports = deep_merge(ports, port)
        parameters = {
            'timeline': self.timeline}

        super(Timeline, self).__init__(ports, parameters)

    def ports_schema(self):
        return {
            'global': {
                'time': {
                    '_default': 0,
                    '_updater': 'accumulate'}}}

    def next_update(self, timestep, states):
        time = states['global']['time']
        update = {'global': {'time': timestep}}
        for (t, change_dict) in self.timeline:
            if time >= t:
                for state, value in change_dict.items():
                    port = state[0]
                    variable = state[1]
                    if port not in update:
                        update[port] = {}
                    update[port][variable] = {
                        '_value': value,
                        '_updater': 'set'}
                self.timeline.pop(0)
        return update


class TimelineCompartment(Compartment):

    def __init__(self, config):
        self.timeline = config['timeline']
        self.processes = config['processes']
        self.topology = config['topology']
        self.path = config['path']

    def generate_processes(self, config):
        processes = {
            'timeline': Timeline({'timeline': self.timeline})}
        processes.update(self.processes)
        return processes

    def generate_topology(self, config):
        topology = {'timeline': self.path}
        topology['timeline'].update({'global': ('global',)})
        topology.update(self.topology)
        return topology
