from __future__ import absolute_import, division, print_function

import copy
import numpy as np
from arrow import StochasticSystem

from vivarium.compartment.process import Process, keys_list
from vivarium.data.chromosomes.flagella_chromosome import FlagellaChromosome

chromosome = FlagellaChromosome()

default_complexation_parameters = {
    'monomer_ids': chromosome.complexation_monomer_ids,
    'complex_ids': chromosome.complexation_complex_ids,
    'stoichiometry': chromosome.complexation_stoichiometry,
    'rates': chromosome.complexation_rates}

def build_complexation_stoichiometry(
        stoichiometry,
        rates,
        reaction_ids,
        monomer_ids,
        complex_ids):

    molecule_ids = monomer_ids + complex_ids
    matrix = np.zeros((len(stoichiometry), len(molecule_ids)), dtype=np.int64)
    rates_array = np.zeros(len(stoichiometry))

    reverse_index = {
        molecule_id: index
        for index, molecule_id in enumerate(molecule_ids)}

    for reaction_index, reaction_id in enumerate(reaction_ids):
        reaction = stoichiometry[reaction_id]
        rates_array[reaction_index] = rates[reaction_id]
        for molecule_id, level in reaction.items():
            matrix[reaction_index][reverse_index[molecule_id]] = level

    return matrix, rates_array
    

class Complexation(Process):
    def __init__(self, initial_parameters={}):
        self.default_parameters = copy.deepcopy(default_complexation_parameters)
        self.derive_defaults(initial_parameters, 'stoichiometry', 'reaction_ids', keys_list)

        self.parameters = self.default_parameters
        self.parameters.update(initial_parameters)

        self.monomer_ids = self.parameters['monomer_ids']
        self.complex_ids = self.parameters['complex_ids']
        self.reaction_ids = self.parameters['reaction_ids']

        self.stoichiometry = self.parameters['stoichiometry']
        self.rates = self.parameters['rates']

        self.complexation_stoichiometry, self.complexation_rates = build_complexation_stoichiometry(
            self.stoichiometry,
            self.rates,
            self.reaction_ids,
            self.monomer_ids,
            self.complex_ids)

        self.complexation = StochasticSystem(self.complexation_stoichiometry)

        self.ports = {
            'monomers': self.monomer_ids,
            'complexes': self.complex_ids}

    def default_settings(self):
        default_state = {
            'monomers': {monomer_id: 1000 for monomer_id in self.monomer_ids},
            'complexes': {complex_id: 0 for complex_id in self.complex_ids}}

        return {
            'state': default_state,
            'parameters': self.parameters}

    def next_update(self, timestep, states):
        monomers = states['monomers']
        complexes = states['complexes']

        substrate = np.zeros(len(self.monomer_ids) + len(self.complex_ids), dtype=np.int64)

        for index, monomer_id in enumerate(self.monomer_ids):
            substrate[index] = monomers[monomer_id]
        for index, complex_id in enumerate(self.complex_ids):
            substrate[index + len(self.monomer_ids)] = complexes[complex_id]

        result = self.complexation.evolve(
            timestep,
            substrate,
            self.complexation_rates)

        outcome = result['outcome'] - substrate

        monomers_update = {
            monomer_id: outcome[index]
            for index, monomer_id in enumerate(self.monomer_ids)}

        complexes_update = {
            complex_id: outcome[index + len(self.monomer_ids)]
            for index, complex_id in enumerate(self.complex_ids)}

        update = {
            'monomers': monomers_update,
            'complexes': complexes_update}

        return update

def test_complexation():
    complexation = Complexation()
    settings = complexation.default_settings()
    state = settings['state']

    update = complexation.next_update(1.0, state)
    print('initial state: {}'.format(state))
    print('complexation update: {}'.format(update))

if __name__ == '__main__':
    test_complexation()