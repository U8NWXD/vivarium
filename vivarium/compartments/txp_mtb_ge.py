from __future__ import absolute_import, division, print_function

import os
import argparse

from vivarium.core.tree import Compartment
from vivarium.core.composition import simulate_compartment_in_experiment

from vivarium.core.composition import (
    simulate_with_environment,
    plot_simulation_output,
    load_compartment)
from vivarium.parameters.parameters import (
    parameter_scan,
    get_parameters_logspace,
    plot_scan_results)

# processes
from vivarium.processes.meta_division import MetaDivision
from vivarium.processes.metabolism import (
    Metabolism,
    get_iAF1260b_config)
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config)
from vivarium.processes.ode_expression import (
    ODE_expression,
    get_lacy_config)


def default_metabolism_config():
    config = get_iAF1260b_config()

    # set flux bond tolerance for reactions in ode_expression's lacy_config
    metabolism_config = {
        'moma': False,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0]}}
    config.update(metabolism_config)
    return config


class TransportMetabolismExpression(Compartment):
    """
    TransportMetabolismExpression Compartment
    """

    defaults = {
        'global_path': ('..', 'global'),
        'external_path': ('..', 'external'),
        'daughter_path': tuple(),
        'transport': get_glc_lct_config(),
        'metabolism': default_metabolism_config(),
        'expression': get_lacy_config(),
        'division': {}}

    def __init__(self, config):
        self.global_path = config.get('global_path', self.defaults['global_path'])
        self.external_path = config.get('external_path', self.defaults['external_path'])
        self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])
        
        self.transport_config = config.get('transport', self.defaults['transport'])
        self.metabolism_config = config.get('metabolism', self.defaults['metabolism'])
        self.expression_config = config.get('expression', self.defaults['expression'])
        self.division_config = config.get('division', self.defaults['division'])

    def generate_processes(self, config):
        agent_id = config.get('agent_id', '0')  # TODO -- configure the agent_id

        # Transport
        # load the kinetic parameters
        transport = ConvenienceKinetics(config.get(
            'transport',
            self.transport_config))

        # Metabolism
        # get target fluxes from transport, and update constrained_reaction_ids
        metabolism_config = config.get(
            'metabolism',
            self.metabolism_config)
        target_fluxes = transport.kinetic_rate_laws.reaction_ids
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # Gene expression
        expression = ODE_expression(config.get(
            'expression',
            self.expression_config))

        # Division
        division_config = dict(
            config.get('division', {}),
            daughter_path=self.daughter_path,
            cell_id=agent_id,
            compartment=self)
        # initial_mass = metabolism.initial_mass
        # division_config.update({'constrained_reaction_ids': target_fluxes})
        # TODO -- configure metadivision
        division = MetaDivision(division_config)

        return {
            'transport': transport,
            'metabolism': metabolism,
            'expression': expression,
            'division': division}

    def generate_topology(self, config):
        external_path = config.get('external_path', self.external_path)
        global_path = config.get('global_path', self.global_path)

        return {
            'transport': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'exchange': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': global_path,
            },
            'metabolism': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'reactions': ('reactions',),
                'exchange': ('exchange',),
                'flux_bounds': ('flux_bounds',),
                'global': global_path,
            },
            'expression': {
                'counts': ('cytoplasm_counts',),
                'internal': ('cytoplasm',),
                'external': external_path
            },
            'division': {
                'global': global_path,
            }
        }


# simulate
def test_txp_mtb_ge(total_time=10):
    # configure the compartment
    compartment_config = {
        'external_path': ('external',),
        'exchange_path': ('exchange',),
        'global_path': ('global',),
        'cells_path': ('..', '..', 'cells',)}
    compartment = TransportMetabolismExpression(compartment_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': total_time}
    return simulate_compartment_in_experiment(compartment, settings)

def simulate_txp_mtb_ge(config={}, out_dir='out'):

    # run simulation
    timeseries = test_txp_mtb_ge(2520) # 2520 sec (42 min) is the expected doubling time in minimal media
    volume_ts = timeseries['global']['volume']
    print('growth: {}'.format(volume_ts[-1]/volume_ts[0]))

    # plot
    plot_settings = {
        'max_rows': 30,
        'remove_zeros': True,
        'overlay': {
            'reactions': 'flux_bounds'},
        'skip_ports': [
            'prior_state', 'null'],
        'show_state': [
            ('reactions', 'EX_glc__D_e'),
            ('reactions', 'EX_lcts_e')]}
    plot_simulation_output(timeseries, plot_settings, out_dir)


# parameters
def scan_txp_mtb_ge():
    composite_function = compose_txp_mtb_ge

    # parameters to be scanned, and their values
    scan_params = {
        ('transport',
         'kinetic_parameters',
         'EX_glc__D_e',
         ('internal', 'EIIglc'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 4),
        ('transport',
         'kinetic_parameters',
         'EX_lcts_e',
         ('internal', 'LacY'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 4),
    }

    # metrics are the outputs of a scan
    metrics = [
        ('reactions', 'EX_glc__D_e'),
        ('reactions', 'EX_lcts_e'),
        ('global', 'mass')
    ]

    # define conditions
    conditions = [
        # {}, # default
        {
        'environment': {
            'glc__D_e': 12.0,
            'lcts_e': 10.0},
        'cytoplasm':{
            'LacY': 0.0}
        },
        {
        'environment': {
            'glc__D_e': 0.0,
            'lcts_e': 10.0},
        'cytoplasm':{
            'LacY': 1.0e-6}
        },
    ]

    ## TODO -- add targets
    # targets = {
    #     'global', 'growth_rate'
    # }

    # set up scan options
    timeline = [(10, {})]
    sim_settings = {
        'environment_port': 'environment',
        'exchange_port': 'exchange',
        'environment_volume': 1e-6,  # L
        'timeline': timeline}
    scan_options = {
        'simulate_with_environment': True,
        'simulation_settings': sim_settings}

    # run scan
    scan_config = {
        'composite': composite_function,
        'scan_parameters': scan_params,
        'conditions': conditions,
        'metrics': metrics,
        'options': scan_options}
    results = parameter_scan(scan_config)

    return results


if __name__ == '__main__':
    out_dir = os.path.join('out', 'tests', 'txp_mtb_ge_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # run scan with python vivarium/compartments/txp_mtb_ge.py --scan
    parser = argparse.ArgumentParser(description='transport metabolism composite')
    parser.add_argument('--scan', '-s', action='store_true', default=False,)
    parser.add_argument('--run', '-r', action='store_true', default=False, )
    args = parser.parse_args()

    if args.scan:
        results = scan_txp_mtb_ge()
        plot_scan_results(results, out_dir)
    else:
        config = {}
        simulate_txp_mtb_ge(config, out_dir)
