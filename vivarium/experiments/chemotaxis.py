from __future__ import absolute_import, division, print_function

import os
import sys
import uuid
import argparse
import copy

from vivarium.core.emitter import timeseries_from_data
from vivarium.library.dict_utils import deep_merge
from vivarium.core.experiment import (
    generate_state,
    Experiment
)
from vivarium.core.composition import (
    agent_environment_experiment,
    make_agents,
    simulate_experiment,
    plot_agents_multigen,
    process_in_compartment,
    EXPERIMENT_OUT_DIR,
)

# compartments
from vivarium.compartments.static_lattice import StaticLattice
from vivarium.compartments.chemotaxis_minimal import ChemotaxisMinimal
from vivarium.compartments.chemotaxis_master import ChemotaxisMaster
from vivarium.compartments.chemotaxis_variable_flagella import ChemotaxisVariableFlagella

# processes
from vivarium.processes.Vladimirov2008_motor import MotorActivity
from vivarium.processes.multibody_physics import agent_body_config
from vivarium.plots.multibody_physics import (
    plot_temporal_trajectory,
    plot_agent_trajectory,
    plot_motility,
)
from vivarium.processes.static_field import make_field


# make an agent from a lone MotorActivity process
MotorActivityAgent = process_in_compartment(
    MotorActivity,
    paths={
        'external': ('boundary',),
        'internal': ('cell',)
    })


DEFAULT_BOUNDS = [1000, 5000]
DEFAULT_AGENT_LOCATION = [0.5, 0.1]
DEFAULT_LIGAND_ID = 'MeAsp'
DEFAULT_INITIAL_LIGAND = 25.0
DEFAULT_ENVIRONMENT_TYPE = StaticLattice


def get_environment_config():
    # field parameters
    field_scale = 1.0
    exponential_base = 2e2
    field_center = [0.5, 0.0]

    # multibody process config
    multibody_config = {
        'animate': False,
        'jitter_force': 5e-4,
        'bounds': DEFAULT_BOUNDS}

    # static field config
    field_config = {
        'molecules': [DEFAULT_LIGAND_ID],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                DEFAULT_LIGAND_ID: {
                    'center': field_center,
                    'scale': field_scale,
                    'base': exponential_base}}},
        'bounds': DEFAULT_BOUNDS}

    return {
        'multibody': multibody_config,
        'field': field_config}

DEFAULT_ENVIRONMENT_CONFIG = {
    'type': DEFAULT_ENVIRONMENT_TYPE,
    'config': get_environment_config()
}

DEFAULT_AGENT_CONFIG = {
    'ligand_id': DEFAULT_LIGAND_ID,
    'initial_ligand': DEFAULT_INITIAL_LIGAND,
    'external_path': ('global',),
    'agents_path': ('..', '..', 'agents')
}


# run the simulation
def run_chemotaxis_experiment(
    agents_config=None,
    environment_config=None,
    initial_state=None,
    simulation_settings=None,
    experiment_settings=None):

    if not initial_state:
        initial_state = {}
    if not experiment_settings:
        experiment_settings = {}

    total_time = simulation_settings['total_time']
    timestep = simulation_settings['timestep']

    # agents ids
    agent_ids = []
    for config in agents_config:
        number = config['number']
        if 'name' in config:
            name = config['name']
            if number > 1:
                new_agent_ids = [name + '_' + str(num) for num in range(number)]
            else:
                new_agent_ids = [name]
        else:
            new_agent_ids = [str(uuid.uuid1()) for num in range(number)]
        config['ids'] = new_agent_ids
        agent_ids.extend(new_agent_ids)

    initial_agent_body = agent_body_config({
        'bounds': DEFAULT_BOUNDS,
        'agent_ids': agent_ids,
        'location': DEFAULT_AGENT_LOCATION})
    initial_state.update(initial_agent_body)

    # make the experiment
    experiment = agent_environment_experiment(
        agents_config,
        environment_config,
        initial_state,
        experiment_settings)

    # simulate
    settings = {
        'total_time': total_time,
        'timestep': timestep,
        'return_raw_data': True}
    return simulate_experiment(experiment, settings)


def run_mixed(out_dir='out'):
    total_time = 720
    timestep = 0.1

    # configure
    agents_config = [
        {
            'type': ChemotaxisMinimal,
            'name': 'motor_receptor',
            'number': 1,
            'config': DEFAULT_AGENT_CONFIG
        },
        {
            'type': MotorActivityAgent,
            'name': 'motor',
            'number': 1,
            'config': DEFAULT_AGENT_CONFIG
        }
    ]

    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config()
    }

    simulation_settings = {
        'total_time': total_time,
        'timestep': timestep
    }

    # simulate
    data = run_chemotaxis_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, out_dir)


def run_variable(out_dir='out'):
    total_time = 720
    timestep = 0.1

    flagella_numbers = [0, 3, 6, 9, 12]

    baseline_agent_config = {
        'number': 1,
        'type': ChemotaxisVariableFlagella,
        'config': DEFAULT_AGENT_CONFIG
    }

    # configure
    agents_config = []
    for n_flagella in flagella_numbers:
        agent_config = copy.deepcopy(baseline_agent_config)
        agent_config['name'] = '{}_flagella'.format(n_flagella)
        agent_config['config'].update({'n_flagella': n_flagella})
        agents_config.append(agent_config)

    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config()}

    simulation_settings = {
        'total_time': total_time,
        'timestep': timestep}

    # simulate
    data = run_chemotaxis_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, out_dir)


def run_minimal(out_dir='out'):
    total_time = 30
    timestep = 0.1

    # configure
    agents_config = [
        {
            'number': 6,
            'name': 'minimal',
            'type': ChemotaxisMinimal,
            'config': DEFAULT_AGENT_CONFIG,
        }
    ]

    simulation_settings = {
        'total_time': total_time,
        'timestep': timestep}

    data = run_chemotaxis_experiment(
        agents_config=agents_config,
        environment_config=DEFAULT_ENVIRONMENT_CONFIG,
        simulation_settings=simulation_settings
    )

    # plot
    field_config = DEFAULT_ENVIRONMENT_CONFIG['config']['field']
    plot_chemotaxis_experiment(data, field_config, out_dir)


def run_master(out_dir='out'):
    # TODO -- master requires environment for metabolism external

    agent_type = ChemotaxisMaster
    total_time = 30
    timestep = 0.1

    # configure
    agents_config = [
        {
            'number': 1,
            'name': 'master',
            'type': agent_type,
            'config': DEFAULT_AGENT_CONFIG
        }
    ]

    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config(),
    }

    simulation_settings = {
        'total_time': total_time,
        'timestep': timestep,
    }

    # simulate
    data = run_chemotaxis_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, out_dir)


def plot_chemotaxis_experiment(
        data,
        field_config,
        out_dir):

    # multigen agents plot
    plot_settings = {
        'agents_key': 'agents',
        'max_rows': 30,
        'skip_paths': [
            ('boundary', 'mass'),
            ('boundary', 'length'),
            ('boundary', 'width'),
            ('boundary', 'location'),
        ]}
    plot_agents_multigen(data, plot_settings, out_dir, 'agents')

    # trajectory and motility
    agents_timeseries = timeseries_from_data(data)
    field = make_field(field_config)
    trajectory_config = {
        'bounds': field_config['bounds'],
        'field': field,
        'rotate_90': True}

    plot_temporal_trajectory(copy.deepcopy(agents_timeseries), trajectory_config, out_dir, 'temporal')
    plot_agent_trajectory(agents_timeseries, trajectory_config, out_dir, 'trajectory')
    try:
        plot_motility(agents_timeseries, out_dir, 'motility_analysis')
    except:
        print('plot_motility failed')


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis')
    make_dir(out_dir)

    parser = argparse.ArgumentParser(description='multibody')
    parser.add_argument('--minimal', '-n', action='store_true', default=False)
    parser.add_argument('--master', '-m', action='store_true', default=False)
    parser.add_argument('--variable', '-v', action='store_true', default=False)
    parser.add_argument('--mixed', '-x', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.minimal or no_args:
        minimal_out_dir = os.path.join(out_dir, 'minimal')
        make_dir(minimal_out_dir)
        run_minimal(minimal_out_dir)
    elif args.master:
        master_out_dir = os.path.join(out_dir, 'master')
        make_dir(master_out_dir)
        run_master(master_out_dir)
    elif args.variable:
        variable_out_dir = os.path.join(out_dir, 'variable')
        make_dir(variable_out_dir)
        run_variable(variable_out_dir)
    elif args.mixed:
        mixed_out_dir = os.path.join(out_dir, 'mixed')
        make_dir(mixed_out_dir)
        run_mixed(mixed_out_dir)
