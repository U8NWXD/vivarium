from __future__ import absolute_import, division, print_function

import os
import sys
import uuid
import argparse

from vivarium.core.emitter import timeseries_from_data
from vivarium.core.experiment import (
    generate_state,
    Experiment)
from vivarium.core.composition import (
    make_agents,
    simulate_experiment,
    plot_agents_multigen,
    EXPERIMENT_OUT_DIR,
)

# compartments
from vivarium.compartments.static_lattice import StaticLattice
from vivarium.compartments.chemotaxis_minimal import ChemotaxisMinimal
from vivarium.compartments.chemotaxis_master import ChemotaxisMaster

# processes
from vivarium.processes.multibody_physics import (
    agent_body_config,
)
from vivarium.plots.multibody_physics import plot_trajectory, plot_motility
from vivarium.processes.static_field import make_field


def make_chemotaxis_experiment(
        agents_config={},
        environment_config={},
        initial_state={},
        settings={}):

    # experiment settings
    emitter = settings.get('emitter', {'type': 'timeseries'})

    # initialize the agents
    agent_type = agents_config['agent_type']
    agent_ids = agents_config['agent_ids']
    chemotaxis_config = agents_config['chemotaxis_config']
    chemotaxis_agent = agent_type(chemotaxis_config)
    agents = make_agents(agent_ids, chemotaxis_agent, chemotaxis_config)

    # initialize the environment
    environment = StaticLattice(environment_config)

    # combine processes and topologies
    network = environment.generate({})
    processes = network['processes']
    topology = network['topology']
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'emitter': emitter,
        'initial_state': initial_state})


def get_environment_config(config={}):
    ligand_id = config.get('ligand_id', 'glc')
    bounds = config.get('bounds', [400, 2000])

    # field parameters
    field_scale = 1.0
    exponential_base = 2e2
    field_center = [0.5, 0.0]

    # multibody process config
    multibody_config = {
        'animate': False,
        'jitter_force': 0.0,
        'bounds': bounds}

    # static field config
    field_config = {
        'molecules': [ligand_id],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                ligand_id: {
                    'center': field_center,
                    'scale': field_scale,
                    'base': exponential_base}}},
        'bounds': bounds}

    return {
        'multibody': multibody_config,
        'field': field_config}


def get_chemotaxis_config(config={}):
    # agent parameters
    n_agents = config.get('n_agents', 1)
    agent_type = config.get('agent_type', ChemotaxisMinimal)
    ligand_id = config.get('ligand_id', 'glc')
    initial_ligand = config.get('initial_ligand', 2.0)
    initial_location = config.get('initial_location', [0.5, 0.1])
    bounds = config.get('bounds', [400, 2000])

    # agents initial state
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]
    initial_agents_state = agent_body_config({
        'bounds': bounds,
        'agent_ids': agent_ids,
        'location': initial_location})

    # chemotaxis_minimal compartment config
    chemotaxis_config = {
        'ligand_id': ligand_id,
        'initial_ligand': initial_ligand,
        'external_path': ('global',),
        'agents_path': ('..', '..', 'agents')}

    return {
        'initial_state': initial_agents_state,
        'agent_type': agent_type,
        'agent_ids': agent_ids,
        'chemotaxis_config': chemotaxis_config}


def simulate_chemotaxis_experiment(config={}):
    agent_config = config['agents']
    environment_config = config['environment']
    initial_state = config['initial_state']
    simulation_settings = config['simulation']

    # configure the experiment
    experiment_settings = {}
    experiment = make_chemotaxis_experiment(
        agent_config,
        environment_config,
        initial_state,
        experiment_settings)

    # simulate
    settings = {
        'total_time': simulation_settings['total_time'],
        'timestep': simulation_settings['timestep'],
        'return_raw_data': True}
    return simulate_experiment(experiment, settings)


def run_minimal():
    filename = 'minimal'

    n_agents = 2
    total_time = 360
    timestep = 0.1

    ## configure and run the experiment
    agents_config = get_chemotaxis_config({
        'n_agents': n_agents,
        'agent_type': ChemotaxisMinimal,
        'agent_config': {}})
    environment_config = get_environment_config()
    config = {
        'agents': agents_config,
        'environment': environment_config,
        'initial_state': agents_config['initial_state'],
        'simulation': {
            'total_time': total_time,
            'timestep': timestep}}
    # run experiment and get the data
    data = simulate_chemotaxis_experiment(config)

    ## plots
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
    plot_agents_multigen(data, plot_settings, out_dir, filename + '_agents')

    # trajectory and motility
    agents_timeseries = timeseries_from_data(data)
    field_config = config['environment']['field']
    field = make_field(field_config)
    trajectory_config = {
        'bounds': field_config['bounds'],
        'field': field}

    plot_trajectory(agents_timeseries, trajectory_config, out_dir, filename + '_trajectory')
    plot_motility(agents_timeseries, out_dir, filename + '_motility_analysis')


def run_master():
    filename = 'master'
    n_agents = 1
    total_time = 30
    timestep = 0.1

    # configure and run the experiment
    agents_config = get_chemotaxis_config({
        'n_agents': n_agents,
        'agent_type': ChemotaxisMaster,
        'agent_config': {}})
    environment_config = get_environment_config()
    config = {
        'agents': agents_config,
        'environment': environment_config,
        'initial_state': agents_config['initial_state'],
        'simulation': {
            'total_time': total_time,
            'timestep': timestep}}
    data = simulate_chemotaxis_experiment(config)

    ## plots
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
    plot_agents_multigen(data, plot_settings, out_dir, filename + '_agents')

    # trajectory
    agents_timeseries = timeseries_from_data(data)
    field_config = config['environment']['field']
    field = make_field(field_config)
    trajectory_config = {
        'bounds': field_config['bounds'],
        'field': field}

    plot_trajectory(agents_timeseries, trajectory_config, out_dir, filename + '_trajectory')


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='multibody')
    parser.add_argument('--minimal', '-m', action='store_true', default=False)
    parser.add_argument('--master', '-x', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.minimal or no_args:
        run_minimal()
    if args.master:
        run_master()
        