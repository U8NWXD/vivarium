from __future__ import absolute_import, division, print_function

import os
import argparse

import matplotlib.pyplot as plt

from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.emitter import get_timeseries_from_path
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
        'agents_path': ('..', '..', 'agents',),
        'daughter_path': tuple(),
        'transport': get_glc_lct_config(),
        'metabolism': default_metabolism_config(),
        'expression': default_expression_config(),
        'division': {}}

    def __init__(self, config):
        self.config = config

        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])
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
            'division': division
        }

    def generate_topology(self, config):
        exchange_path =  self.boundary_path + ('exchange',)
        external_path = self.boundary_path + ('external',)
        # properties_path = self.boundary_path + ('properties',)
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
def test_txp_mtb_ge(total_time=10):
    # configure the compartment
    compartment_config = {
        'external_path': ('external',),
        'exchange_path': ('exchange',),
        'global_path': ('global',),
        'agents_path': ('agents',)}
    compartment = TransportMetabolism(compartment_config)

    # simulate
    settings = {
        'environment': {
            'volume': 1e-12 * units.L,
            'ports': {
                'exchange': ('boundary', 'exchange',),
                'external': ('boundary', 'external'),
            }},
        'timestep': 1,
        'total_time': total_time}
    return simulate_compartment_in_experiment(compartment, settings)

def simulate_txp_mtb_ge(config={}, out_dir='out'):
    # run simulation
    timeseries = test_txp_mtb_ge(20)  # 2520 sec (42 min) is the expected doubling time in minimal media

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

# plots
def plot_diauxic_shift(timeseries, settings={}, out_dir='out'):
    external_path = settings.get('external_path', ('environment',))
    internal_path = settings.get('internal_path', ('cytoplasm',))
    internal_counts_path = settings.get('internal_counts_path', ('cytoplasm_counts',))
    reactions_path = settings.get('reactions_path', ('reactions',))
    global_path = settings.get('global_path', ('global',))

    time = [t/60 for t in timeseries['time']]  # convert to minutes

    environment = get_timeseries_from_path(timeseries, external_path)
    cell = get_timeseries_from_path(timeseries, internal_path)
    cell_counts = get_timeseries_from_path(timeseries, internal_counts_path)
    reactions = get_timeseries_from_path(timeseries, reactions_path)
    globals = get_timeseries_from_path(timeseries, global_path)

    # environment
    lactose = environment['lcts_e']
    glucose = environment['glc__D_e']

    # internal
    LacY = cell['LacY']
    lacy_RNA = cell['lacy_RNA']
    LacY_counts = cell_counts['LacY']
    lacy_RNA_counts = cell_counts['lacy_RNA']

    # reactions
    glc_exchange = reactions['EX_glc__D_e']
    lac_exchange = reactions['EX_lcts_e']

    # global
    mass = globals['mass']

    # settings
    environment_volume = settings.get('environment_volume')

    n_cols = 2
    n_rows = 4

    # make figure and plot
    fig = plt.figure(figsize=(n_cols * 6, n_rows * 1.5))
    grid = plt.GridSpec(n_rows, n_cols)

    ax1 = fig.add_subplot(grid[0, 0])  # grid is (row, column)
    ax1.plot(time, glucose, label='glucose')
    ax1.plot(time, lactose, label='lactose')
    set_axes(ax1)
    ax1.title.set_text('environment, volume = {} L'.format(environment_volume))
    ax1.set_ylabel('(mM)')
    ax1.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    ax2 = fig.add_subplot(grid[1, 0])  # grid is (row, column)
    ax2.plot(time, lacy_RNA, label='lacy_RNA')
    ax2.plot(time, LacY, label='LacY')
    set_axes(ax2)
    ax2.title.set_text('internal')
    ax2.set_ylabel('(mM)')
    ax2.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    ax3 = fig.add_subplot(grid[2, 0])  # grid is (row, column)
    ax3.plot(time, mass, label='mass')
    set_axes(ax3, True)
    ax3.title.set_text('global')
    ax3.set_ylabel('(fg)')
    ax3.set_xlabel('time (min)')
    ax3.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    ax4 = fig.add_subplot(grid[0, 1])  # grid is (row, column)
    ax4.plot(time, glc_exchange, label='glucose exchange')
    ax4.plot(time, lac_exchange, label='lactose exchange')
    set_axes(ax4, True)
    ax4.title.set_text('flux'.format(environment_volume))
    ax4.set_xlabel('time (min)')
    ax4.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    # save figure
    fig_path = os.path.join(out_dir, 'diauxic_shift')
    plt.subplots_adjust(wspace=0.6, hspace=0.5)
    plt.savefig(fig_path, bbox_inches='tight')

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
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # run scan with python vivarium/compartments/transport_metabolism.py --scan
    parser = argparse.ArgumentParser(description='transport metabolism composite')
    parser.add_argument('--scan', '-s', action='store_true', default=False, )
    parser.add_argument('--run', '-r', action='store_true', default=False, )
    args = parser.parse_args()

    if args.scan:
        results = scan_txp_mtb_ge()
        plot_scan_results(results, out_dir)
    else:
        config = {}
        simulate_txp_mtb_ge(config, out_dir)
