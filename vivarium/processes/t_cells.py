from __future__ import absolute_import, division, print_function

import os
import random

from vivarium.library.units import units
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

    States:
        - PD1p (PD1+)
        - PD1n (PD1-)

    Required parameters:
        -

    Target behavior:
        - a population of (how many) PD1n cells transition to PD1p in sigmoidal fashion in ~2 weeks

    TODOs
        - make this work!
    """

    defaults = {
        'diameter': 10 * units.um,
        'initial_PD1n': 0.8,
        'transition_PD1n_to_PD1p': 0.01,  # probability/sec
        # death rates
        'death_PD1p': 7e-3,  # 0.7 / 14 hrs (Petrovas 2007)
        'death_PD1n': 2e-3,  # 0.2 / 14 hrs (Petrovas 2007)
        'death_PD1p_next_to_PDL1p': 9.5e-3,  # 0.95 / 14 hrs (Petrovas 2007)
        # IFNg_production
        'PD1n_IFNg_production': 1.6e4/3600,  # (molecules/cell/second) (Bouchnita 2017)
        'PD1p_IFNg_production': 0.0,  # (molecules/cell/second)
        # division rate (Petrovas 2007)
        'PD1n_growth': 0.9,  # probability of division in 8 hours
        'PD1p_growth': 0.05,  # probability of division in 8 hours
        # migration
        'PD1n_migration': 10.0,  # um/minute (Boissonnas 2007)
        'PD1n_migration_MHC1p_tumor': 2.0,  # um/minute (Boissonnas 2007)
        'PD1n_migration_MHC1p_tumor_dwell_time': 25.0,  # minutes (Thibaut 2020)
        'PD1p_migration': 5.0,   # um/minute (Boissonnas 2007)
        'PD1p_migration_MHC1p_tumor': 1.0,   # um/minute (Boissonnas 2007)
        'PD1p_migration_MHC1p_tumor_dwell_time': 10.0,  # minutes (Thibaut 2020)
        # killing  # TODO -- pass these to contacted tumor cells. TODO -- base this on tumor type (MHC1p, MHC1n)
        'PD1n_cytotoxic_packets': 5,  # number of packets to each contacted tumor cell
        'PD1p_cytotoxic_packets': 1,  # number of packets to each contacted tumor cell
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        if random.uniform(0, 1) < self.defaults['initial_PD1n']:
            self.initial_state = 'PD1n'
        else:
            self.initial_state = 'PD1p'

        parameters = self.defaults
        
        ports = {
            'internal': ['cell_state'],
            'boundary': ['IFNg']}
        super(T_cell, self).__init__(ports, parameters)

    def ports_schema(self):
        return {
            'internal': {
                'cell_state': {
                    '_default': self.initial_state,
                    '_emit': True,
                    '_updater': 'set'}},
            'boundary': {
                'diameter': {
                    '_default': self.parameters['diameter']
                },
                'IFNg': {
                    '_default': 0,
                    '_updater': 'accumulate',
                }
            }}

    def next_update(self, timestep, states):
        cell_state = states['internal']['cell_state']

        # state transition
        new_cell_state = cell_state
        death = False
        division = False
        IFNg = 0.0
        if cell_state == 'PD1n':
            # death
            if random.uniform(0, 1) < self.parameters['death_PD1n'] * timestep:
                death = True

            # change state
            if random.uniform(0,1) < self.parameters['transition_PD1n_to_PD1p'] * timestep:
                new_cell_state = 'PD1p'

            # produce IFNg  # TODO -- integer? save remainder
            IFNg = self.parameters['PD1n_IFNg_production'] * timestep

            # division # TODO -- make this reproduce the Petrovas distribution
            # if random.uniform(0, 1) < self.parameters['PD1n_growth'] * timestep:
            #     division = True

            # TODO migration

            # TODO killing -- pass cytotoxic packets to contacted tumor cells, based on tumor type
                
        if cell_state == 'PD1p':

            # TODO -- if next to PDL1+ tumor then use self.parameters['death_PD1p_next_to_PDL1p']
            if random.uniform(0, 1) < self.parameters['death_PD1p'] * timestep:
                death = True

            # produce IFNg  # TODO -- integer? save remainder
            IFNg = self.parameters['PD1p_IFNg_production'] * timestep

            # division # TODO -- make this reproduce the Petrovas distribution
            # if random.uniform(0, 1) < self.parameters['PD1p_growth'] * timestep:
            #     division = True

        # TODO -- if death, then pass a death update
        return {
            'internal': {
                'cell_state': new_cell_state},
            'boundary': {
                'IFNg': IFNg
            }}



def run_t_cells():
    t_cell_process = T_cell({})
    settings = {'total_time': 1000}
    timeseries = simulate_process_in_experiment(t_cell_process, settings)

    import ipdb;
    ipdb.set_trace()


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_t_cells()
