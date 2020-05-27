from __future__ import absolute_import, division, print_function

from vivarium.core.process import Deriver
from vivarium.utils.units import units

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

    def __init__(self, initial_parameters={}):
        self.from_path = self.or_default(initial_parameters, 'from_path')
        self.initial_mass = initial_parameters.get('initial_mass', self.defaults['initial_mass'])

        ports = {
            'global': [
                'mass']}

        super(TreeMass, self).__init__(ports, initial_parameters)

    def ports_schema(self):
        return {
            'global': {
                'mass': {
                    '_units': units.fg,
                    '_default': self.initial_mass.magnitude,
                    '_updater': 'set'}}}

    def next_update(self, timestep, states):
        return {
            'global': {
                'mass': {
                    '_reduce': {
                        'reducer': calculate_mass,
                        'from': self.from_path,
                        'initial': 0.0 * units.fg}}}}
