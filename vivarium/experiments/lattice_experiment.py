from __future__ import absolute_import, division, print_function

import os
import sys
import uuid
import argparse

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
    # configure the experiment
    n_agents = config.get('n_agents')
    emitter = config.get('emitter', {'type': 'timeseries'})

    # make lattice environment
    environment = Lattice(config.get('environment', {}))
    network = environment.generate()
    processes = network['processes']
    topology = network['topology']

    # add the agents
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]
    agent_config = config['agent']
    agent_compartment = agent_config['compartment']
    compartment_config = agent_config['config']
    agent = agent_compartment(compartment_config)
    agents = make_agents(agent_ids, agent, {})
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'emitter': emitter,
        'initial_state': config.get('initial_state', {})})



# configs
def get_gd_config():
    return {
        'compartment': GrowthDivision,
        'config': {
            'agents_path': ('..', '..', 'agents'),
        }
    }

def get_gd_minimal_config():
    return {
        'compartment': GrowthDivisionMinimal,
        'config': {
            'agents_path': ('..', '..', 'agents'),
            'growth_rate': 0.03,
            'growth_rate_noise': 0.02,
            'division_volume': 2.6
        }
    }

def get_lattice_config():
    bounds = [10, 10]
    n_bins = [10, 10]
    molecules = ['glc__D_e', 'lcts_e']

    environment_config = {
        'multibody': {
            'bounds': bounds,
            'agents': {}
        },
        'diffusion': {
            'molecules': molecules,
            'n_bins': n_bins,
            'bounds': bounds,
            'depth': 3000.0,
            'diffusion': 1e-2,
        }
    }
    return {
        'environment': environment_config}

def run_lattice_experiment(agent_config=get_gd_minimal_config):
    n_agents = 1

    experiment_config = get_lattice_config()
    experiment_config['n_agents'] = n_agents
    experiment_config['agent'] = agent_config()
    experiment = lattice_experiment(experiment_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': 200,
        'return_raw_data': True}
    data = simulate_experiment(experiment, settings)

    # extract data
    multibody_config = experiment_config['environment']['multibody']
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

    parser = argparse.ArgumentParser(description='lattice_experiment')
    parser.add_argument('--gd', '-g', action='store_true', default=False)
    parser.add_argument('--gd_minimal', '-m', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.gd_minimal or no_args:
        run_lattice_experiment(get_gd_minimal_config)
    elif args.gd:
        run_lattice_experiment(get_gd_config)
