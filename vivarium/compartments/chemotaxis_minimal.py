from __future__ import absolute_import, division, print_function

import os
import random

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
from vivarium.processes.Vladimirov2008_motor import MotorActivity



NAME = 'chemotaxis_minimal'

class ChemotaxisMinimal(Compartment):

    defaults = {
        'ligand_id': 'MeAsp',
        'initial_ligand': 0.1,
        'boundary_path': ('boundary',)
    }

    def __init__(self, config):
        self.config = config
        self.ligand_id = config.get(
            'ligand_id',
            self.defaults['ligand_id'])
        self.initial_ligand = config.get(
            'initial_ligand',
            self.defaults['initial_ligand'])
        self.boundary_path = self.config.get(
            'boundary_path',
            self.defaults['boundary_path'])

    def generate_processes(self, config):
        receptor_parameters = {
            'ligand_id': self.ligand_id,
            'initial_ligand': self.initial_ligand}

        # declare the processes
        receptor = ReceptorCluster(receptor_parameters)
        motor = MotorActivity({})

        return {
            'receptor': receptor,
            'motor': motor}

    def generate_topology(self, config):
        external_path = self.boundary_path + ('external',)
        return {
            'receptor': {
                'external': external_path,
                'internal': ('cell',)},
            'motor': {
                'external': self.boundary_path,
                'internal': ('cell',)}}


def get_chemotaxis_config(config={}):
    ligand_id = config.get('ligand_id', 'MeAsp')
    initial_ligand = config.get('initial_ligand', 5.0)
    external_path = config.get('external_path', 'external')
    return {
        'external_path': (external_path,),
        'ligand_id': ligand_id,
        'initial_ligand': initial_ligand}


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

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
        'ligand_id': ligand_id,
        'initial_ligand': initial_conc,
        'external_path': environment_port}
    compartment = ChemotaxisMinimal(get_chemotaxis_config(config))

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
