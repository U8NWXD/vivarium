from __future__ import absolute_import, division, print_function

import os

import numpy as np
import scipy.constants as constants
import matplotlib.pyplot as plt

from vivarium.core.process import Process
from vivarium.library.dict_utils import deep_merge
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)


NAME = 'membrane_potential'

# PMF ~170mV at pH 7. ~140mV at pH 7.7 (Berg)
# Ecoli internal pH in range 7.6-7.8 (Berg)

# (mmol) http://book.bionumbers.org/what-are-the-concentrations-of-different-ions-in-cells/
# Schultz, Stanley G., and A. K. Solomon. "Cation Transport in Escherichia coli" (1961)
# TODO -- add Mg2+, Ca2+
DEFAULT_STATE = {
    'internal': {
        'K': 300,  # (mmol) 30-300
        'Na': 10,  # (mmol) 10
        'Cl': 10},  # (mmol) 10-200 media-dependent
    'external': {
        'K': 5,
        'Na': 145,
        'Cl': 110,  # (mmol)
        'T': 310.15}
    }

DEFAULT_PARAMETERS = {
    'p_K': 1,  # unitless, relative membrane permeability of K
    'p_Na': 0.05,  # unitless, relative membrane permeability of Na
    'p_Cl': 0.05,  # unitless, relative membrane permeability of Cl
    }

PERMEABILITY_MAP = {
    'K': 'p_K',
    'Na': 'p_Na',
    'Cl': 'p_Cl'
    }

# cation is positively charged, anion is negatively charged
CHARGE_MAP = {
    'K': 'cation',
    'Na': 'cation',
    'Cl': 'anion',
    'PROTON': 'cation',
    }

class NoChargeError(Exception):
    pass

class MembranePotential(Process):
    '''
    Need to add a boot method for this process to vivarium/environment/boot.py for it to run on its own
    '''

    defaults = {
        'initial_state': DEFAULT_STATE,
        'parameters': DEFAULT_PARAMETERS,
        'permeability': PERMEABILITY_MAP,
        'charge': CHARGE_MAP,
        'constants': {
            'R': constants.gas_constant,  # (J * K^-1 * mol^-1) gas constant
            'F': constants.physical_constants['Faraday constant'][0],  # (C * mol^-1) Faraday constant
            'k': constants.Boltzmann,  # (J * K^-1) Boltzmann constant
            }
    }

    def __init__(self, initial_parameters=None):
        if not initial_parameters:
            initial_parameters = {}

        self.initial_state = self.or_default(
            initial_parameters, 'initial_state')
        self.permeability = self.or_default(
            initial_parameters, 'permeability')
        self.charge = self.or_default(
            initial_parameters, 'charge')
        self.parameters = self.or_default(
            initial_parameters, 'parameters')
        self.parameters.update(self.defaults['constants'])

        super(MembranePotential, self).__init__(self.parameters)

    def ports_schema(self):
        ports = [
            'internal',
            'membrane',
            'external',
        ]
        schema = {port: {} for port in ports}

        ## internal
        # internal ions and charge (c_in)
        for state in list(self.initial_state['internal'].keys()):
            schema['internal'][state] = {
                '_default': self.initial_state['internal'].get(state, 0.0),
                '_emit': True,
            }

        ## external
        # external ions, charge (c_out) and temperature (T)
        for state in list(self.initial_state['external'].keys()) + ['T']:
            schema['external'][state] = {
                '_default': self.initial_state['external'].get(state, 0.0),
                '_emit': True,
            }

        ## membrane
        # proton motive force (PMF), electrical difference (d_V), pH difference (d_pH)
        for state in ['PMF', 'd_V', 'd_pH']:
            schema['membrane'][state] = {
                '_updater': 'set',
                '_emit': True,
            }

        return schema

    def next_update(self, timestep, states):
        internal_state = states['internal']
        external_state = states['external']

        # parameters
        R = self.parameters['R']
        F = self.parameters['F']
        k = self.parameters['k']

        # state
        T = external_state['T']  # temperature
        # e = 1 # proton charge # TODO -- get proton charge from state

        # Membrane potential.
        numerator = 0
        denominator = 0
        for ion_id, p_ion_id in self.permeability.items():
            charge = self.charge[ion_id]
            p_ion = self.parameters[p_ion_id]

            # ions states
            internal = internal_state[ion_id]
            external = external_state[ion_id]

            if charge is 'cation':
                numerator += p_ion * external
                denominator += p_ion * internal
            elif charge is 'anion':
                numerator += p_ion * internal
                denominator += p_ion * external
            else:
                raise NoChargeError(
                    "No charge given for {}".format(ion_id))

        # Goldman equation for membrane potential
        # expected d_V = -120 mV
        d_V = (R * T) / (F) * np.log(numerator / denominator) * 1e3  # (mV). 1e3 factor converts from V

        # Nernst equation for pH difference
        # -2.3 * k * T / e  # -2.3 Boltzmann constant * temperature
        # expected d_pH = -50 mV
        d_pH = -50  # (mV) for cells grown at pH 7. (Berg, H. "E. coli in motion", pg 105)

        # proton motive force
        PMF = d_V + d_pH

        return {
            'membrane': {
                'd_V': d_V,
                'd_pH': d_pH,
                'PMF': PMF}}

def test_mem_potential():
    initial_parameters = {
        'initial_state': DEFAULT_STATE,
        'parameters': DEFAULT_PARAMETERS,
        'permeability': PERMEABILITY_MAP,
        'charge': CHARGE_MAP,
    }

    # configure process
    mp = MembranePotential(initial_parameters)
    timeline = [
        (0, {('external', 'Na'): 1}),
        (100, {('external', 'Na'): 2}),
        (500, {})]

    settings = {'timeline': {'timeline': timeline}}
    return simulate_process_in_experiment(mp, settings)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    timeseries = test_mem_potential()
    settings = {
        'remove_first_timestep': True
    }
    plot_simulation_output(timeseries, settings, out_dir)
