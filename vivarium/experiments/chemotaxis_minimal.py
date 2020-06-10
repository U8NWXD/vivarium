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
        'initial_state': config.get('initial_state', {})
    })



# configurations
def get_chemotaxis_experiment_config():
    ligand_id = 'glc'
    initial_ligand = 1e-1
    bounds = [100, 500]
    n_agents = 1
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]

    ## minimal chemotaxis agent
    chemotaxis_config = {
        'ligand_id': ligand_id,
        'initial_ligand': initial_ligand,
        'external_path': ('global',),
        'agents_path': ('..', '..', 'agents')}

    ## environment
    # multibody
    multibody_config = {
        'animate': False,
        'jitter_force': 1e-3,
        'bounds': bounds}

    body_config = {
        'bounds': bounds,
        'agent_ids': agent_ids,
        'location': [0.5, 0.0]}
    multibody_config.update(agent_body_config(body_config))

    # field
    field_config = {
        'molecules': [ligand_id],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                ligand_id: {
                    'center': [0.5, 0.0],
                    'scale': initial_ligand,
                    'base': 0.1}}},
        'size': bounds}

    return {
        'agent_ids': agent_ids,
        'chemotaxis': chemotaxis_config,
        'environment': {
            'multibody': multibody_config,
            'field': field_config}}

def run_chemotaxis_experiment(out_dir='out'):
    chemotaxis_config = get_chemotaxis_experiment_config()
    experiment = make_chemotaxis_experiment(chemotaxis_config)

    # simulate
    settings = {
        'total_time': 30,
        'timestep': 0.01,
        'return_raw_data': True}
    raw_data = simulate_experiment(experiment, settings)

    # agents plot
    plot_settings = {
        'agents_key': 'agents'}
    plot_agents_multigen(raw_data, plot_settings, out_dir)

    # trajectory and motility plots
    agents_timeseries = timeseries_from_data(raw_data)
    trajectory_config = {'bounds': chemotaxis_config['environment']['multibody']['bounds']}

    plot_motility(agents_timeseries, out_dir)
    plot_trajectory(agents_timeseries, trajectory_config, out_dir)


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis_minimal')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_chemotaxis_experiment(out_dir)
