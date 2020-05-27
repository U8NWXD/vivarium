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
    simulate_experiment
)

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision

# processes
from vivarium.processes.multibody_physics import plot_snapshots, mother_machine_body_config, volume_from_length
from vivarium.processes.diffusion_field import plot_field_output



def mother_machine_experiment(config):
    # configure the experiment
    n_agents = config.get('n_agents', 1)

    # get the environment
    environment = Lattice(config.get('environment', {}))
    processes = environment.generate_processes()
    topology = environment.generate_topology()

    # get the agents
    growth_division = GrowthDivision({'cells_path': ('..', 'agents')})
    agents = make_agents(range(n_agents), growth_division, config.get('growth_division', {}))
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'initial_state': config.get('initial_state', {})})



# configurations
def get_mother_machine_config():
    bounds = [30, 30]
    channel_height = 0.7 * bounds[1]
    channel_space = 1.5
    n_agents = 5
    # growth division agent
    growth_division_config = {
        'growth_rate': 0.03,
        'growth_rate_noise': 0.02,
        'division_volume': 2.6 }

    # environment
    multibody_config = {
        'animate': True,
        'mother_machine': {
            'channel_height': channel_height,
            'channel_space': channel_space},
        'jitter_force': 2e-2,
        'bounds': bounds}

    body_config = {
        'bounds': bounds,
        'channel_height': channel_height,
        'channel_space': channel_space,
        'n_agents': n_agents}
    multibody_config.update(mother_machine_body_config(body_config))

    return {
        'n_agents': n_agents,
        'growth_division': growth_division_config,
        'environment': {
            'multibody': multibody_config,
            'diffusion': {},
        }
    }

def run_mother_machine(time=10):
    mm_config = get_mother_machine_config()
    experiment = mother_machine_experiment(mm_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': time,
        'return_raw_data': True}
    data = simulate_experiment(experiment, settings)

    # make snapshot plot
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}
    plot_snapshots(agents, fields, config, out_dir, 'snapshots')


    import ipdb; ipdb.set_trace()
    # TODO -- did the mm_config get in there?
    # TODO -- get channel height, have multibody perform deletion




if __name__ == '__main__':
    out_dir = os.path.join('out', 'experiments', 'mother_machine')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_mother_machine()

    # make snapshot
    agents = {time: time_data['agents'] for time, time_data in mm_data.items()}
    fields = {}
    plot_snapshots(agents, fields, mm_config, out_dir, 'mother_machine_snapshots')