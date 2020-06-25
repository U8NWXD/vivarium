from __future__ import absolute_import, division, print_function

import os
import random
import argparse

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    COMPARTMENT_OUT_DIR
)

# processes
from vivarium.processes.Endres2006_chemoreceptor import (
    ReceptorCluster,
    get_exponential_random_timeline
)
from vivarium.processes.Mears2014_flagella_activity import FlagellaActivity



NAME = 'chemotaxis_variable_flagella'

class ChemotaxisVariableFlagella(Compartment):

    defaults = {
        'n_flagella': 5,
        'ligand_id': 'MeAsp',
        'initial_ligand': 0.1,
        'boundary_path': ('boundary',)
    }

    def __init__(self, config):
        self.config = config

        n_flagella = config.get(
            'n_flagella',
            self.defaults['n_flagella'])
        ligand_id = config.get(
            'ligand_id',
            self.defaults['ligand_id'])
        initial_ligand = config.get(
            'initial_ligand',
            self.defaults['initial_ligand'])
        self.boundary_path = self.config.get(
            'boundary_path',
            self.defaults['boundary_path'])

        self.config['receptor'] = {
            'ligand_id': ligand_id,
            'initial_ligand': initial_ligand}

        self.config['flagella'] = {
            'n_flagella': n_flagella}

    def generate_processes(self, config):
        receptor = ReceptorCluster(config['receptor'])
        flagella = FlagellaActivity(config['flagella'])

        return {
            'receptor': receptor,
            'flagella': flagella}

    def generate_topology(self, config):
        boundary_path = ('boundary',)
        external_path = boundary_path + ('external',)
        return {
            'receptor': {
                'external': external_path,
                'internal': ('cell',)},
            'flagella': {
                'internal': ('internal',),
                'membrane': ('membrane',),
                'internal_counts': ('proteins',),
                'flagella': ('flagella',),
                'boundary': boundary_path},
        }


def test_variable_chemotaxis(n_flagella=5, out_dir='out'):
    environment_port = 'external'
    ligand_id = 'MeAsp'
    initial_conc = 0
    total_time = 60

    # configure timeline
    exponential_random_config = {
        'ligand': ligand_id,
        'environment_port': environment_port,
        'time': total_time,
        'timestep': 1,
        'initial_conc': initial_conc,
        'base': 1+4e-4,
        'speed': 14}

    # make the compartment
    config = {
        'external_path': (environment_port,),
        'ligand_id': ligand_id,
        'initial_ligand': initial_conc,
        'n_flagella': n_flagella}
    compartment = ChemotaxisVariableFlagella(config)

    # run experiment
    experiment_settings = {
        'timeline': {
            'timeline': get_exponential_random_timeline(exponential_random_config),
            'ports': {'external': ('boundary', 'external')}},
        'timestep': 0.01,
        'total_time': 100}
    timeseries = simulate_compartment_in_experiment(compartment, experiment_settings)

    # plot settings for the simulations
    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'overlay': {
            'reactions': 'flux'},
        'skip_ports': ['prior_state', 'null', 'global']}
    plot_simulation_output(
        timeseries,
        plot_settings,
        out_dir,
        'exponential_timeline')


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='variable flagella')
    parser.add_argument('--flagella', '-f', type=int, default=5)
    args = parser.parse_args()

    test_variable_chemotaxis(args.flagella, out_dir)
