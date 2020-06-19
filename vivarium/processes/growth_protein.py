from __future__ import absolute_import, division, print_function

import os

import numpy as np

from vivarium.library.units import units
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)


NAME = 'growth_protein'

class GrowthProtein(Process):
 
    defaults = {
        'initial_protein': 5e7,
        'growth_rate': 0.006,
        'global_deriver_key': 'global_deriver',
        'mass_deriver_key': 'mass_deriver',
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        self.growth_rate = self.or_default(initial_parameters, 'growth_rate')
        self.global_deriver_key = self.or_default(
            initial_parameters, 'global_deriver_key')
        self.mass_deriver_key = self.or_default(
            initial_parameters, 'mass_deriver_key')

        # default state
        # 1000 proteins per fg
        self.initial_protein = self.or_default(
            initial_parameters, 'initial_protein')  # counts of protein
        self.divide_protein = self.initial_protein * 2

        parameters = {
            'growth_rate': self.growth_rate}
        parameters.update(initial_parameters)

        super(GrowthProtein, self).__init__(parameters)

    def ports_schema(self):
        return {
            'internal': {
                'protein': {
                    '_default': self.initial_protein,
                    '_divider': 'split',
                    '_emit': True,
                    '_properties': {
                        'mw': 2.09e4 * units.g / units.mol}}},  # the median E. coli protein is 209 amino acids long, and AAs ~ 100 Da
            'global': {
                'volume': {
                    '_updater': 'set',
                    '_divider': 'split'},
                'divide': {
                    '_default': False,
                    '_updater': 'set'}}}

    def derivers(self):
        return {
            self.global_deriver_key: {
                'deriver': 'globals',
                'port_mapping': {
                    'global': 'global'},
                'config': {}},
            self.mass_deriver_key: {
                'deriver': 'mass',
                'port_mapping': {
                    'global': 'global'},
                'config': {}},
        }

    def next_update(self, timestep, states):
        protein = states['internal']['protein']
        total_protein = protein * np.exp(self.parameters['growth_rate'] * timestep)
        new_protein = int(total_protein - protein)
        extra = total_protein - int(total_protein)

        # simulate remainder
        where = np.random.random()
        if where < extra:
            new_protein += 1

        divide = False
        if protein >= self.divide_protein:
            divide = True

        return {
            'internal': {
                'protein': new_protein},
            'global': {
                'divide': divide}}

if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    process = GrowthProtein()
    settings = {'total_time': 10}
    timeseries = simulate_process_in_experiment(process, settings)
    plot_simulation_output(timeseries, {}, out_dir)
