from __future__ import absolute_import, division, print_function

import os

from vivarium.core.experiment import (
    Compartment,
)

from vivarium.core.composition import (
    COMPARTMENT_OUT_DIR,
    simulate_compartment_in_experiment,
    plot_simulation_output,
)

# processes
from vivarium.processes.growth_protein import GrowthProtein
from vivarium.processes.minimal_expression import MinimalExpression
from vivarium.processes.division import (
    Division,
    divide_condition
)
from vivarium.processes.meta_division import MetaDivision
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config
)
from vivarium.processes.tree_mass import TreeMass

from vivarium.utils.dict_utils import deep_merge


NAME = 'growth_division'

class GrowthDivision(Compartment):

    defaults = {
        'global_path': ('..', 'global',),
        'external_path': ('..', 'external',),
        'exchange_path': ('..', 'exchange',),
        'agents_path': ('..', '..', 'cells',),
        'transport_config': get_glc_lct_config(),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config

        # paths
        self.global_path = config.get('global_path', self.defaults['global_path'])
        self.external_path = config.get('external_path', self.defaults['external_path'])
        self.exchange_path = config.get('exchange_path', self.defaults['exchange_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
        self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])

        # process configs
        self.transport_config = self.config.get('transport_config', self.defaults['transport_config'])
        self.transport_config['global_deriver_config'] = {
            'type': 'globals',
            'source_port': 'global',
            'derived_port': 'global',
            'global_port': self.global_path,
            'keys': []}

    def generate_processes(self, config):
        # declare the processes
        agent_id = config.get('agent_id', '0')  # TODO -- configure the agent_id

        transport_config = deep_merge(
            config.get('transport', {}),
            self.transport_config)

        division_config = dict(
            config.get('division', {}),
            daughter_path=self.daughter_path,
            cell_id=agent_id,
            compartment=self)

        growth = GrowthProtein(config.get('growth', {}))
        transport = ConvenienceKinetics(transport_config)
        division = MetaDivision(division_config)
        expression = MinimalExpression(config.get('expression', {}))
        mass = TreeMass(config.get('mass', {}))

        return {
            'transport': transport,
            'growth': growth,
            'expression': expression,
            'division': division,
            'mass': mass}

    def generate_topology(self, config):
        # make the topology.
        # for each process, map process ports to store ids
        external_path = config.get('external_path', self.external_path)
        exchange_path = config.get('external_path', self.exchange_path)
        global_path = config.get('global_path', self.global_path)
        agents_path = config.get('agents_path', self.agents_path)

        return {
            'transport': {
                'internal': ('internal',),
                'external': external_path,
                'exchange': exchange_path,
                'fluxes': ('fluxes',),
                'global': global_path},
            'growth': {
                'internal': ('internal',),
                'global': global_path},
            'mass': {
                'global': global_path},
            'division': {
                'global': global_path,
                'cells': agents_path},
            'expression': {
                'internal': ('internal',),
                'external': external_path,
                'concentrations': ('internal_concentrations',),
                'global': global_path}}



if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    compartment_config = {
        'external_path': ('external',),
        'exchange_path': ('exchange',),
        'global_path': ('global',),
        'agents_path': ('..', '..', 'cells',)}
    compartment = GrowthDivision(compartment_config)

    # settings for simulation and plot
    settings = {
        'environment': {
            'volume': 1e-6,  # L
            'environment_port': 'external',
            'states': list(compartment.transport_config['initial_state']['external'].keys()),
        },
        'outer_path': ('cells', '0'),
        'return_raw_data': True,
        'timestep': 1,
        'total_time': 100}
    data = simulate_compartment_in_experiment(compartment, settings)
