from __future__ import absolute_import, division, print_function

import os

import numpy as np
import scipy.constants as constants
import matplotlib.pyplot as plt

from vivarium.core.process import Process
from vivarium.utils.dict_utils import deep_merge
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

# TODO -- get references on these
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
        'states': DEFAULT_STATE,
        'parameters': DEFAULT_PARAMETERS,
        'permeability': PERMEABILITY_MAP,
        'charge': CHARGE_MAP,
        'constants': {
            'R': constants.gas_constant,  # (J * K^-1 * mol^-1) gas constant
            'F': constants.physical_constants['Faraday constant'][0], # (C * mol^-1) Faraday constant
            'k': constants.Boltzmann, # (J * K^-1) Boltzmann constant
            }
    }


    def __init__(self, config={}):

        # set states
        self.initial_states = config.get('states', self.defaults['states'])
        self.permeability = config.get('permeability', self.defaults['permeability'])
        self.charge = config.get('charge', self.defaults['charge'])

        # set parameters
        parameters = self.defaults['constants']
        parameters.update(config.get('parameters', self.defaults['parameters']))

        # get list of internal and external states
        internal_states = list(self.initial_states['internal'].keys())
        external_states = list(self.initial_states['external'].keys())

        # set ports
        ports = {
            'internal': internal_states + ['c_in'],
            'membrane': ['PMF', 'd_V', 'd_pH'],  # proton motive force (PMF), electrical difference (d_V), pH difference (d_pH)
            'external': external_states + ['c_out', 'T'],
        }

        super(MembranePotential, self).__init__(ports, parameters)

    def ports_schema(self):
        set_update = {'membrane': ['d_V', 'd_pH', 'PMF']}
        default_state = self.initial_states

        schema = {}
        for port, states in self.ports.items():
            schema[port] = {
                state: {
                    '_emit': True  # emit all states
                } for state in states}
            if port in set_update:
                for state_id in set_update[port]:
                    schema[port][state_id]['_updater'] = 'set'
            if port in default_state:
                for state_id, value in default_state[port].items():
                    schema[port][state_id]['_default'] = value

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
        'states': DEFAULT_STATE,
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

    settings = {'timeline': timeline}
    return simulate_process_in_experiment(mp, settings)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    timeseries = test_mem_potential()
    plot_simulation_output(timeseries, {}, out_dir)
