from __future__ import absolute_import, division, print_function

import uuid

from vivarium.core.process import Deriver


# functions for generating daughter ids
def daughter_uuid(mother_id):
    return [
        str(uuid.uuid1()),
        str(uuid.uuid1())]

def daughter_phylogeny_id(mother_id):
    return [
        str(mother_id) + '0',
        str(mother_id) + '1']


class MetaDivision(Deriver):

    defaults = {
        'initial_state': {},
        'daughter_path': ('cell',),
        'daughter_ids_function': daughter_phylogeny_id}

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        self.division = 0

        # must provide a compartment to generate new daughters
        self.agent_id = initial_parameters['agent_id']
        self.compartment = initial_parameters['compartment']
        self.daughter_ids_function = self.or_default(
            initial_parameters, 'daughter_ids_function')
        self.daughter_path = self.or_default(
            initial_parameters, 'daughter_path')

        super(MetaDivision, self).__init__(initial_parameters)

    def ports_schema(self):
        return {
            'global': {
                'divide': {
                    '_default': False,
                    '_updater': 'set'}},
            'cells': {
                '*': {}}}

    def next_update(self, timestep, states):
        divide = states['global']['divide']

        if divide:
            daughter_ids = self.daughter_ids_function(self.agent_id)
            daughter_updates = []
            
            for daughter_id in daughter_ids:
                compartment = self.compartment.generate({
                    'agent_id': daughter_id})
                daughter_updates.append({
                    'daughter': daughter_id,
                    'path': (daughter_id,) + self.daughter_path,
                    'processes': compartment['processes'],
                    'topology': compartment['topology'],
                    'initial_state': {}})

            # initial state will be provided by division in the tree
            return {
                'cells': {
                    '_divide': {
                        'mother': self.agent_id,
                        'daughters': daughter_updates}}}
        else:
             return {}   
