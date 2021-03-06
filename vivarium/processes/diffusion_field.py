from __future__ import absolute_import, division, print_function

import sys
import os
import argparse

import numpy as np
from scipy import constants
from scipy.ndimage import convolve
import matplotlib.pyplot as plt

from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process,
    PROCESS_OUT_DIR
)

from vivarium.plots.multibody_physics import plot_snapshots

NAME = 'diffusion_field'

# laplacian kernel for diffusion
LAPLACIAN_2D = np.array([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]])
AVOGADRO = constants.N_A


def gaussian(deviation, distance):
    return np.exp(-np.power(distance, 2.) / (2 * np.power(deviation, 2.)))

def make_gradient(gradient, n_bins, size):
    bins_x = n_bins[0]
    bins_y = n_bins[1]
    length_x = size[0]
    length_y = size[1]
    fields = {}

    if gradient.get('type') == 'gaussian':
        """
        gaussian gradient multiplies the base concentration of the given molecule
        by a gaussian function of distance from center and deviation. Distance is
        scaled by 1/1000 from microns to millimeters.

        'gradient': {
            'type': 'gaussian',
            'molecules': {
                'mol_id1':{
                    'center': [0.25, 0.5],
                    'deviation': 30},
                'mol_id2': {
                    'center': [0.75, 0.5],
                    'deviation': 30}
            }},
        """

        for molecule_id, specs in gradient['molecules'].items():
            field = np.ones((bins_x, bins_y), dtype=np.float64)
            center = [specs['center'][0] * length_x,
                      specs['center'][1] * length_y]
            deviation = specs['deviation']

            for x_bin in range(bins_x):
                for y_bin in range(bins_y):
                    # distance from middle of bin to center coordinates
                    dx = (x_bin + 0.5) * length_x / bins_x - center[0]
                    dy = (y_bin + 0.5) * length_y / bins_y - center[1]
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    scale = gaussian(deviation, (distance/1000))
                    # multiply gradient by scale
                    field[x_bin][y_bin] *= scale
            fields[molecule_id] = field

    elif gradient.get('type') == 'linear':
        """
        linear gradient sets a site's concentration (c) of the given molecule
        as a function of distance (d) from center and slope (b), and base
        concentration (a). Distance is scaled by 1/1000 from microns to
        millimeters.

        c = a + b * d

        'gradient': {
            'type': 'linear',
            'molecules': {
                'mol_id1':{
                    'center': [0.0, 0.0],
                    'base': 0.1,
                    'slope': -10},
                'mol_id2': {
                    'center': [1.0, 1.0],
                    'base': 0.1,
                    'slope': -5}
            }},
        """

        for molecule_id, specs in gradient['molecules'].items():
            field = np.zeros((bins_x, bins_y), dtype=np.float64)
            center = [specs['center'][0] * length_x,
                      specs['center'][1] * length_y]
            base = specs.get('base', 0.0)
            slope = specs['slope']

            for x_bin in range(bins_x):
                for y_bin in range(bins_y):
                    dx = (x_bin + 0.5) * length_x / bins_x - center[0]
                    dy = (y_bin + 0.5) * length_y / bins_y - center[1]
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    field[x_bin][y_bin] += base + slope * (distance/1000)
            fields[molecule_id] = field

    elif gradient.get('type') == 'exponential':
        """
        exponential gradient sets a site's concentration (c) of the given
        molecule as a function of distance (d) from center, with parameters
        base (b) and scale (a). Distance is scaled by 1/1000 from microns to
        millimeters. Note: base > 1 makes concentrations increase from the center.

        c=a*b^d.

        'gradient': {
            'type': 'exponential',
            'molecules': {
                'mol_id1':{
                    'center': [0.0, 0.0],
                    'base': 1+2e-4,
                    'scale': 1.0},
                'mol_id2': {
                    'center': [1.0, 1.0],
                    'base': 1+2e-4,
                    'scale' : 0.1}
            }},
        """

        for molecule_id, specs in gradient['molecules'].items():
            field = np.zeros((bins_x, bins_y), dtype=np.float64)
            center = [specs['center'][0] * length_x,
                      specs['center'][1] * length_y]
            base = specs['base']
            scale = specs.get('scale', 1)

            for x_bin in range(bins_x):
                for y_bin in range(bins_y):
                    dx = (x_bin + 0.5) * length_x / bins_x - center[0]
                    dy = (y_bin + 0.5) * length_y / bins_y - center[1]
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    field[x_bin][y_bin] = scale * base ** (distance/1000)
            fields[molecule_id] = field
    return fields


class DiffusionField(Process):
    '''
    Diffusion in 2-dimensional fields of molecules, with agent locations for uptake and secretion.

    Notes:
    - Diffusion constant of glucose in 0.5 and 1.5 percent agarose gel = ~6 * 10^-10 m^2/s
        (Weng et al. 2005. Transport of glucose and poly(ethylene glycol)s in agarose gels).
    - Conversion to micrometers: 6 * 10^-10 m^2/s = 600 micrometers^2/s.

    '''

    defaults = {
        'molecules': ['glc'],
        'initial_state': {},
        'n_bins': [10, 10],
        'bounds': [10, 10],
        'depth': 3000.0,  # um
        'diffusion': 5e-1,
        'gradient': {},
        'agents': {},
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        # initial state
        self.molecule_ids = initial_parameters.get('molecules', self.defaults['molecules'])
        self.initial_state = initial_parameters.get('initial_state', self.defaults['initial_state'])

        # parameters
        self.n_bins = initial_parameters.get('n_bins', self.defaults['n_bins'])
        self.bounds = initial_parameters.get('bounds', self.defaults['bounds'])
        depth = initial_parameters.get('depth', self.defaults['depth'])

        # diffusion
        diffusion = initial_parameters.get('diffusion', self.defaults['diffusion'])
        bins_x = self.n_bins[0]
        bins_y = self.n_bins[1]
        length_x = self.bounds[0]
        length_y = self.bounds[1]
        dx = length_x / bins_x
        dy = length_y / bins_y
        dx2 = dx * dy
        self.diffusion = diffusion / dx2
        self.diffusion_dt = 0.01
        # self.diffusion_dt = 0.5 * dx ** 2 * dy ** 2 / (2 * self.diffusion * (dx ** 2 + dy ** 2))

        # volume, to convert between counts and concentration
        total_volume = (depth * length_x * length_y) * 1e-15 # (L)
        self.bin_volume = total_volume / (length_x * length_y)

        # initialize gradient fields
        gradient = initial_parameters.get('gradient', self.defaults['gradient'])
        if gradient:
            gradient_fields = make_gradient(gradient, self.n_bins, self.bounds)
            self.initial_state.update(gradient_fields)

        # agents
        self.initial_agents = initial_parameters.get('agents', self.defaults['agents'])

        parameters = {}
        parameters.update(initial_parameters)

        super(DiffusionField, self).__init__(parameters)

    def ports_schema(self):
        local_concentration_schema = {
            molecule: {
                '_default': 0.0,
                '_updater': 'set'}
            for molecule in self.molecule_ids}

        schema = {'agents': {}}
        for agent_id, states in self.initial_agents.items():
            location = states['boundary'].get('location', [])
            exchange = states['boundary'].get('exchange', {})
            schema['agents'][agent_id] = {
                'boundary': {
                    'location': {
                        '_value': location},
                    'exchange': {
                        mol_id: {
                            '_value': value}
                        for mol_id, value in exchange.items()}}}
        glob_schema = {
            '*': {
                'boundary': {
                    'location': {
                        '_default': [0.5, 0.5],
                        '_updater': 'set'},
                    'exchange': local_concentration_schema,
                    'external': local_concentration_schema}}}
        schema['agents'].update(glob_schema)

        # fields
        fields_schema = {
             'fields': {
                 field: {
                     '_default': self.initial_state.get(field, self.ones_field()),
                     '_updater': 'accumulate',
                     '_emit': True}
                 for field in self.molecule_ids}}
        schema.update(fields_schema)
        return schema

    def next_update(self, timestep, states):
        fields = states['fields'].copy()
        agents = states['agents']

        # uptake/secretion from agents
        delta_exchanges = self.apply_exchanges(agents)
        for field_id, delta in delta_exchanges.items():
            fields[field_id] += delta

        # diffuse field
        delta_fields = self.diffuse(fields, timestep)

        # get each agent's local environment
        local_environments = self.get_local_environments(agents, fields)

        update = {'fields': delta_fields}
        if local_environments:
            update.update({'agents': local_environments})

        return update

    def count_to_concentration(self, count):
        return count / (self.bin_volume * AVOGADRO)

    def get_bin_site(self, location):
        bin = np.array([
            location[0] * self.n_bins[0] / self.bounds[0],
            location[1] * self.n_bins[1] / self.bounds[1]])
        bin_site = tuple(np.floor(bin).astype(int) % self.n_bins)
        return bin_site

    def get_single_local_environments(self, specs, fields):
        bin_site = self.get_bin_site(specs['location'])
        local_environment = {}
        for mol_id, field in fields.items():
            local_environment[mol_id] = field[bin_site]
        return local_environment

    def get_local_environments(self, agents, fields):
        local_environments = {}
        if agents:
            for agent_id, specs in agents.items():
                local_environments[agent_id] = {'boundary': {}}
                local_environments[agent_id]['boundary']['external'] = \
                    self.get_single_local_environments(specs['boundary'], fields)
        return local_environments

    def apply_single_exchange(self, delta_fields, specs):
        exchange = specs.get('exchange', {})
        bin_site = self.get_bin_site(specs['location'])
        for mol_id, count in exchange.items():
            if count != 0:
                concentration = self.count_to_concentration(count)
                delta_fields[mol_id][bin_site[0], bin_site[1]] += concentration

    def empty_field(self):
        return np.zeros((self.n_bins[0], self.n_bins[1]), dtype=np.float64)

    def ones_field(self):
        return np.ones((self.n_bins[0], self.n_bins[1]), dtype=np.float64)

    def apply_exchanges(self, agents):
        # initialize delta_fields with zero array
        delta_fields = {
            mol_id: self.empty_field()
            for mol_id in self.molecule_ids}

        if agents:
            # apply exchanges to delta_fields
            for agent_id, specs in agents.items():
                self.apply_single_exchange(delta_fields, specs['boundary'])

        return delta_fields

    # diffusion functions
    def diffusion_delta(self, field, timestep):
        ''' calculate concentration changes cause by diffusion'''
        field_new = field.copy()
        t = 0.0
        dt = min(timestep, self.diffusion_dt)
        while t < timestep:
            field_new += self.diffusion * dt * convolve(field_new, LAPLACIAN_2D, mode='reflect')
            t += dt

        return field_new - field

    def diffuse(self, fields, timestep):
        delta_fields = {}
        for mol_id, field in fields.items():

            # run diffusion if molecule field is not uniform
            if len(set(field.flatten())) != 1:
                delta = self.diffusion_delta(field, timestep)
            else:
                delta = np.zeros_like(field)
            delta_fields[mol_id] = delta

        return delta_fields


# testing
def get_random_field_config(config={}):
    bounds = config.get('bounds', (20, 20))
    n_bins = config.get('n_bins', (10, 10))
    return {
        'molecules': ['glc'],
        'initial_state': {
            'glc': np.random.rand(n_bins[0], n_bins[1])},
        'n_bins': n_bins,
        'bounds': bounds}

def get_gaussian_config(config={}):
    molecules = config.get('molecules', ['glc'])
    bounds = config.get('bounds', (50, 50))
    n_bins = config.get('n_bins', (20, 20))
    center = config.get('center', [0.5, 0.5])
    deviation = config.get('deviation', 5)
    diffusion = config.get('diffusion', 5e-1)

    return {
        'molecules': molecules,
        'n_bins': n_bins,
        'bounds': bounds,
        'diffusion': diffusion,
        'gradient': {
            'type': 'gaussian',
            'molecules': {
                'glc': {
                    'center': center,
                    'deviation': deviation}}}}

def get_exponential_config(config={}):
    molecules = config.get('molecules', ['glc'])
    bounds = config.get('bounds', (40, 40))
    n_bins = config.get('n_bins', (20, 20))
    center = config.get('center', [1.0, 1.0])
    base = config.get('base', 1 + 2e-4)
    scale = config.get('scale', 0.1)
    diffusion = config.get('diffusion', 1e1)

    return {
        'molecules': molecules,
        'n_bins': n_bins,
        'bounds': bounds,
        'diffusion': diffusion,
        'gradient': {
            'type': 'exponential',
            'molecules': {
                'glc': {
                    'center': center,
                    'base': base,
                    'scale': scale}}}}

def get_secretion_agent_config(config={}):
    molecules = config.get('molecules', ['glc'])
    bounds = config.get('bounds', (20, 20))
    n_bins = config.get('n_bins', (10, 10))
    depth = config.get('depth', 30)
    n_agents = config.get('n_agents', 3)

    agents = {}
    for agent in range(n_agents):
        agent_id = str(agent)
        agents[agent_id] = {
            'boundary': {
                'location': [
                        np.random.uniform(0, bounds[0]),
                        np.random.uniform(0, bounds[1])],
                'exchange': {
                    mol_id: 1e3 for mol_id in molecules},
                'external': {
                    mol_id: 0 for mol_id in molecules}}}
    return {
        'molecules': molecules,
        'n_bins': n_bins,
        'bounds': bounds,
        'depth': depth,
        'agents': agents,
        'initial_state': {
            mol_id: np.ones((n_bins[0], n_bins[1]))
            for mol_id in molecules}}

def test_diffusion_field(config=get_gaussian_config(), time=10):
    diffusion = DiffusionField(config)
    settings = {
        'return_raw_data': True,
        'total_time': time,
        'timestep': 1}
    return simulate_process(diffusion, settings)

def plot_fields(data, config, out_dir='out', filename='fields'):
    fields = {time: time_data['fields'] for time, time_data in data.items()}
    snapshots_data = {
        'fields': fields,
        'config': config}
    plot_config = {
        'out_dir': out_dir,
        'filename': filename}
    plot_snapshots(snapshots_data, plot_config)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='diffusion_field')
    parser.add_argument('--random', '-r', action='store_true', default=False)
    parser.add_argument('--gaussian', '-g', action='store_true', default=False)
    parser.add_argument('--exponential', '-e', action='store_true', default=False)
    parser.add_argument('--secretion', '-s', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.random or no_args:
        config = get_random_field_config()
        data = test_diffusion_field(config, 10)
        plot_fields(data, config, out_dir, 'random_field')

    if args.gaussian or no_args:
        config = get_gaussian_config()
        data = test_diffusion_field(config, 10)
        plot_fields(data, config, out_dir, 'gaussian_field')

    if args.exponential or no_args:
        config = get_exponential_config()
        data = test_diffusion_field(config, 20)
        plot_fields(data, config, out_dir, 'exponential_field')

    if args.secretion or no_args:
        config = get_secretion_agent_config()
        data = test_diffusion_field(config, 10)
        plot_fields(data, config, out_dir, 'secretion')
