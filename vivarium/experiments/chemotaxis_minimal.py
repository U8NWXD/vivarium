from __future__ import absolute_import, division, print_function

import os
import uuid

from vivarium.core.experiment import (
    generate_state,
    Experiment)
from vivarium.core.composition import (
    make_agents,
    simulate_experiment,
    plot_agent_data,
    EXPERIMENT_OUT_DIR,
)

# compartments
from vivarium.compartments.lattice import (
    Lattice,
    get_lattice_config
)
from vivarium.compartments.chemotaxis_minimal import (
    ChemotaxisMinimal,
    get_chemotaxis_config
)

# processes
from vivarium.processes.multibody_physics import (
    plot_snapshots,
    random_body_config
)



def make_chemotaxis_experiment(config={}):
    # configure the experiment
    agent_ids = config.get('agent_ids', [])
    emitter = config.get('emitter', {'type': 'timeseries'})

    # get the environment
    env_config = config.get('environment', {})
    environment = Lattice(env_config)
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
    initial_ligand = 0.1
    n_agents = 3
    bounds = [50, 50]
    n_bins = [50, 50]

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
        'agent_ids': agent_ids}
    multibody_config.update(random_body_config(body_config))

    # diffusion
    diffusion_config = {
        'molecules': [ligand_id],
        'gradient': {
            'type': 'gaussian',
            'molecules': {
                ligand_id: {
                    'center': [0.5, 0.5],
                    'deviation': 15},
            }},
        'diffusion': 1e-1,
        'n_bins': n_bins,
        'size': bounds}

    return {
        'agent_ids': agent_ids,
        'chemotaxis': chemotaxis_config,
        'environment': {
            'multibody': multibody_config,
            'diffusion': diffusion_config}}

def run_chemotaxis_experiment(time=5, out_dir='out'):
    chemotaxis_config = get_chemotaxis_experiment_config()
    experiment = make_chemotaxis_experiment(chemotaxis_config)

    # simulate
    settings = {
        'timestep': 0.1,
        'total_time': time,
        'return_raw_data': True}
    data = simulate_experiment(experiment, settings)

    # agents plot
    plot_settings = {
        'agents_key': 'agents'}
    plot_agent_data(data, plot_settings, out_dir)

    # snapshot plot
    multibody_config = chemotaxis_config['environment']['multibody']
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}
    data = {
        'agents': agents,
        'fields': fields,
        'config': multibody_config}
    plot_config = {
        'out_dir': out_dir,
        'filename': 'snapshots'}
    plot_snapshots(data, plot_config)



if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'minimal_chemotaxis')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_chemotaxis_experiment(30, out_dir)
