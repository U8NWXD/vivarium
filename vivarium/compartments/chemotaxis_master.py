from __future__ import absolute_import, division, print_function

import os

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    plot_compartment_topology,
    COMPARTMENT_OUT_DIR
)
from vivarium.compartments.gene_expression import plot_gene_expression_output
from vivarium.compartments.flagella_expression import get_flagella_expression_config

# processes
from vivarium.processes.metabolism import (
    Metabolism,
    get_iAF1260b_config
)
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config
)
from vivarium.processes.transcription import Transcription
from vivarium.processes.translation import Translation
from vivarium.processes.degradation import RnaDegradation
from vivarium.processes.complexation import Complexation
from vivarium.processes.Endres2006_chemoreceptor import ReceptorCluster
from vivarium.processes.Mears2014_flagella_activity import FlagellaActivity
from vivarium.processes.membrane_potential import MembranePotential
from vivarium.processes.division_volume import DivisionVolume


NAME = 'chemotaxis_master'


class ChemotaxisMaster(Compartment):

    defaults = {
        'transport': get_glc_lct_config(),
        'boundary_path': ('boundary',)
    }

    def __init__(self, config):
        self.config = config
        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])

        self.transport_config = self.config.get('transport', self.defaults['transport'])
        self.transport_config['global_deriver_config'] = {
            'type': 'globals',
            'source_port': self.boundary_path,
            'derived_port': self.boundary_path,
            'global_port': self.boundary_path,
            'keys': []}

    def generate_processes(self, config):
        ## Declare the processes.
        # Transport
        # load the kinetic parameters
        transport_config = config.get('transport', self.transport_config)
        transport = ConvenienceKinetics(transport_config)
        target_fluxes = transport.kinetic_rate_laws.reaction_ids

        # Metabolism
        # get target fluxes from transport
        # load regulation function
        metabolism_config = config.get('metabolism', get_iAF1260b_config())
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # flagella expression
        flg_expression_config = get_flagella_expression_config({})
        transcription = Transcription(flg_expression_config['transcription'])
        translation = Translation(flg_expression_config['translation'])
        degradation = RnaDegradation(flg_expression_config['degradation'])
        complexation = Complexation(flg_expression_config['complexation'])

        # chemotaxis -- flagella activity, receptor activity, and PMF
        receptor_parameters = {'ligand': 'GLC'}
        receptor_parameters.update(config)
        receptor = ReceptorCluster(config.get('receptor', receptor_parameters))
        flagella = FlagellaActivity(config.get('flagella', {}))
        PMF = MembranePotential(config.get('PMF', {}))

        # Division
        # get initial volume from metabolism
        division_config = config.get('division', {})
        division_config.update({'initial_state': metabolism.initial_state})
        division = DivisionVolume(division_config)

        return {
            'PMF': PMF,
            'receptor': receptor,
            'transport': transport,
            'transcription': transcription,
            'translation': translation,
            'degradation': degradation,
            'complexation': complexation,
            'metabolism': metabolism,
            'flagella': flagella,
            'division': division}


    def generate_topology(self, config):
        boundary_path = config.get('boundary_path', self.boundary_path)

        return {
            'transport': {
                'internal': ('internal',),
                'external': boundary_path,
                'exchange': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': boundary_path},

            'metabolism': {
                'internal': ('internal',),
                'external': boundary_path,
                'reactions': ('reactions',),
                'exchange': ('exchange',),
                'flux_bounds': ('flux_bounds',),
                'global': boundary_path},

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

            'receptor': {
                'boundary': boundary_path,
                'internal': ('internal',)},

            'flagella': {
                'internal': ('internal',),
                'membrane': ('membrane',),
                'flagella_counts': ('proteins',),
                'flagella_activity': ('flagella_activity',),
                'external': boundary_path},

            'PMF': {
                'external': boundary_path,
                'membrane': ('membrane',),
                'internal': ('internal',)},

            'division': {
                'global': boundary_path}}

def run_chemotaxis_master(out_dir):
    total_time = 5
    compartment = ChemotaxisMaster({})

    # save the topology network
    settings = {'show_ports': True}
    plot_compartment_topology(
        compartment,
        settings,
        out_dir)

    timeseries = test_chemotaxis_master(total_time)
    volume_ts = timeseries['boundary']['volume']
    print('growth: {}'.format(volume_ts[-1]/volume_ts[0]))

    # plots
    plot_settings = {
        'max_rows': 60,
        'remove_zeros': True,
        'overlay': {'reactions': 'flux_bounds'},
        'skip_ports': ['prior_state', 'null']}
    plot_simulation_output(timeseries, plot_settings, out_dir)

    gene_exp_plot_config = {
        'name': 'flagella_expression',
        'ports': {
            'transcripts': 'transcripts',
            'proteins': 'proteins',
            'molecules': 'internal'}}
    plot_gene_expression_output(
        timeseries,
        gene_exp_plot_config,
        out_dir)

def test_chemotaxis_master(total_time=10):
    compartment_config = {
        'external_path': ('external',),
        'exchange_path': ('exchange',),
        'global_path': ('global',),
        'agents_path': ('..', '..', 'cells',)}
    compartment = ChemotaxisMaster(compartment_config)

    settings = {
        'timestep': 1,
        'total_time': total_time}
    return simulate_compartment_in_experiment(compartment, settings)


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_chemotaxis_master(out_dir)
