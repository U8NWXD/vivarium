from __future__ import absolute_import, division, print_function

import os
import random

from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)


NAME = 'T_cell'


class T_cell(Process):
    """
    T-cell process with 2 states

    Required parameters:
        -

    Target behavior:
        - a population of (how many) PD1- cells transition to PD1+ in sigmoidal fashion in ~2 weeks

    TODOs
        - make this work!
    """

    defaults = {
        'initial_PD1-': 0.8
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        if random.uniform(0,1) < self.defaults['initial_PD1-']:
            self.initial_state = 'PD1-'
        else:
            self.initial_state = 'PD1+'

        self.cell_states = [
            'PD1+',
            'PD1-']

        parameters = {
            'transition_PD1-_to_PD1+': 0.01,  # probability/sec
        }

        ports = {
            'internal': ['cell_state'],
            'boundary': ['IFN-g']
        }
        super(T_cell, self).__init__(ports, parameters)

    def ports_schema(self):
        return {
            'internal': {
                'cell_state': {
                    '_value': self.initial_state,
                    '_updater': 'set'}}}

    def next_update(self, timestep, states):
        cell_state = states['internal']['cell_state']

        new_cell_state = cell_state
        if cell_state is 'PD1-':
            if random.uniform(0,1) < self.parameters['transition_PD1-_to_PD1+'] * timestep:
                new_cell_state = 'PD1+'

        if cell_state is 'PD1+':
            pass

        return {
            'internal': {
                'cell_state': new_cell_state}}



def run_t_cells():
    t_cell_process = T_cell({})
    settings = {'total_time': 10}
    timeseries = simulate_process_in_experiment(t_cell_process, settings)

    import ipdb;
    ipdb.set_trace()


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_t_cells()
