from __future__ import absolute_import, division, print_function

import math
import os

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    flatten_timeseries,
    save_timeseries,
    load_timeseries,
    REFERENCE_DATA_DIR,
    COMPARTMENT_OUT_DIR,
    assert_timeseries_close,
)
from vivarium.processes.antibiotic_transport import AntibioticTransport
from vivarium.processes.antibiotic_transport import (
    DEFAULT_INITIAL_STATE as ANTIBIOTIC_DEFAULT_INITIAL_STATE,
)
from vivarium.processes.death import DeathFreezeState
from vivarium.processes.division_volume import DivisionVolume
from vivarium.processes.growth import Growth
from vivarium.processes.ode_expression import ODE_expression


NAME = 'antibiotics_composite'
NUM_DIVISIONS = 3
DIVISION_TIME = 2400  # seconds to divide



class Antibiotics(Compartment):

    def __init__(self, config):
        self.config = config
        division_time = self.config.get('cell_cycle_division_time', 2400)

        # Expression Config
        transcription_config = self.config.setdefault('transcription_rates', {})
        transcription_config.setdefault('AcrAB-TolC_RNA', 1e-3)
        translation_config = self.config.setdefault('translation_rates', {})
        translation_config.setdefault('AcrAB-TolC', 1.0)
        degradation_config = self.config.setdefault('degradation_rates', {})
        degradation_config.setdefault('AcrAB-TolC', 1.0)
        degradation_config.setdefault('AcrAB-TolC_RNA', 1e-3)
        protein_map = self.config.setdefault('protein_map', {})
        protein_map.setdefault(
            'AcrAB-TolC', 'AcrAB-TolC_RNA')

        initial_state_config = self.config.setdefault(
            'initial_state', ANTIBIOTIC_DEFAULT_INITIAL_STATE)
        internal_initial_config = initial_state_config.setdefault(
            'internal', {})
        internal_initial_config['AcrAB-TolC'] = 0.0

        # Death Config
        checkers_config = self.config.setdefault('checkers', {})
        antibiotic_checker_config = checkers_config.setdefault(
            'antibiotic', {})
        antibiotic_checker_config.setdefault('antibiotic_threshold', 0.09)

        # Growth Config
        # Growth rate calculated so that 2 = exp(DIVISION_TIME * rate)
        # because division process divides once cell doubles in size
        self.config.setdefault('growth_rate', math.log(2) / division_time)

    def generate_processes(self, config):
        # TODO -- use config to update self.config
        antibiotic_transport = AntibioticTransport(self.config)
        growth = Growth(self.config)
        expression = ODE_expression(self.config)
        death = DeathFreezeState(self.config)
        division = DivisionVolume(self.config)

        return {
            'antibiotic_transport': antibiotic_transport,
            'growth': growth,
            'expression': expression,
            'death': death,
            'division': division,
        }

    def generate_topology(self, config):
        return {
            'antibiotic_transport': {
                'internal': ('cell',),
                'external': ('environment',),
                'exchange': ('exchange',),
                'fluxes': ('fluxes',),
                'global': ('global',),
            },
            'growth': {
                'global': ('global',),
            },
            'expression': {
                'counts': ('cell_counts',),
                'internal': ('cell',),
                'external': ('environment',),
                'global': ('global',),
            },
            'division': {
                'global': ('global',),
            },
            'death': {
                'global': ('global',),
            },
        }



def run_antibiotics_composite():
    sim_settings = {
        'environment_port': ('environment',),
        'exchange_port': ('exchange',),
        'environment_volume': 1e-5,  # L
        'emit_step': 1,
        'total_time': DIVISION_TIME * NUM_DIVISIONS,
    }
    config = {
        'transcription_rates': {
            'AcrAB-TolC_RNA': 1e-3,
        },
        'degradation_rates': {
            # Set for on the order of 100 RNAs at equilibrium
            'AcrAB-TolC_RNA': 1.0,
            # Set so exporter concentration reaches equilibrium
            'AcrAB-TolC': 1e-3,
        },
        'checkers': {
            'antibiotic': {
                # Set so cell dies after first division
                'antibiotic_threshold': 10.0,
            },
        },
    }
    compartment = Antibiotics(config)
    return simulate_compartment_in_experiment(compartment, sim_settings)

def test_antibiotics_composite_similar_to_reference():
    timeseries = run_antibiotics_composite()
    flattened = flatten_timeseries(timeseries)
    reference = load_timeseries(
        os.path.join(REFERENCE_DATA_DIR, NAME + '.csv'))
    assert_timeseries_close(flattened, reference)


def main():
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    plot_settings = {
        'max_rows': 25,
    }

    timeseries = run_antibiotics_composite()
    plot_simulation_output(timeseries, plot_settings, out_dir)
    save_timeseries(timeseries, out_dir)


if __name__ == '__main__':
    main()
