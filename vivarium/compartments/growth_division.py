from __future__ import absolute_import, division, print_function

import os
import uuid
import copy

from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    COMPARTMENT_OUT_DIR,
    simulate_compartment_in_experiment,
    plot_agents_multigen,
)

# processes
from vivarium.processes.growth_protein import GrowthProtein
from vivarium.processes.minimal_expression import MinimalExpression
from vivarium.processes.meta_division import MetaDivision
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config
)
from vivarium.processes.tree_mass import TreeMass

from vivarium.library.dict_utils import deep_merge


NAME = 'growth_division'

class GrowthDivision(Compartment):

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('..', '..', 'agents',),
        'transport': get_glc_lct_config(),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = copy.deepcopy(config)
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value

        # paths
        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
        # self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])

        # # process configs
        self.config['transport'] = self.config.get('transport', self.defaults['transport'])
        self.config['transport']['global_deriver_config'] = {
            'type': 'globals',
            'source_port': 'global',
            'derived_port': 'global',
            'global_port': self.boundary_path,
            'keys': []}

    def generate_processes(self, config):
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)

        growth = GrowthProtein(config.get('growth', {}))
        transport = ConvenienceKinetics(config.get('transport', {}))
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
        external_path = self.boundary_path + ('external',)
        exchange_path = self.boundary_path + ('exchange',)

        return {
            'transport': {
                'internal': ('internal',),
                'external': external_path,
                'exchange': exchange_path,
                'fluxes': ('fluxes',),
                'global': self.boundary_path},
            'growth': {
                'internal': ('internal',),
                'global': self.boundary_path},
            'mass': {
                'global': self.boundary_path},
            'division': {
                'global': self.boundary_path,
                'cells': self.agents_path},
            'expression': {
                'internal': ('internal',),
                'external': external_path,
                'concentrations': ('internal_concentrations',),
                'global': self.boundary_path}}



if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    agent_id = '0'
    compartment = GrowthDivision({'agent_id': agent_id})

    # settings for simulation and plot
    settings = {
        'environment': {
            'volume': 1e-6 * units.L,  # L
            'ports': {
                'exchange': ('boundary', 'exchange',),
                'external': ('boundary', 'external',)}
        },
        'outer_path': ('agents', agent_id),  # TODO -- need to set the agent_id through here?
        'return_raw_data': True,
        'timestep': 1,
        'total_time': 500}
    output_data = simulate_compartment_in_experiment(compartment, settings)

    plot_settings = {}
    plot_agents_multigen(output_data, plot_settings, out_dir)
