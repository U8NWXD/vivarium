from __future__ import absolute_import, division, print_function

import os

import matplotlib.pyplot as plt

from vivarium.actor.composition import set_axes

# composite
from vivarium.composites.ode_expression import compose_ode_expression

# process configurations
from vivarium.processes.metabolism import get_e_coli_core_config
from vivarium.processes.convenience_kinetics import get_glc_lct_config
from vivarium.processes.ode_expression import get_lacy_config


# processes configurations
def get_metabolism_config():
    config = get_e_coli_core_config()

    # set flux bond tolerance for reactions in ode_expression's lacy_config
    metabolism_config = {
        'moma': False,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lac__D_e': [1.05, 1.0]}}

    config.update(metabolism_config)

    return config

def get_expression_config():
    # glc lct config from ode_expression
    config = get_lacy_config()

    # define regulation
    regulators = [('external', 'glc__D_e')]
    regulation = {'lacy_RNA': 'if not (external, glc__D_e) > 0.1'}
    reg_config = {
        'regulators': regulators,
        'regulation': regulation}

    config.update(reg_config)

    return config

# composite configuration
def compose_glc_lct_shifter(config):
    """
    Load a glucose/lactose diauxic shift configuration into the kinetic_FBA composite
    TODO (eran) -- fit glc/lct uptake rates to growth rates
    """
    shifter_config = {
        'name': 'glc_lct_shifter',
        'transport': get_glc_lct_config(),
        'metabolism': get_metabolism_config(),
        'expression': get_expression_config()}

    config.update(shifter_config)

    return compose_ode_expression(config)



def plot_diauxic_shift(timeseries, settings={}, out_dir='out'):

    time = timeseries['time']
    environment = timeseries['environment']
    cell = timeseries['cell']
    cell_counts = timeseries['cell_counts']
    reactions = timeseries['reactions']
    globals = timeseries['global']

    # environment
    lactose = environment['lac__D_e']
    glucose = environment['glc__D_e']

    # internal
    LacY = cell['LacY']
    lacy_RNA = cell['lacy_RNA']
    LacY_counts = cell_counts['LacY']
    lacy_RNA_counts = cell_counts['lacy_RNA']

    # reactions
    glc_exchange = reactions['EX_glc__D_e']
    lac_exchange = reactions['EX_lac__D_e']

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
    ax3.set_xlabel('time (s)')
    ax3.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    ax4 = fig.add_subplot(grid[0, 1])  # grid is (row, column)
    ax4.plot(time, glc_exchange, label='glucose exchange')
    ax4.plot(time, lac_exchange, label='lactose exchange')
    set_axes(ax4, True)
    ax4.title.set_text('flux'.format(environment_volume))
    ax4.set_xlabel('time (s)')
    ax4.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    # save figure
    fig_path = os.path.join(out_dir, 'diauxic_shift')
    plt.subplots_adjust(wspace=0.6, hspace=0.5)
    plt.savefig(fig_path, bbox_inches='tight')



if __name__ == '__main__':
    from vivarium.actor.process import load_compartment
    from vivarium.actor.composition import simulate_with_environment, convert_to_timeseries, plot_simulation_output

    out_dir = os.path.join('out', 'tests', 'glc_lct_shifter')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    boot_config = {'emitter': 'null'}
    compartment = load_compartment(compose_glc_lct_shifter, boot_config)

    # settings for simulation and plot
    options = compartment.configuration

    # define timeline
    # timeline = [
    #     (100, {})]

    timeline = [
        (0, {'environment': {
            'glc__D_e': 5.0,
            'lac__D_e': 5.0}
        }),
        (3000, {})]

    settings = {
        'environment_role': options['environment_role'],
        'exchange_role': options['exchange_role'],
        'environment_volume': 2e-13,  # L
        'timeline': timeline}

    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'overlay': {'reactions': 'flux'},
        'show_state': [
            ('environment', 'glc__D_e'),
            ('environment', 'lac__D_e'),
            ('reactions', 'GLCpts'),
            ('reactions', 'EX_glc__D_e'),
            ('reactions', 'EX_lac__D_e'),
            ('cell', 'g6p_c'),
            ('cell', 'PTSG'),
            ('cell', 'lac__D_c'),
            ('cell', 'lacy_RNA'),
            ('cell', 'LacY')],
        'skip_roles': ['prior_state', 'null']}

    # saved_state = simulate_compartment(compartment, settings)
    saved_data = simulate_with_environment(compartment, settings)
    del saved_data[0]
    timeseries = convert_to_timeseries(saved_data)
    plot_diauxic_shift(timeseries, settings, out_dir)
    plot_simulation_output(timeseries, plot_settings, out_dir)
