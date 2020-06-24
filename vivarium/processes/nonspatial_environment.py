from __future__ import absolute_import, division, print_function

import copy

from vivarium.library.units import units
from vivarium.library.dict_utils import deep_merge
from vivarium.core.process import Deriver

from vivarium.processes.derive_globals import AVOGADRO


class NonSpatialEnvironment(Deriver):
    '''A non-spatial environment with volume'''

    defaults = {
        'volume': 1e-12 * units.L}

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        volume = initial_parameters.get('volume', self.defaults['volume'])
        self.mmol_to_counts = (AVOGADRO.to('1/mmol') * volume).to('L/mmol')

        parameters = initial_parameters
        super(NonSpatialEnvironment, self).__init__(parameters)

    def ports_schema(self):
        return {
            'external': {
                '*': {
                    '_default': 0.0}},
            'exchange': {
                '*': {
                    '_default': 0}}}

    def next_update(self, timestep, states):
        exchange = states['exchange']

        # get counts, convert to concentration change
        update = {
            'external': {},
            'exchange': {}}

        for mol_id, delta_count in exchange.items():
            delta_concs = delta_count / self.mmol_to_counts
            if delta_concs != 0:
                update['external'][mol_id] = delta_concs.magnitude  # TODO -- remove magnitude

                # reset exchange
                update['exchange'][mol_id] = {
                    '_value': 0.0,
                    '_updater': 'set'}

        return update
