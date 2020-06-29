from __future__ import absolute_import, division, print_function

import os
import sys
import copy
import random
import argparse

from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units
from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    COMPARTMENT_OUT_DIR
)

# data
from vivarium.data.amino_acids import amino_acids

# processes
from vivarium.processes.Endres2006_chemoreceptor import (
    ReceptorCluster,
    get_exponential_random_timeline
)
from vivarium.processes.Mears2014_flagella_activity import FlagellaActivity
from vivarium.processes.transcription import Transcription, UNBOUND_RNAP_KEY
from vivarium.processes.translation import Translation, UNBOUND_RIBOSOME_KEY
from vivarium.processes.degradation import RnaDegradation
from vivarium.processes.complexation import Complexation
from vivarium.processes.tree_mass import TreeMass
from vivarium.compartments.flagella_expression import (
    get_flagella_expression_config,
    get_flagella_initial_state,
    plot_gene_expression_output,
)



NAME = 'chemotaxis_flagella'


class ChemotaxisVariableFlagella(Compartment):

    defaults = {
        'n_flagella': 5,
        'ligand_id': 'MeAsp',
        'initial_ligand': 0.1,
    }

    def __init__(self, config):
        self.config = config

        n_flagella = config.get(
            'n_flagella',
            self.defaults['n_flagella'])
        ligand_id = config.get(
            'ligand_id',
            self.defaults['ligand_id'])
        initial_ligand = config.get(
            'initial_ligand',
            self.defaults['initial_ligand'])

        self.config['receptor'] = {
            'ligand_id': ligand_id,
            'initial_ligand': initial_ligand}

        self.config['flagella'] = {
            'n_flagella': n_flagella}

    def generate_processes(self, config):
        receptor = ReceptorCluster(config['receptor'])
        flagella = FlagellaActivity(config['flagella'])

        return {
            'receptor': receptor,
            'flagella': flagella}

    def generate_topology(self, config):
        boundary_path = ('boundary',)
        external_path = boundary_path + ('external',)
        return {
            'receptor': {
                'external': external_path,
                'internal': ('cell',)},
            'flagella': {
                'internal': ('internal',),
                'membrane': ('membrane',),
                'internal_counts': ('proteins',),
                'flagella': ('flagella',),
                'boundary': boundary_path},
        }



class ChemotaxisExpressionFlagella(Compartment):

    defaults = {
        'n_flagella': 5,
        'ligand_id': 'MeAsp',
        'initial_ligand': 0.1,
        'initial_mass': 1339.0 * units.fg,
        'config': {
            'transcription': get_flagella_expression_config({})['transcription'],
            'translation': get_flagella_expression_config({})['translation'],
            'degradation': get_flagella_expression_config({})['degradation'],
            'complexation': get_flagella_expression_config({})['complexation'],
        }
    }

    def __init__(self, config=None):
        if config is None:
            config = {}
        self.config = copy.deepcopy(self.defaults['config'])
        deep_merge(self.config, config)

        self.initial_mass = config.get(
            'initial_mass',
            self.defaults['initial_mass'])

        n_flagella = config.get(
            'n_flagella',
            self.defaults['n_flagella'])
        ligand_id = config.get(
            'ligand_id',
            self.defaults['ligand_id'])
        initial_ligand = config.get(
            'initial_ligand',
            self.defaults['initial_ligand'])

        # add receptor and flagella configs
        self.config['receptor'] = {
            'ligand_id': ligand_id,
            'initial_ligand': initial_ligand}

        self.config['flagella'] = {
            'n_flagella': n_flagella}

    def generate_processes(self, config):
        receptor = ReceptorCluster(config['receptor'])
        flagella = FlagellaActivity(config['flagella'])

        # expression
        transcription = Transcription(config['transcription'])
        translation = Translation(config['translation'])
        degradation = RnaDegradation(config['degradation'])
        complexation = Complexation(config['complexation'])
        mass_deriver = TreeMass(config.get('mass_deriver', {
            'initial_mass': config.get('initial_mass', self.initial_mass)}))

        return {
            'receptor': receptor,
            'flagella': flagella,
            'transcription': transcription,
            'translation': translation,
            'degradation': degradation,
            'complexation': complexation,
            'mass_deriver': mass_deriver,
        }

    def generate_topology(self, config):
        boundary_path = ('boundary',)
        external_path = boundary_path + ('external',)
        return {

            'receptor': {
                'external': external_path,
                'internal': ('cell',)},

            'flagella': {
                'internal': ('internal',),
                'membrane': ('membrane',),
                'internal_counts': ('proteins',),
                'flagella': ('flagella',),
                'boundary': boundary_path},

            'transcription': {
                'chromosome': ('chromosome',),
                'molecules': ('internal',),
                'proteins': ('proteins',),
                'transcripts': ('transcripts',),
                'factors': ('concentrations',),
                'global': boundary_path},

            'translation': {
                'ribosomes': ('ribosomes',),
                'molecules': ('internal',),
                'transcripts': ('transcripts',),
                'proteins': ('proteins',),
                'concentrations': ('concentrations',),
                'global': boundary_path},

            'degradation': {
                'transcripts': ('transcripts',),
                'proteins': ('proteins',),
                'molecules': ('internal',),
                'global': boundary_path},

            'complexation': {
                'monomers': ('proteins',),
                'complexes': ('proteins',),
                'global': boundary_path},

            'mass_deriver': {
                'global': boundary_path},
        }


def test_expression_chemotaxis(
        n_flagella=5,
        total_time=10,
        out_dir='out'):

    environment_port = 'external'
    ligand_id = 'MeAsp'
    initial_conc = 0

    # configure timeline
    exponential_random_config = {
        'ligand': ligand_id,
        'environment_port': environment_port,
        'time': total_time,
        'timestep': 1,
        'initial_conc': initial_conc,
        'base': 1+4e-4,
        'speed': 14}

    # make the compartment
    config = {
        'external_path': (environment_port,),
        'ligand_id': ligand_id,
        'initial_ligand': initial_conc,
        'n_flagella': n_flagella}
    compartment = ChemotaxisExpressionFlagella(config)

    # run experiment
    initial_state = get_flagella_initial_state({
        'molecules': 'internal'})
    experiment_settings = {
        'initial_state': initial_state,
        'timeline': {
            'timeline': get_exponential_random_timeline(
                exponential_random_config),
            'ports': {'external': ('boundary', 'external')}},
    }
    timeseries = simulate_compartment_in_experiment(
        compartment,
        experiment_settings)

    # plot settings for the simulations
    plot_settings = {
        'max_rows': 30,
        'remove_zeros': True,
        'skip_ports': ['chromosome', 'ribosomes']
    }
    plot_simulation_output(
        timeseries,
        plot_settings,
        out_dir)

    # gene expression plot
    plot_config = {
        'ports': {
            'transcripts': 'transcripts',
            'proteins': 'proteins',
            'molecules': 'internal'}}
    plot_gene_expression_output(
        timeseries,
        plot_config,
        out_dir)



def test_variable_chemotaxis(
        n_flagella=5,
        total_time=10,
        out_dir='out'):

    environment_port = 'external'
    ligand_id = 'MeAsp'
    initial_conc = 0

    # configure timeline
    exponential_random_config = {
        'ligand': ligand_id,
        'environment_port': environment_port,
        'time': total_time,
        'timestep': 1,
        'initial_conc': initial_conc,
        'base': 1+4e-4,
        'speed': 14}

    # make the compartment
    config = {
        'external_path': (environment_port,),
        'ligand_id': ligand_id,
        'initial_ligand': initial_conc,
        'n_flagella': n_flagella}
    compartment = ChemotaxisVariableFlagella(config)

    # run experiment
    experiment_settings = {
        'timeline': {
            'timeline': get_exponential_random_timeline(exponential_random_config),
            'ports': {'external': ('boundary', 'external')}},
    }
    timeseries = simulate_compartment_in_experiment(compartment, experiment_settings)

    # plot settings for the simulations
    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
    }
    plot_simulation_output(
        timeseries,
        plot_settings,
        out_dir)


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='variable flagella')
    parser.add_argument('--variable', '-v', action='store_true', default=False)
    parser.add_argument('--expression', '-e', action='store_true', default=False)
    parser.add_argument('--flagella', '-f', type=int, default=5)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.variable or no_args:
        variable_out_dir = os.path.join(out_dir, 'variable')
        make_dir(variable_out_dir)
        test_variable_chemotaxis(
            n_flagella=args.flagella,
            total_time=60,
            out_dir=variable_out_dir)
    elif args.expression:
        expression_out_dir = os.path.join(out_dir, 'expression')
        make_dir(expression_out_dir)
        test_expression_chemotaxis(
            n_flagella=args.flagella,
            # a cell cycle of 2520 sec is expected to express 8 flagella.
            # 2 flagella expected in 630 seconds.
            total_time=630,
            out_dir=expression_out_dir)
