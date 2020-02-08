import os
from vivarium.utils.units import units

from scipy import constants

from vivarium.data.proteins import GFP
from vivarium.data.chromosome import gfp_plasmid_config
from vivarium.states.chromosome import Chromosome, Promoter, rna_bases, sequence_monomers
from vivarium.processes.translation import generate_template
from vivarium.composites.gene_expression import compose_gene_expression, plot_gene_expression_output
from vivarium.environment.make_media import Media

def degradation_sequences(sequence, promoters):
    return {
        promoter.last_terminator().product[0]: rna_bases(sequence_monomers(
            sequence,
            promoter.position,
            promoter.last_terminator().position))
        for promoter_key, promoter in promoters.items()}

def generate_gfp_compartment(config):
    media = Media()
    PURE = {
        key: value * units.mmol / units.L
        for key, value in media.get_saved_media('PURE_Fuji_2014').items()}

    # TODO: deal with volume
    volume = 1e-15 * units.L
    avogadro = constants.N_A * 1 / units.mol
    mmol_to_count = avogadro.to('1/mmol') * volume.to('L')
    
    print(mmol_to_count)

    PURE_counts = {
        key: int(value * mmol_to_count)
        for key, value in PURE.items()}

    print(PURE)
    print(PURE_counts)

    plasmid = Chromosome(gfp_plasmid_config)
    sequences = plasmid.product_sequences()

    print(sequences)

    gfp_config = {

        'transcription': {

            'sequence': gfp_plasmid_config['sequence'],
            'templates': gfp_plasmid_config['promoters'],
            'genes': gfp_plasmid_config['genes'],
            'promoter_affinities': {
                'T7': 0.5},

            'advancement_rate': 10.0,
            'elongation_rate': 50},

        'translation': {

            'sequences': {
                'GFP_RNA': GFP.sequence},
            'templates': {
                'GFP_RNA': generate_template(
                    'GFP_RNA', len(GFP.sequence), ['GFP'])},
            'transcript_affinities': {
                'GFP_RNA': 0.1},

            'elongation_rate': 22,
            'advancement_rate': 10.0},

        'degradation': {
            
            'sequences': sequences,
            'catalysis_rates': {
                'endoRNAse': 8.0},
            'degradation_rates': {
                'transcripts': {
                    'endoRNAse': {
                        'GFP_RNA': 1e-23}}}},

        'initial_state': {
            'molecules': PURE_counts,
            'transcripts': {'GFP_RNA': 0},
            'proteins': {'GFP': 0, 'endoRNAse': 1}}}

    return compose_gene_expression(gfp_config)

if __name__ == '__main__':
    from vivarium.actor.process import load_compartment, simulate_compartment, convert_to_timeseries

    out_dir = os.path.join('out', 'tests', 'gfp_expression_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # load the compartment
    gfp_expression_compartment = load_compartment(generate_gfp_compartment)

    # run simulation
    settings = {
        'total_time': 40}
    saved_state = simulate_compartment(gfp_expression_compartment, settings)
    del saved_state[0]  # remove the first state
    timeseries = convert_to_timeseries(saved_state)
    plot_gene_expression_output(timeseries, 'gfp_expression', out_dir)
    