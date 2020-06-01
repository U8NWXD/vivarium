from __future__ import absolute_import, division, print_function

import os
import random

from vivarium.core.tree import Compartment
from vivarium.core.composition import (
    add_timeline_to_compartment,
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
        'external_path': ('..', 'external',)
    }

    def __init__(self, config):
        self.config = config
        self.ligand_id = config.get(
            'ligand_id',
            self.defaults['ligand_id'])
        self.initial_ligand = config.get(
            'initial_ligand',
            self.defaults['initial_ligand'])
        self.external_path = self.config.get(
            'external_path',
            self.defaults['external_path'])

    def generate_processes(self, config):
        receptor_parameters = {
            'ligand': self.ligand_id,
            'initial_ligand': self.initial_ligand}

        # declare the processes
        receptor = ReceptorCluster(receptor_parameters)
        motor = MotorActivity({})

        return {
            'receptor': receptor,
            'motor': motor}

    def generate_topology(self, config):
        return {
            'receptor': {
                'external': self.external_path,
                'internal': ('cell',)},
            'motor': {
                'external': self.external_path,
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
    timeline_config = {
        'timeline': get_exponential_random_timeline(exponential_random_config),
        'path': {'external': ('external',)}}

    # make the compartment
    config = {
        'ligand_id': ligand_id,
        'initial_ligand': initial_conc,
        'external_path': environment_port}
    compartment = ChemotaxisMinimal(get_chemotaxis_config(config))

    # add the timeline
    compartment = add_timeline_to_compartment(compartment, timeline_config)

    # run experiment
    experiment_settings = {
        'timestep': 1,
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
