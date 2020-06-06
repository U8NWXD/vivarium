from __future__ import absolute_import, division, print_function

from vivarium.core.process import Process


class Template(Process):
    '''
    This mock process provides a basic template that can be used for a new process
    '''

    defaults = {
        'parameters': {}
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        ports = {
            'internal': ['A'],
            'external': ['B'],
        }

        parameters = initial_parameters.get(
            'parameters', self.defaults['parameters'])

        super(Template, self).__init__(ports, parameters)

    def ports_schema(self):
        '''
        schema is is a dictionary that declares how each state will behave.

        TODO -- describe the schema
            '_value'
            '_default'
            '_updater'
            '_divider'
            '_emit'
        '''

        return {
            'internal': {
                'A': {
                    '_default': 1.0,
                    '_emit': True,
                }
            },
            'external': {
                'A': {
                    '_default': 1.0,
                    '_emit': True,
                }
            },
        }

    def derivers(self):
        '''
        declare which derivers are needed for this process
        '''
        pass

    def next_update(self, timestep, states):
        internal_state = states['internal']
        external_state = states['external']

        internal_updates = 0
        external_updates = 0

        update = {
            'internal': {'states': internal_updates},
            'external': {'states': external_updates},
        }
        return update