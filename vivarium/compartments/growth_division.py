from __future__ import absolute_import, division, print_function

import os

from vivarium.core.process import (
    initialize_state)

from vivarium.core.tree import (
    Compartment,
)

from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output
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


class GrowthDivision(Compartment):

    defaults = {
        'global_key': ('..', 'global',),
        'external_key': ('..', 'external',),
        'cells_key': ('..', '..', 'cells',)}

    def __init__(self, config):
        self.config = config
        self.global_key = config.get('global_key', self.defaults['global_key'])
        self.external_key = config.get('external_key', self.defaults['external_key'])
        self.cells_key = config.get('cells_key', self.defaults['cells_key'])

        # self.external_key = ('..',) + self.config.get('external_key', ('external',))
        # self.cells_key = ('..', '..') + self.config.get('cells_key', ('cells',))

        self.transport_config = self.config.get('transport', get_glc_lct_config())
        self.transport_config['global_deriver_config'] = {
            'type': 'globals',
            'source_port': 'global',
            'derived_port': 'global',
            'global_port': self.global_key,
            'keys': []}

    def generate_processes(self, config):
        # declare the processes
        agent_id = config.get('agent_id')

        transport_config = deep_merge(
            config.get('transport', {}),
            self.transport_config)

        division_config = dict(
            config.get('division', {}),
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
        external_key = config.get('external_key', self.external_key)
        global_key = config.get('global_key', self.global_key)
        cells_key = config.get('cells_key', self.cells_key)

        return {
            'transport': {
                'internal': ('cell',),
                'external': external_key,
                'exchange': external_key,
                # 'fluxes': ['flux'], # just for testing
                'fluxes': None,
                'global': global_key},
            'growth': {
                'internal': ('cell',),
                'global': global_key},
            'mass': {
                'global': global_key},
            'division': {
                'global': global_key,
                'cells': cells_key},
            'expression': {
                'internal': ('cell',),
                'external': external_key,
                'concentrations': ('cell_concentrations',),
                'global': global_key}}



if __name__ == '__main__':
    out_dir = os.path.join('out', 'tests', 'growth_division_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    compartment_config = {
        'external_key': ('external',),
        'global_key': ('global',),
        'cells_key': ('cells',)}
    compartment = GrowthDivision(compartment_config)

    # TODO -- pass in an environment compartment, add to experiment
    # settings for simulation and plot
    settings = {
        'environment': {
            'volume': 1e-6,  # L
            'environment_port': 'external',
            'states': list(compartment.transport_config['initial_state']['external'].keys()),
            # 'exchange_port': ('exchange'),
        },
        'timestep': 1,
        'total_time': 100}
    timeseries = simulate_compartment_in_experiment(compartment, settings)

    import ipdb; ipdb.set_trace()

    plot_settings = {
        'max_rows': 25,
        'skip_ports': ['prior_state']}
    plot_simulation_output(timeseries, plot_settings, out_dir)
