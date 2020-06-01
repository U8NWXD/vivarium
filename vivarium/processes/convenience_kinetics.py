'''
====================
Convenience Kinetics
====================

Convenience kinetics :cite:`liebermeister_bringing_2006` provides a
generic way to represent rate laws that follow Michaelis-Menten-style
enzyme kinetics. The generalized law can model arbitrary reaction
stoichiometries, catalytic enzymes, activators, and inhibitors.

If you are looking to model a catalyzed proess, this may be the
:term:`process class` you need.

Executing this file directly simulates an instance of
:py:class:`ConvenienceKinetics` with the configuration from
:py:func:`get_glc_lct_config`.

------------
Bibliography
------------

.. bibliography:: /references.bib
    :style: plain

'''

from __future__ import absolute_import, division, print_function

import os

from scipy import constants

from vivarium.core.process import Process
from vivarium.core.tree import schema_for
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    flatten_timeseries,
    save_timeseries,
    load_timeseries,
    REFERENCE_DATA_DIR,
    PROCESS_OUT_DIR,
    assert_timeseries_close,
)
from vivarium.utils.kinetic_rate_laws import KineticFluxModel
from vivarium.utils.dict_utils import tuplify_port_dicts
from vivarium.utils.units import units


#: The name of the process, which is used to name the subdirectory under
#: ``out/tests`` that stores the output data from executing this file.
NAME = 'convenience_kinetics'


class ConvenienceKinetics(Process):

    defaults = {
        'reactions': {},
        'initial_state': {
            'internal': {},
            'external': {}},
        'kinetic_parameters': {},
        'ports': {
            'internal': [],
            'external': []},
        'global_deriver_key': 'global_deriver'}

    def __init__(self, initial_parameters={}):
        '''Michaelis-Menten-style enzyme kinetics model

        Arguments:
            initial_parameters: Configures the :term:`process` with the
                following configuration options:

                * **reactions** (:py:class:`dict`): Specifies the
                  stoichiometry, reversibility, and catalysts of each
                  reaction to model. For a non-reversible reaction
                  :math:`A + B \\rightleftarrows 2C` catalized by an
                  enzyme :math:`E`, we have the following reaction
                  specification:

                  .. code-block:: python

                    {
                        # reaction1 is a reaction ID
                        'reaction1': {
                            'stoichiometry': {
                                # 1 mol A is consumd per mol reaction
                                ('internal', 'A'): -1,
                                ('internal', 'B'): -1,
                                # 2 mol C are produced per mol reaction
                                ('internal', 'C'): 2,
                            },
                            'is reversible': False,
                            'catalyzed by': [
                                ('internal', 'E'),
                            ],
                        }
                    }

                  Note that for simplicity, we assumed all the molecules
                  and enzymes were in the ``internal`` port, but this is
                  not necessary.
                * **kinetic_parameters** (:py:class:`dict`): Specifies
                  the kinetics of the reaction by providing
                  :math:`k_{cat}` and :math:`K_M` parameters for each
                  enzyme. For example, let's say that for the reaction
                  described above, :math:`k{cat} = 1`, :math:`K_A = 2`,
                  and :math:`K_B = 3`. Then the reaction kinetics would
                  be specified by:

                  .. code-block:: python

                    {
                        'reaction1': {
                            ('internal', 'E'): {
                                'kcat_f': 1,  # kcat for forward reaction
                                ('internal', 'A'): 2,
                                ('internal', 'B'): 3,
                            },
                        },
                    }

                  If the reaction were reversible, we could have
                  specified ``kcat_r`` as the :math:`k_{cat}` of the
                  reverse reaction.
                * **initial_state** (:py:class:`dict`): Provides the
                  initial quantities of the molecules and enzymes. The
                  initial reaction flux must also be specified. For
                  example, to start with :math:`[E] = 1.2 mM` and
                  :math:`[A] = [B] = [C] = 0 mM` with an initial
                  reaction flux of `0`, we would have:

                  .. code-block:: python

                    {
                        'internal': {
                            'A': 0.0,
                            'B': 0.0,
                            'C': 0.0,
                            'E': 1.2,
                        },
                        'fluxes': {
                            'reaction1': 0.0,
                        }
                    }

                  .. note:: Unlike the previous configuration options,
                      the initial state dictionary is not divided up by
                      reaction.

                  If no initial state is specified,
                  :py:const:`EMPTY_STATES` is used.
                * **ports** (:py:class:`dict`): Each item in the
                  dictionary has a :term:`port` name as its key and a
                  list of the :term:`variables` in that port as its
                  value. Each port should be specified only once. For
                  example, the reaction we have been using as an example
                  would have:

                  .. code-block:: python

                    {
                        'internal': ['A', 'B', 'C', 'E'],
                    }

                  If no ports are specified, :py:const:`EMPTY_ROLES` is
                  used.

        The ports of the process are the ports configured by the
        user, with the following modifications:

        * A ``fluxes`` port is added with variable names equal to
          the IDs of the configured reactions.
        * An ``exchange`` port is added with the same variables as the
          ``external`` port.
        * A ``global`` port is added with a variable named
          ``mmol_to_counts``, which is set by a :term:`deriver`.

        Example configuring a process to model the kinetics and reaction
        described above.

        >>> configuration = {
        ...     'reactions': {
        ...         # reaction1 is the reaction ID
        ...         'reaction1': {
        ...             'stoichiometry': {
        ...                 # 1 mol A is consumd per mol reaction
        ...                 ('internal', 'A'): -1,
        ...                 ('internal', 'B'): -1,
        ...                 # 2 mol C are produced per mol reaction
        ...                 ('internal', 'C'): 2,
        ...             },
        ...             'is reversible': False,
        ...             'catalyzed by': [
        ...                 ('internal', 'E'),
        ...             ],
        ...         }
        ...     },
        ...     'kinetic_parameters': {
        ...         'reaction1': {
        ...             ('internal', 'E'): {
        ...                 'kcat_f': 1,  # kcat for forward reaction
        ...                 ('internal', 'A'): 2,
        ...                 ('internal', 'B'): 3,
        ...             },
        ...         },
        ...     },
        ...     'initial_state': {
        ...         'internal': {
        ...             'A': 0.0,
        ...             'B': 0.0,
        ...             'C': 0.0,
        ...             'E': 1.2,
        ...         },
        ...         'fluxes': {
        ...             'reaction1': 0.0,
        ...         }
        ...     },
        ...     'ports': {
        ...         'internal': ['A', 'B', 'C', 'E'],
        ...         'external': [],
        ...     },
        ... }
        >>> kinetic_process = ConvenienceKinetics(configuration)
        '''
        self.nAvogadro = constants.N_A * 1 / units.mol

        # retrieve initial parameters
        self.reactions = initial_parameters.get('reactions', self.defaults['reactions'])
        self.initial_state = initial_parameters.get('initial_state', self.defaults['initial_state'])
        kinetic_parameters = initial_parameters.get('kinetic_parameters', self.defaults['kinetic_parameters'])
        ports = initial_parameters.get('ports', self.defaults['ports'])

        # make the kinetic model
        self.kinetic_rate_laws = KineticFluxModel(self.reactions, kinetic_parameters)

        # ports
        # fluxes port is used to pass constraints
        # exchange is equivalent to external, for lattice_compartment
        ports.update({
            'fluxes': self.kinetic_rate_laws.reaction_ids,
            'exchange': ports['external'],
            'global': ['mmol_to_counts']})

        # parameters
        parameters = {}
        parameters.update(initial_parameters)

        self.global_deriver_key = self.or_default(
            initial_parameters, 'global_deriver_key')

        super(ConvenienceKinetics, self).__init__(ports, parameters)

    def ports_schema(self):
        set_ports = ['fluxes']
        emit_ports = ['internal', 'external']

        schema = {}
        for port, states in self.ports.items():
            schema[port] = {}
            for state_id in states:
                schema[port][state_id] = {}
                if port in self.initial_state:
                    if state_id in self.initial_state[port]:
                        schema[port][state_id]['_default'] = self.initial_state[port][state_id]
                else:
                    schema[port][state_id]['_default'] = 0.0
            if port in set_ports:
                for state_id in states:
                    schema[port][state_id]['_updater'] = 'set'

            emitting = port in emit_ports
            for state_id in states:
                schema[port][state_id]['_emit'] = emitting

        return schema

    def derivers(self):
        return {
            self.global_deriver_key: {
                'deriver': 'globals',
                'port_mapping': {
                    'global': 'global'},
                'config': {
                    'width': 1.0}}}

    def next_update(self, timestep, states):

        # get mmol_to_counts for converting flux to exchange counts
        mmol_to_counts = states['global']['mmol_to_counts'] * units.L / units.mmol

        # kinetic rate law requires a flat dict with ('port', 'state') keys.
        flattened_states = tuplify_port_dicts(states)

        # get flux
        fluxes = self.kinetic_rate_laws.get_fluxes(flattened_states)

        # make the update
        # add fluxes to update
        update = {port: {} for port in self.ports.keys()}
        update.update({'fluxes': fluxes})

        # get exchange
        for reaction_id, flux in fluxes.items():
            stoichiometry = self.reactions[reaction_id]['stoichiometry']
            for port_state_id, coeff in stoichiometry.items():
                for port_id, state_list in self.ports.items():
                    # separate the state_id and port_id
                    if port_id in port_state_id:
                        state_id = port_state_id[1]
                        state_flux = coeff * flux * timestep

                        if port_id == 'external':
                            # convert exchange fluxes to counts with mmol_to_counts
                            # TODO -- use deriver to get exchanges
                            delta_counts = int((state_flux * mmol_to_counts).magnitude)
                            update['exchange'][state_id] = (
                                update['exchange'].get(state_id, 0)
                                + delta_counts
                            )
                        else:
                            update[port_id][state_id] = (
                                update[port_id].get(state_id, 0)
                                + state_flux
                            )

        # note: external and internal ports update change in mmol.
        return update



# functions
def get_glc_lct_config():
    """
    :py:class:`ConvenienceKinetics` configuration for simplified glucose
    and lactose transport.Glucose uptake simplifies the PTS/GalP system
    to a single uptake kinetic with ``glc__D_e_external`` as the only
    cofactor.

    You can use this configuration with :py:class:`ConvenienceKinetics`
    like this:

    >>> configuration = get_glc_lct_config()
    >>> kinetic_process = ConvenienceKinetics(configuration)
    """
    transport_reactions = {
        'EX_glc__D_e': {
            'stoichiometry': {
                ('internal', 'g6p_c'): 1.0,
                ('external', 'glc__D_e'): -1.0,
                ('internal', 'pep_c'): -1.0,  # TODO -- PEP requires homeostasis mechanism to avoid depletion
                ('internal', 'pyr_c'): 1.0,
            },
            'is reversible': False,
            'catalyzed by': [('internal', 'EIIglc')]
        },
        'EX_lcts_e': {
            'stoichiometry': {
                ('external', 'lcts_e'): -1.0,
                ('internal', 'lcts_p'): 1.0,
            },
            'is reversible': False,
            'catalyzed by': [('internal', 'LacY')]
        }
    }

    transport_kinetics = {
        'EX_glc__D_e': {
            ('internal', 'EIIglc'): {
                ('external', 'glc__D_e'): 1e0,  # k_m for external [glc__D_e]
                ('internal', 'pep_c'): None,  # Set k_m = None to make a reactant non-limiting
                'kcat_f': 6e1,  # kcat for the forward direction
            }
        },
        'EX_lcts_e': {
            ('internal', 'LacY'): {
                ('external', 'lcts_e'): 1e0,
                'kcat_f': 6e1,
            }
        }
    }

    transport_initial_state = {
        'internal': {
            'EIIglc': 1.8e-3,  # (mmol/L)
            'g6p_c': 0.0,
            'pep_c': 1.8e-1,
            'pyr_c': 0.0,
            'LacY': 0,
            'lcts_p': 0.0,
        },
        'external': {
            'glc__D_e': 10.0,
            'lcts_e': 10.0,
        },
        'fluxes': {
            'EX_glc__D_e': 0.0,
            'EX_lcts_e': 0.0,
        }
    }

    transport_ports = {
        'internal': [
            'g6p_c', 'pep_c', 'pyr_c', 'EIIglc', 'LacY', 'lcts_p'],
        'external': [
            'glc__D_e', 'lcts_e']
    }

    return {
        'reactions': transport_reactions,
        'kinetic_parameters': transport_kinetics,
        'initial_state': transport_initial_state,
        'ports': transport_ports}

def get_toy_config():
    '''
    Returns
        A configuration for :py:class:`ConvenienceKinetics` that models
        a toy reaction for illustration purposes.
    '''
    toy_reactions = {
        'reaction1': {
            'stoichiometry': {
                ('internal', 'A'): 1,
                ('external', 'B'): -1},
            'is reversible': False,
            'catalyzed by': [('internal', 'enzyme1')]
        }
    }

    toy_kinetics = {
        'reaction1': {
            ('internal', 'enzyme1'): {
                ('external', 'B'): 0.2,
                'kcat_f': 5e1,
            }
        }
    }

    toy_ports = {
        'internal': ['A', 'enzyme1'],
        'external': ['B']
    }

    toy_initial_state = {
        'internal': {
            'A': 1.0,
            'enzyme1': 1e-1,
        },
        'external': {
            'B': 10.0,
        },
        'fluxes': {
            'reaction1': 0.0,
        }
    }

    return {
        'reactions': toy_reactions,
        'kinetic_parameters': toy_kinetics,
        'initial_state': toy_initial_state,
        'ports': toy_ports}


def test_convenience_kinetics(end_time=2520):
    config = get_glc_lct_config()
    kinetic_process = ConvenienceKinetics(config)

    settings = {
        'environment': {
            'volume': 5e-14,
            'states': ['glc__D_e', 'lcts_e'],
            'environment_port': 'external',
            'exchange_port': 'exchange'},
        'timestep': 1,
        'total_time': end_time}

    return simulate_process_in_experiment(kinetic_process, settings)

def test_convenience_kinetics_correlated_to_reference():
    timeseries = test_convenience_kinetics()
    flattened = flatten_timeseries(timeseries)
    reference_timeseries = load_timeseries(
        os.path.join(REFERENCE_DATA_DIR, NAME + '.csv'))
    assert_timeseries_close(flattened, reference_timeseries)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    timeseries = test_convenience_kinetics()

    plot_settings = {}
    plot_simulation_output(timeseries, plot_settings, out_dir)
    save_timeseries(timeseries, out_dir)
