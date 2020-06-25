from __future__ import absolute_import, division, print_function

import os

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    compartment_in_experiment,
    COMPARTMENT_OUT_DIR,
)

# processes
from vivarium.processes.multibody_physics import (
    Multibody,
    agent_body_config,
)
from vivarium.plots.multibody_physics import plot_snapshots
from vivarium.processes.diffusion_field import (
    DiffusionField,
    get_gaussian_config,
)


NAME = 'lattice'


class Lattice(Compartment):
    """
    Lattice:  A two-dimensional lattice environmental model with multibody physics and diffusing molecular fields.
    """

    defaults = {
        'config': {
            'multibody': {
                'bounds': [10, 10],
                'size': [10, 10],
                'agents': {}
            },
            'diffusion': {
                'molecules': ['glc'],
                'n_bins': [10, 10],
                'size': [10, 10],
                'depth': 3000.0,
                'diffusion': 1e-2,
            }
        }
    }

    def __init__(self, config=None):
        if config is None or not bool(config):
            config = self.defaults['config']
        self.config = config

    def generate_processes(self, config):
        return {
            'multibody': Multibody(config['multibody']),
            'diffusion': DiffusionField(config['diffusion'])}

    def generate_topology(self, config):
        return {
            'multibody': {
                'agents': ('agents',)},
            'diffusion': {
                'agents': ('agents',),
                'fields': ('fields',)}}


def get_lattice_config(config={}):
    bounds = config.get('bounds', [25, 25])
    molecules = config.get('molecules', ['glc'])
    n_bins = config.get('n_bins', tuple(bounds))
    center = config.get('center', [0.5, 0.5])
    deviation = config.get('deviation', 5)
    diffusion = config.get('diffusion', 1e0)
    n_agents = config.get('n_agents', 1)
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]

    # multibody config
    mbp_config = {
        # 'animate': True,
        'jitter_force': 1e2,
        'bounds': bounds}
    body_config = {
        'bounds': bounds,
        'agent_ids': agent_ids}
    mbp_config.update(agent_body_config(body_config))

    # diffusion config
    dff_config = get_gaussian_config({
        'molecules': molecules,
        'n_bins': n_bins,
        'bounds': bounds,
        'diffusion': diffusion,
        'center': center,
        'deviation': deviation})

    return {
        'bounds': bounds,
        'multibody': mbp_config,
        'diffusion': dff_config}

def test_lattice(config=get_lattice_config(), end_time=10):

    # configure the compartment
    compartment = Lattice(config)

    # configure experiment
    experiment_settings = {
        'compartment': config}
    experiment = compartment_in_experiment(
        compartment,
        experiment_settings)

    # run experiment
    timestep = 1
    time = 0
    while time < end_time:
        experiment.update(timestep)
        time += timestep
    return experiment.emitter.get_data()



if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    config = get_lattice_config()
    data = test_lattice(config, 40)

    # make snapshot plot
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}
    data = {
        'agents': agents,
        'fields': fields,
        'config': config}
    plot_config = {
        'out_dir': out_dir,
        'filename': 'snapshots'}
    plot_snapshots(data, plot_config)
