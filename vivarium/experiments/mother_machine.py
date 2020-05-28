from __future__ import absolute_import, division, print_function

import os
import uuid
import math
import random

from vivarium.core.tree import (
    generate_state,
    Experiment
)
from vivarium.core.composition import (
    make_agents,
    simulate_experiment,
    plot_agent_data
)

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal

# processes
from vivarium.processes.multibody_physics import (
    plot_snapshots,
    mother_machine_body_config,
    volume_from_length)



def mother_machine_experiment(config):
    # configure the experiment
    agent_ids = config.get('agent_ids', [])
    emitter = config.get('emitter', {'type': 'timeseries'})

    # get the environment
    environment = Lattice(config.get('environment', {}))
    network = environment.generate({})
    processes = network['processes']
    topology = network['topology']

    # get the agents
    growth_division = GrowthDivisionMinimal({'agents_path': ('..', 'agents')})
    agents = make_agents(agent_ids, growth_division, config.get('growth_division', {}))
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'initial_state': config.get('initial_state', {}),
        'emitter': emitter,
    })



# configurations
def get_mother_machine_config():
    bounds = [10, 10]
    n_bins = [10, 10]
    channel_height = 0.7 * bounds[1]
    channel_space = 1.5
    n_agents = 1

    agent_ids = [str(agent_id) for agent_id in range(n_agents)]

    ## growth division agent
    growth_division_config = {
        'agents_path': ('..', '..', 'agents'),
        'global_path': ('global',),
        'growth_rate': 0.03,
        'growth_rate_noise': 0.02,
        'division_volume': 2.6}

    ## environment
    # multibody
    multibody_config = {
        'animate': False,
        'mother_machine': {
            'channel_height': channel_height,
            'channel_space': channel_space},
        'jitter_force': 0,
        'bounds': bounds}

    body_config = {
        'bounds': bounds,
        'channel_height': channel_height,
        'channel_space': channel_space,
        'agent_ids': agent_ids}
    multibody_config.update(mother_machine_body_config(body_config))

    # diffusion
    diffusion_config = {
        'molecules': ['glc'],
        'gradient': {
            'type': 'gaussian',
            'molecules': {
                'glc':{
                    'center': [0.5, 0.5],
                    'deviation': 3},
            }},
        'diffusion': 1e-1,
        'n_bins': n_bins,
        'size': bounds}

    return {
        'agent_ids': agent_ids,
        'growth_division': growth_division_config,
        'environment': {
            'multibody': multibody_config,
            'diffusion': diffusion_config}}

def run_mother_machine(time=5, out_dir='out'):
    mm_config = get_mother_machine_config()
    experiment = mother_machine_experiment(mm_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': time,
        'return_raw_data': True}
    data = simulate_experiment(experiment, settings)

    # agents plot
    plot_settings = {
        'agents_key': 'agents'}
    plot_agent_data(data, plot_settings, out_dir)

    # snapshot plot
    multibody_config = mm_config['environment']['multibody']
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
    out_dir = os.path.join('out', 'experiments', 'mother_machine')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_mother_machine(500, out_dir)
