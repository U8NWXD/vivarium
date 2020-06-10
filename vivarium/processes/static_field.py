from __future__ import absolute_import, division, print_function

import sys
import os
import argparse

import numpy as np
from scipy import constants
from scipy.ndimage import convolve
import matplotlib.pyplot as plt

from vivarium.core.process import Deriver
from vivarium.core.composition import (
    simulate_process,
    PROCESS_OUT_DIR
)

from vivarium.plots.multibody_physics import plot_snapshots
from vivarium.processes.diffusion_field import plot_fields


NAME = 'static_field'


class StaticField(Deriver):

    defaults = {
        'molecules': ['glc'],
        'initial_state': {},
        'n_bins': [10, 10],
        'bounds': [10, 10],
        'gradient': {},
        'agents': {},
        'boundary_port': 'boundary',
        'external_key': 'external',
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        # initial state
        self.molecules = self.or_default(
            initial_parameters, 'molecules')
        self.initial_state = self.or_default(
            initial_parameters, 'initial_state')

        # parameters
        self.bounds = self.or_default(
            initial_parameters, 'bounds')
        self.boundary_port = self.or_default(
            initial_parameters, 'boundary_port')
        self.external_key = self.or_default(
            initial_parameters, 'external_key')

        # initialize gradient fields
        self.gradient = initial_parameters.get('gradient', self.defaults['gradient'])

        # agents
        self.initial_agents = initial_parameters.get('agents', self.defaults['agents'])

        # make ports
        ports = {'agents': ['*']}

        parameters = {}
        parameters.update(initial_parameters)

        super(StaticField, self).__init__(ports, parameters)

    def ports_schema(self):
        local_concentration_schema = {
            molecule: {
                '_default': 0.0,
                '_updater': 'set'}
            for molecule in self.molecules}

        schema = {}
        glob_schema = {
            '*': {
                self.boundary_port: {
                    'location': {
                        '_default': [0.5, 0.5],
                        '_updater': 'set'},
                    # 'exchange': local_concentration_schema,
                    self.external_key: local_concentration_schema}}}
        schema['agents'] = glob_schema
        return schema

    def next_update(self, timestep, states):
        agents = states['agents']

        # get each agent's local environment
        local_environments = {}
        for agent_id, state in agents.items():
            location = state[self.boundary_port]['location']
            local_environments[agent_id] = {
                self.boundary_port: {
                    self.external_key: self.get_concentration(location)}}

        return {'agents': local_environments}

    def get_concentration(self, location):
        concentrations = {}
        if self.gradient['type'] == 'gaussian':
            import ipdb;
            ipdb.set_trace()
            for molecule_id, specs in self.gradient['molecules'].items():
                deviation = specs['deviation']
                dx = location[0] - specs['center'][0] * self.bounds[0]
                dy = location[1] - specs['center'][1] * self.bounds[1]
                distance = np.sqrt(dx ** 2 + dy ** 2)
                concentrations[molecule_id] = gaussian(deviation, distance)

        elif self.gradient['type'] == 'linear':
            for molecule_id, specs in self.gradient['molecules'].items():
                slope = specs['slope']
                base = specs.get('base', 0.0)
                dx = location[0] - specs['center'][0] * self.bounds[0]
                dy = location[1] - specs['center'][1] * self.bounds[1]
                distance = np.sqrt(dx ** 2 + dy ** 2)
                concentrations[molecule_id] = base + slope * distance

        elif self.gradient['type'] == 'exponential':
            for molecule_id, specs in self.gradient['molecules'].items():
                base = specs['base']
                scale = specs.get('scale', 1)
                dx = location[0] - specs['center'][0] * self.bounds[0]
                dy = location[1] - specs['center'][1] * self.bounds[1]
                distance = np.sqrt(dx ** 2 + dy ** 2)
                concentrations[molecule_id] = scale * base ** (distance/1000)

        return concentrations


def get_exponential_config(bounds, center, molecule):
    scale = 1
    base = 0.1
    return {
        'bounds': bounds,
        'molecules': [molecule],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                molecule: {
                    'center': center,
                    'scale': scale,
                    'base': base}}}}

def make_field():
    molecule = 'glc'
    center = [0.1, 0.5]
    bins_per_micron = 1
    bounds = [20, 30]
    n_bins = [bound*bins_per_micron for bound in bounds]

    config = get_exponential_config(bounds, center, molecule)
    process = StaticField(config)

    field = np.zeros((n_bins[0], n_bins[1]), dtype=np.float64)
    for x in range(n_bins[0]):
        for y in range(n_bins[1]):
            location = [x/bins_per_micron, y/bins_per_micron]
            concentration = process.get_concentration(location)
            field[x,y] = concentration[molecule]
    return field

def plot_field(field, out_dir='out'):
    field = np.transpose(field)
    shape = field.shape
    fig = plt.figure()
    im = plt.imshow(field,
                    origin='lower',
                    extent=[0, shape[1], 0, shape[0]],
                    # vmin=vmin,
                    # vmax=vmax,
                    cmap='BuPu')

    fig_path = os.path.join(out_dir, 'field')
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    field = make_field()
    plot_field(field, out_dir)
    