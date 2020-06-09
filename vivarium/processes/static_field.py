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
from vivarium.processes.diffusion_field import make_gradient, plot_fields


NAME = 'static_field'


class StaticField(Process):

    defaults = {
        'molecules': ['glc'],
        'initial_state': {},
        'n_bins': [10, 10],
        'bounds': [10, 10],
        'gradient': {},
        'agents': {},
        'boundary_port': 'boundary',
        'external_port': 'external',
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
        self.boundary_port = initial_parameters.get('boundary_port', self.defaults['boundary_port'])
        self.external_port = initial_parameters.get('external_port', self.defaults['external_port'])

        # initialize gradient fields
        gradient = initial_parameters.get('gradient', self.defaults['gradient'])
        if gradient:
            gradient_fields = make_gradient(gradient, self.n_bins, self.bounds)
            self.initial_state.update(gradient_fields)

        # agents
        self.initial_agents = initial_parameters.get('agents', self.defaults['agents'])

        # make ports
        ports = {
             'fields': self.molecule_ids,
             'agents': ['*']}

        parameters = {}
        parameters.update(initial_parameters)

        super(StaticField, self).__init__(ports, parameters)

    def ports_schema(self):
        local_concentration_schema = {
            molecule: {
                '_default': 0.0,
                '_updater': 'set'}
            for molecule in self.molecule_ids}

        schema = {'agents': {}}
        # for agent_id, states in self.initial_agents.items():
        #     location = states[self.boundary_port].get('location', [])
        #     exchange = states[self.boundary_port].get('exchange', {})
        #     schema['agents'][agent_id] = {
        #         self.boundary_port: {
        #             'location': {
        #                 '_value': location},
        #             'exchange': {
        #                 mol_id: {
        #                     '_value': value}
        #                 for mol_id, value in exchange.items()}}}
        glob_schema = {
            '*': {
                self.boundary_port: {
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
                     '_value': self.initial_state.get(field, self.ones_field()),
                     '_updater': 'accumulate',
                     '_emit': False}
                 for field in self.molecule_ids}}
        schema.update(fields_schema)
        return schema

    def next_update(self, timestep, states):
        fields = states['fields'].copy()
        agents = states['agents']

        # check for unexpected fields
        new_fields = {}
        for agent_id, specs in agents.items():
            external = specs['boundary']['external']
            for mol_id, concentration in external.items():
                if mol_id not in self.molecule_ids and concentration is not None:
                    self.molecule_ids.append(mol_id)
                    new_fields[mol_id] = concentration * self.ones_field()

        # get each agent's local environment
        local_environments = self.get_local_environments(agents, fields)

        return {'agents': local_environments}


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
                local_environments[agent_id] = {self.boundary_port: {}}
                local_environments[agent_id][self.boundary_port][self.external_port] = \
                    self.get_single_local_environments(specs[self.boundary_port], fields)
        return local_environments

    def empty_field(self):
        return np.zeros((self.n_bins[0], self.n_bins[1]), dtype=np.float64)

    def ones_field(self):
        return np.ones((self.n_bins[0], self.n_bins[1]), dtype=np.float64)



def get_config(config={}):

    molecules = ['glc']
    bounds = (20, 20)
    n_bins = (10, 10)
    n_agents = 3

    agents = {}
    for agent in range(n_agents):
        agent_id = str(agent)
        agents[agent_id] = {
            'boundary': {
                'location': [
                        np.random.uniform(0, bounds[0]),
                        np.random.uniform(0, bounds[1])],
                'external': {
                    mol_id: 0 for mol_id in molecules}}}
    return {
        'molecules': molecules,
        'n_bins': n_bins,
        'bounds': bounds,
        'agents': agents,
        'gradient': {
            'type': 'exponential',
            'molecules': {
                mol_id: {
                    'center': [0.0, 0.0],
                    'base': 1 + 1e-1}
                for mol_id in molecules}},
        'initial_state': {
            mol_id: np.ones((n_bins[0], n_bins[1]))
            for mol_id in molecules}}

def test_fields(config=get_config(), time=2):
    fields = StaticField(config)
    settings = {
        'return_raw_data': True,
        'total_time': 10,
        'timestep': 1}
    return simulate_process(fields, settings)

if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    config = get_config()
    data = test_fields(config, 10)
    plot_fields(data, config, out_dir, 'exponential')