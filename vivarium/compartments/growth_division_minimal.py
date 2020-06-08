from __future__ import absolute_import, division, print_function

import os

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_agent_data,
    COMPARTMENT_OUT_DIR,
)

# processes
from vivarium.processes.growth_protein import GrowthProtein
from vivarium.processes.meta_division import MetaDivision

from vivarium.library.dict_utils import deep_merge


NAME = 'growth_division_minimal'

class GrowthDivisionMinimal(Compartment):

    defaults = {
        'global_path': ('..', 'global',),
        'agents_path': ('..', '..', 'cells',),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config

        # paths
        self.global_path = config.get('global_path', self.defaults['global_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
        self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])


    def generate_processes(self, config):
        # declare the processes
        agent_id = config.get('agent_id', '0')  # TODO -- configure the agent_id

        division_config = dict(
            config.get('division', {}),
            daughter_path=self.daughter_path,
            cell_id=agent_id,
            compartment=self)

        growth = GrowthProtein(config.get('growth', {}))
        division = MetaDivision(division_config)

        return {
            'growth': growth,
            'division': division}

    def generate_topology(self, config):
        global_path = config.get('global_path', self.global_path)
        agents_path = config.get('agents_path', self.agents_path)

        return {
            'growth': {
                'internal': ('internal',),
                'global': global_path},
            'division': {
                'global': global_path,
                'cells': agents_path},
            }


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    compartment_config = {
        'global_path': ('global',),
        'agents_path': ('..', '..', 'cells',)}
    compartment = GrowthDivisionMinimal(compartment_config)

    # settings for simulation and plot
    settings = {
        'environment': {
            'volume': 1e-6,  # L
            'environment_port': 'external',
            # 'states': list(compartment.transport_config['initial_state']['external'].keys()),
        },
        'outer_path': ('cells', '0'),
        'return_raw_data': True,
        'timestep': 1,
        'total_time': 600}
    output_data = simulate_compartment_in_experiment(compartment, settings)

    plot_settings = {}
    plot_agent_data(output_data, plot_settings, out_dir)
