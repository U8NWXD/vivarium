from __future__ import absolute_import, division, print_function

import os
import argparse

from vivarium.library.dict_utils import get_value_from_path
from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    set_axes,
    COMPARTMENT_OUT_DIR)
from vivarium.parameters.parameters import (
    parameter_scan,
    get_parameters_logspace,
    plot_scan_results)

# processes
from vivarium.plots.transport_metabolism import plot_diauxic_shift
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


NAME = 'transport_metabolism'

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

def default_expression_config():
    # glc lct config from ode_expression
    config = get_lacy_config()

    # redo regulation with BiGG id for glucose
    regulators = [('external', 'glc__D_e')]
    regulation = {'lacy_RNA': 'if not (external, glc__D_e) > 0.1'}
    reg_config = {
        'regulators': regulators,
        'regulation': regulation}

    config.update(reg_config)

    return config


class TransportMetabolism(Compartment):
    """
    Transport/Metabolism Compartment, with ODE expression
    """

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('agents',),
        'daughter_path': tuple(),
        'division': {}}

    default_config = {
        'transport': get_glc_lct_config(),
        'metabolism': default_metabolism_config(),
        'expression': default_expression_config()}

    def __init__(self, config=None):
        if not config:
            config = self.default_config
        self.config = config

        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
        self.daughter_path = config.get('daughter_path', self.defaults['daughter_path'])

    def generate_processes(self, config):
        agent_id = config.get('agent_id', '0')  # TODO -- configure the agent_id

        # Transport
        # load the kinetic parameters
        transport = ConvenienceKinetics(config.get('transport', {}))

        # Metabolism
        # get target fluxes from transport, and update constrained_reaction_ids
        metabolism_config = config.get('metabolism', {})
        target_fluxes = transport.kinetic_rate_laws.reaction_ids
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # Gene expression
        expression = ODE_expression(config.get('expression', {}))

        # Division
        division_config = dict(
            config.get('division', {}),
            daughter_path=self.daughter_path,
            agent_id=agent_id,
            compartment=self)
        # initial_mass = metabolism.initial_mass
        # division_config.update({'constrained_reaction_ids': target_fluxes})
        # TODO -- configure metadivision
        division = MetaDivision(division_config)

        return {
            'transport': transport,
            'metabolism': metabolism,
            'expression': expression,
            'division': division
        }

    def generate_topology(self, config):
        exchange_path = self.boundary_path + ('exchange',)
        external_path = self.boundary_path + ('external',)
        return {
            'transport': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'exchange': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': self.boundary_path,
            },
            'metabolism': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'reactions': ('reactions',),
                'exchange': exchange_path,
                'flux_bounds': ('flux_bounds',),
                'global': self.boundary_path,
            },
            'expression': {
                'counts': ('cytoplasm_counts',),
                'internal': ('cytoplasm',),
                'external': external_path,
                'global': self.boundary_path,
            },
            'division': {
                'global': self.boundary_path,
                'cells': self.agents_path,
            }
        }


# simulate
def test_txp_mtb_ge():
    default_test_setting = {
        'environment': {
            'volume': 1e-12 * units.L,
            'ports': {
                'exchange': ('boundary', 'exchange',),
                'external': ('boundary', 'external'),
            }},
        'timestep': 1,
        'total_time': 10}

    compartment = TransportMetabolism({})
    return simulate_compartment_in_experiment(compartment, default_test_setting)

def simulate_txp_mtb_ge(config={}, out_dir='out'):

    end_time = 2520  # 2520 sec (42 min) is the expected doubling time in minimal media
    environment_volume = 1e-14
    timeline = [
        (0, {
            ('external', 'glc__D_e'): 3.0,
            ('external', 'lcts_e'): 3.0,
        }),
        # (500, {
        #     ('external', 'glc__D_e'): 0.0,
        #     ('external', 'lcts_e'): 3.0,
        # }),
        (end_time, {})]

    sim_settings = {
        'environment': {
            'volume': environment_volume * units.L,
            'ports': {
                'external': ('boundary', 'external'),
                'exchange': ('boundary', 'exchange'),
            }},
        'timeline': {
            'timeline': timeline,
            'ports': {
                'external': ('boundary', 'external')}}
    }

    # run simulation
    compartment = TransportMetabolism({})
    timeseries = simulate_compartment_in_experiment(compartment, sim_settings)

    # calculate growth
    volume_ts = timeseries['boundary']['volume']
    try:
        print('growth: {}'.format(volume_ts[-1] / volume_ts[0]))
    except:
        print('no volume!')

    ## plot
    # diauxic plot
    settings = {
        'internal_path': ('cytoplasm',),
        'external_path': ('boundary', 'external'),
        'global_path': ('boundary',),
        'exchange_path': ('boundary', 'exchange'),
        'environment_volume': 1e-13,  # L
        # 'timeline': timeline
    }
    plot_diauxic_shift(timeseries, settings, out_dir)

    # simulation plot
    plot_settings = {
        'max_rows': 30,
        'remove_zeros': True,
        'skip_ports': ['null', 'reactions'],
    }
    plot_simulation_output(timeseries, plot_settings, out_dir)

# parameters
def scan_transport_metabolism():

    # initialize the compartment
    compartment = TransportMetabolism({})

    # parameters to be scanned, and their values
    scan_params = {
        ('transport',
         'kinetic_parameters',
         'EX_glc__D_e',
         ('internal', 'EIIglc'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 3),
        ('transport',
         'kinetic_parameters',
         'EX_lcts_e',
         ('internal', 'LacY'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 3),
    }

    # metrics are the outputs of a scan
    metrics = [
        ('reactions', 'EX_glc__D_e'),
        ('reactions', 'EX_lcts_e'),
        ('boundary', 'mass')
    ]

    # define conditions
    conditions = [
        {
        'environment': {
            'glc__D_e': 12.0,
            'lcts_e': 10.0},
        'cytoplasm': {
            'LacY': 0.0}
        },
        {
        'environment': {
            'glc__D_e': 0.0,
            'lcts_e': 10.0},
        'cytoplasm': {
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
        'environment': {
            'volume': 1e-14 * units.L,
            'ports': {
                'external': ('boundary', 'external'),
                'exchange': ('boundary', 'exchange'),
            }},
        'timeline': {
            'timeline': timeline,
            'ports': {
                'external': ('boundary', 'external')}}}

    # run scan
    scan_config = {
        'compartment': compartment,
        'scan_parameters': scan_params,
        'conditions': conditions,
        'metrics': metrics,
        'settings': sim_settings}
    results = parameter_scan(scan_config)

    return results


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # run scan with python vivarium/compartments/transport_metabolism.py --scan
    parser = argparse.ArgumentParser(description='transport metabolism composite')
    parser.add_argument('--scan', '-s', action='store_true', default=False, )
    parser.add_argument('--run', '-r', action='store_true', default=False, )
    args = parser.parse_args()

    if args.scan:
        results = scan_transport_metabolism()
        plot_scan_results(results, out_dir)
    else:
        config = {}
        simulate_txp_mtb_ge(config, out_dir)
