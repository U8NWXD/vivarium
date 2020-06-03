'''Simulates antibiotic import'''


from __future__ import absolute_import, division, print_function

import os

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
from vivarium.processes.convenience_kinetics import ConvenienceKinetics


#: Default initial concentrations
DEFAULT_INITIAL_STATE = {
    'internal': {
        'porin': 1.0,  # Membrane pore through which antibiotics enter
        # EcoCyc ID: TRANS-CPLX-201
        'AcrAB-TolC': 1.0,  # Efflux pump complex
        'antibiotic': 0.0,
    },
    'external': {
        'antibiotic': 1.0,
    },
    'exchange': {
        'antibiotic': 0.0,
    },
}

#: Default initial flux levels
DEFAULT_INITIAL_FLUXES = {
    'antibiotic_import': 0.0,
    'antibiotic_export': 0.0,
}

NAME = 'antibiotic_transport'


class AntibioticTransport(ConvenienceKinetics):
    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        if 'initial_state' not in initial_parameters:
            initial_state = DEFAULT_INITIAL_STATE
        else:
            initial_state = initial_parameters['initial_state']
        if 'fluxes' not in initial_state:
            initial_state['fluxes'] = DEFAULT_INITIAL_FLUXES
        porin_kcat = initial_parameters.get('porin_kcat', 1e-4)
        porin_km = initial_parameters.get('porin_km', 0.6)
        acrABTolC_kcat = initial_parameters.get('acrABTolC_kcat', 2e-4)
        acrABTolC_km = initial_parameters.get('acrABTolC_km', 0.6)
        parameters = {
            'reactions': {
                'antibiotic_import': {
                    'stoichiometry': {
                        ('internal', 'antibiotic'): 1,
                        ('external', 'antibiotic'): -1,
                    },
                    'is_reversible': False,
                    'catalyzed by': [('internal', 'porin')],
                },
                'antibiotic_export': {
                    'stoichiometry': {
                        ('internal', 'antibiotic'): -1,
                        ('external', 'antibiotic'): 1,
                    },
                    'is_reversible': False,
                    'catalyzed by': [
                        ('internal', 'AcrAB-TolC')],
                },
            },
            'kinetic_parameters': {
                'antibiotic_import': {
                    ('internal', 'porin'): {
                        'kcat_f': porin_kcat,
                        ('external', 'antibiotic'): porin_km,
                    },
                },
                'antibiotic_export': {
                    ('internal', 'AcrAB-TolC'): {
                        'kcat_f': acrABTolC_kcat,
                        ('internal', 'antibiotic'): acrABTolC_km,
                    },
                },
            },
            'initial_state': initial_state,
            'ports': {
                'internal': [
                    'porin',
                    'AcrAB-TolC',
                    'antibiotic',
                ],
                'external': ['antibiotic'],
            },
        }

        super(AntibioticTransport, self).__init__(parameters)

    def ports_schema(self):
        emit = {
            'internal': ['antibiotic'],
            'external': ['antibiotic']}
        set_update = {
            'exchange': ['antibiotic'],
            'fluxes': [
                'antibiotic_import',
                'antibiotic_export']}

        # update convenience kinetics schema
        schema = super(AntibioticTransport, self).ports_schema()
        for port, states in self.ports.items():
            for state_id in states:
                if port in emit:
                    if state_id in emit[port]:
                        schema[port][state_id]['_emit'] = True
                if port in set_update:
                    if state_id in set_update[port]:
                        schema[port][state_id]['_updater'] = 'set'

        return schema

def run_antibiotic_transport():
    process = AntibioticTransport()
    settings = {
        'total_time': 4000,
        'environment': {
            'volume': 1e-15,
            'states': ['antibiotic'],
            'environment_port': 'external',
            'exchange_port': 'exchange'},
    }
    return simulate_process_in_experiment(process, settings)


def test_antibiotic_transport():
    timeseries = run_antibiotic_transport()
    flattened = flatten_timeseries(timeseries)
    reference = load_timeseries(
        os.path.join(REFERENCE_DATA_DIR, NAME + '.csv'))
    assert_timeseries_close(flattened, reference)


def main():
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    timeseries = run_antibiotic_transport()
    plot_settings = {}
    plot_simulation_output(timeseries, plot_settings, out_dir)
    save_timeseries(timeseries, out_dir)


if __name__ == '__main__':
    main()
