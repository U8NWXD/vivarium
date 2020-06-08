from __future__ import absolute_import, division, print_function

import os
import uuid

from vivarium.core.experiment import (
    generate_state,
    Experiment
)
from vivarium.core.composition import (
    make_agents,
    simulate_experiment,
)

from vivarium.processes.multibody_physics import plot_snapshots

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal


def lattice_experiment(config):
    # configure the experiment
    count = config.get('count')

    # get the environment
    environment = Lattice(config.get('environment', {}))
    network = environment.generate()
    processes = network['processes']
    topology = network['topology']

    # get the agents
    growth_division = GrowthDivisionMinimal({
        'agents_path': ('..', 'agents')})
    agents = make_agents(range(count), growth_division, {})
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'initial_state': config.get('initial_state', {})})



# configs
def get_lattice_config():
    bounds = [10, 10]
    n_bins = [10, 10]

    environment_config = {
        'multibody': {
            'bounds': bounds,
            'agents': {}
        },
        'diffusion': {
            'molecules': ['glc'],
            'n_bins': n_bins,
            'bounds': bounds,
            'depth': 3000.0,
            'diffusion': 1e-2,
        }
    }

    growth_division_config = {
        'agents_path': ('..', '..', 'agents'),
        'global_path': ('global',),
        'growth_rate': 0.03,
        'growth_rate_noise': 0.02,
        'division_volume': 2.6}

    return {
        'count': 3,
        'environment': environment_config,
        'agents': growth_division_config}

def run_lattice_experiment():
    config = get_lattice_config()
    experiment = lattice_experiment(config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': 100}
    data = simulate_experiment(experiment, settings)

    import ipdb;
    ipdb.set_trace()



if __name__ == '__main__':
    out_dir = os.path.join('out', 'tests', 'lattice_experiment')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_lattice_experiment()
