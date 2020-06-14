from __future__ import absolute_import, division, print_function

import os
import uuid

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
from vivarium.compartments.chemotaxis_minimal import (
    ChemotaxisMinimal,
    get_chemotaxis_config
)

# processes
from vivarium.processes.multibody_physics import (
    agent_body_config,
)
from vivarium.plots.multibody_physics import plot_trajectory, plot_motility
from vivarium.processes.static_field import make_field


def make_chemotaxis_experiment(config={}):
    # configure the experiment
    agent_ids = config.get('agent_ids', [])
    emitter = config.get('emitter', {'type': 'timeseries'})

    # initialize the environment
    env_config = config.get('environment', {})
    environment = StaticLattice(env_config)
    network = environment.generate({})
    processes = network['processes']
    topology = network['topology']

    chemotaxis = ChemotaxisMinimal(config.get('chemotaxis', {}))
    agents = make_agents(agent_ids, chemotaxis, config.get('chemotaxis', {}))
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'emitter': emitter,
        'initial_state': config.get('initial_state', {})})



def get_chemotaxis_experiment_config():
    # agent parameters
    n_agents = 1
    ligand_id = 'glc'
    initial_ligand = 2.0

    # environment parameters
    initial_location = [0.5, 0.1]
    bounds = [400, 2000]

    # field parameters
    field_scale = 1.0
    exponential_base = 2e2
    field_center = [0.5, 0.0]

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
        'initial_state': initial_agents_state,
        'agent_ids': agent_ids,
        'chemotaxis': chemotaxis_config,
        'environment': {
            'multibody': multibody_config,
            'field': field_config}}

def simulate_chemotaxis_experiment(out_dir='out'):
    total_time = 360
    timestep = 0.01

    chemotaxis_config = get_chemotaxis_experiment_config()
    experiment = make_chemotaxis_experiment(chemotaxis_config)

    # simulate
    settings = {
        'total_time': total_time,
        'timestep': timestep,
        'return_raw_data': True}
    raw_data = simulate_experiment(experiment, settings)

    # agents plot
    plot_settings = {
        'agents_key': 'agents',
        'skip_paths': [
            ('boundary', 'mass'),
            ('boundary', 'length'),
            ('boundary', 'width'),
            ('boundary', 'location'),
            ('cell', 'CheA'),
            ('cell', 'CheB'),
            ('cell', 'CheR'),
        ]}
    plot_agents_multigen(raw_data, plot_settings, out_dir)

    # trajectory and motility plots
    # get a sample field
    field_config = chemotaxis_config['environment']['field']
    field = make_field(field_config)
    agents_timeseries = timeseries_from_data(raw_data)
    trajectory_config = {
        'bounds': chemotaxis_config['environment']['multibody']['bounds'],
        'field': field}

    plot_motility(agents_timeseries, out_dir)
    plot_trajectory(agents_timeseries, trajectory_config, out_dir)


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis_minimal')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    simulate_chemotaxis_experiment(out_dir)
