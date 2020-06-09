from __future__ import absolute_import, division, print_function

import os

from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_agents_multigen,
    COMPARTMENT_OUT_DIR,
)

# processes
from vivarium.processes.growth_protein import GrowthProtein
from vivarium.processes.meta_division import MetaDivision

from vivarium.library.dict_utils import deep_merge


NAME = 'growth_division_minimal'

class GrowthDivisionMinimal(Compartment):

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('..', '..', 'agents',),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value

        # paths
        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
        # self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])

    def generate_processes(self, config):
        # declare the processes
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)

        growth = GrowthProtein(config.get('growth', {}))
        division = MetaDivision(division_config)

        return {
            'growth': growth,
            'division': division}

    def generate_topology(self, config):
        return {
            'growth': {
                'internal': ('internal',),
                'global': self.boundary_path},
            'division': {
                'global': self.boundary_path,
                'cells': self.agents_path},
            }


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    agent_id = '0'
    compartment = GrowthDivisionMinimal({'agent_id': agent_id})

    # settings for simulation and plot
    settings = {
        'outer_path': ('agents', agent_id),
        'return_raw_data': True,
        'timestep': 1,
        'total_time': 600}
    output_data = simulate_compartment_in_experiment(compartment, settings)

    plot_settings = {}
    plot_agents_multigen(output_data, plot_settings, out_dir)
