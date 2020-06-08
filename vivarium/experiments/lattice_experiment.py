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
    plot_agent_data,
    EXPERIMENT_OUT_DIR,
)

from vivarium.plots.multibody_physics import plot_snapshots

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal


NAME = 'lattice'


def lattice_experiment(config):
    # # configure the experiment
    count = config.get('count')

    emitter = config.get('emitter', {'type': 'timeseries'})

    # get the environment
    environment = Lattice(config.get('environment', {}))
    network = environment.generate()
    processes = network['processes']
    topology = network['topology']

    # get the agents
    agent_ids = [str(agent_id) for agent_id in range(count)]
    growth_division = GrowthDivisionMinimal(config.get('growth_division', {}))
    agents = make_agents(agent_ids, growth_division, {})
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'emitter': emitter,
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
        'total_time': 500,
        'return_raw_data': True}
    data = simulate_experiment(experiment, settings)


    # extract data
    multibody_config = config['environment']['multibody']
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}

    # agents plot
    plot_settings = {
        'agents_key': 'agents'}
    plot_agent_data(data, plot_settings, out_dir)

    # snapshot plot
    data = {
        'agents': agents,
        'fields': fields,
        'config': multibody_config}
    plot_config = {
        'out_dir': out_dir,
        'filename': 'snapshots'}
    plot_snapshots(data, plot_config)


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_lattice_experiment()
