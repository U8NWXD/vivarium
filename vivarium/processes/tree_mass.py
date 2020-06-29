from __future__ import absolute_import, division, print_function

from vivarium.core.process import Deriver
from vivarium.library.units import units

from vivarium.processes.derive_globals import AVOGADRO


def calculate_mass(value, path, node):
    if 'mw' in node.properties:
        count = node.value
        mw = node.properties['mw']
        mol = count / AVOGADRO
        added_mass = mw * mol
        return value + added_mass
    else:
        return value


class TreeMass(Deriver):
    """
    Derives and sets total mass from individual molecular counts
    that have a mass schema in their stores .

    """

    defaults = {
        'from_path': ('..', '..'),
        'initial_mass': 0.0 * units.fg,
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        self.from_path = self.or_default(initial_parameters, 'from_path')
        self.initial_mass = self.or_default(initial_parameters, 'initial_mass')

        super(TreeMass, self).__init__(initial_parameters)

    def ports_schema(self):
        return {
            'global': {
                'initial_mass': {
                    '_default': self.initial_mass,
                    '_updater': 'set',
                    '_divider': 'split'},
                'mass': {
                    '_default': self.initial_mass,
                    '_emit': True,
                    '_updater': 'set'}}}

    def next_update(self, timestep, states):
        initial_mass = states['global']['initial_mass']
        return {
            'global': {
                'mass': {
                    '_reduce': {
                        'reducer': calculate_mass,
                        'from': self.from_path,
                        'initial': initial_mass}}}}
