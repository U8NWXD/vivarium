from __future__ import absolute_import, division, print_function

import os

from vivarium.core.tree import Compartment
from vivarium.core.composition import (
    get_derivers,
    simulate_with_environment,
    plot_simulation_output, load_compartment)
from vivarium.compartments.gene_expression import plot_gene_expression_output

# processes
from vivarium.processes.division import Division, divide_condition
from vivarium.processes.metabolism import Metabolism, get_iAF1260b_config
from vivarium.processes.convenience_kinetics import ConvenienceKinetics, get_glc_lct_config
from vivarium.processes.transcription import Transcription
from vivarium.processes.translation import Translation
from vivarium.processes.degradation import RnaDegradation
from vivarium.processes.complexation import Complexation



def default_metabolism_config():
    metabolism_config = get_iAF1260b_config()
    metabolism_config.update({
        'moma': False,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0]}})
    return metabolism_config



class Master(Compartment):

    defaults = {
        'global_key': ('..', 'global'),
        'external_key': ('..', 'external'),
        'transport': get_glc_lct_config(),
        'metabolism': default_metabolism_config(),
    }

    def __init__(self, config):
        self.config = config
        self.global_key = config.get('global_key', self.defaults['global_key'])
        self.external_key = config.get('external_key', self.defaults['external_key'])

    def generate_processes(self, config):

        ## Declare the processes.
        # Transport
        # load the kinetic parameters
        transport_config = config.get('transport', self.defaults['transport'])
        transport = ConvenienceKinetics(transport_config)
        target_fluxes = transport.kinetic_rate_laws.reaction_ids

        # Metabolism
        # get target fluxes from transport
        # load regulation function
        metabolism_config = config.get('metabolism', self.defaults['metabolism'])
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # expression
        transcription_config = config.get('transcription', {})
        translation_config = config.get('translation', {})
        degradation_config = config.get('degradation', {})
        transcription = Transcription(transcription_config)
        translation = Translation(translation_config)
        degradation = RnaDegradation(degradation_config)
        complexation = Complexation(config.get('complexation', {}))

        # Division
        # get initial volume from metabolism
        division_config = config.get('division', {})
        division_config.update({'initial_state': metabolism.initial_state})
        division = Division(division_config)

        return {
            'transport': transport,
            'transcription': transcription,
            'translation': translation,
            'degradation': degradation,
            'complexation': complexation,
            'metabolism': metabolism,
            'division': division}

    def generate_topology(self, config):
        external_key = config.get('external_key', self.external_key)
        global_key = config.get('global_key', self.global_key)

        topology = {
            'transport': {
                'internal': ('metabolites',),
                'external': external_key,
                'exchange': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': global_key},

            'metabolism': {
                'internal': ('metabolites',),
                'external': external_key,
                'reactions': ('reactions',),
                'exchange': ('exchange',),
                'flux_bounds': ('flux_bounds',),
                'global': global_key},

            'transcription': {
                'chromosome': ('chromosome',),
                'molecules': ('metabolites',),
                'proteins': ('proteins',),
                'transcripts': ('transcripts',),
                'factors': ('concentrations',)},

            'translation': {
                'ribosomes': ('ribosomes',),
                'molecules': ('metabolites',),
                'transcripts': ('transcripts',),
                'proteins': ('proteins',),
                'concentrations': ('concentrations',)},

            'degradation': {
                'transcripts': ('transcripts',),
                'proteins': ('proteins,),
                'molecules': ('metabolites',),
                'global': global_key},

            'complexation': {
                'monomers': ('proteins',),
                'complexes': ('proteins',)},

            'division': {
                'global': global_key}}



if __name__ == '__main__':
    out_dir = os.path.join('out', 'tests', 'master_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    compartment = load_compartment(compose_master)

    # settings for simulation and plot
    options = compartment.configuration

    # define timeline
    timeline = [(2520, {})] # 2520 sec (42 min) is the expected doubling time in minimal media

    settings = {
        'environment_port': options['environment_port'],
        'exchange_port': options['exchange_port'],
        'environment_volume': 1e-13,  # L
        'timeline': timeline,
    }

    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'overlay': {'reactions': 'flux_bounds'},
        'skip_ports': ['prior_state', 'null']}

    expression_plot_settings = {
        'name': 'gene_expression',
        'ports': {
            'transcripts': 'transcripts',
            'molecules': 'metabolites',
            'proteins': 'proteins'}}

    # saved_state = simulate_compartment(compartment, settings)
    timeseries = simulate_with_environment(compartment, settings)
    volume_ts = timeseries['global']['volume']
    print('growth: {}'.format(volume_ts[-1]/volume_ts[0]))
    plot_gene_expression_output(timeseries, expression_plot_settings, out_dir)
    plot_simulation_output(timeseries, plot_settings, out_dir)
