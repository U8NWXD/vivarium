from __future__ import absolute_import, division, print_function

import os
import copy

from vivarium.utils.dict_utils import keys_list
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)
from vivarium.data.nucleotides import nucleotides
from vivarium.utils.units import units


NAME = 'degradation'

def all_subkeys(d):
    subkeys = set([])
    for ase in d.keys():
        subkeys = subkeys.union(set(d[ase].keys()))
    return list(subkeys)

def kinetics(E, S, kcat, km):
    return kcat * E * S / (S + km)

DEFAULT_TRANSCRIPT_DEGRADATION_KM = 1e-23

class RnaDegradation(Process):
    defaults = {
        'sequences': {
            'oA': 'GCC',
            'oAZ': 'GCCGUGCAC',
            'oB': 'AGUUGA',
            'oBY': 'AGUUGACGG'},

        'catalysis_rates': {
            'endoRNAse': 0.1},

        'degradation_rates': {
            'transcripts': {
                'endoRNAse': {
                    'oA': DEFAULT_TRANSCRIPT_DEGRADATION_KM,
                    'oAZ': DEFAULT_TRANSCRIPT_DEGRADATION_KM,
                    'oB': DEFAULT_TRANSCRIPT_DEGRADATION_KM,
                    'oBY': DEFAULT_TRANSCRIPT_DEGRADATION_KM}}},
        'global_deriver_key': 'global_deriver',
    }

    def __init__(self, initial_parameters={}):
        self.default_parameters = self.defaults

        self.derive_defaults(initial_parameters, 'sequences', 'transcript_order', keys_list)
        self.derive_defaults(initial_parameters, 'catalysis_rates', 'protein_order', keys_list)

        self.parameters = copy.deepcopy(self.default_parameters)
        self.parameters.update(initial_parameters)

        self.sequences = self.parameters['sequences']
        self.catalysis_rates = self.parameters['catalysis_rates']
        self.degradation_rates = self.parameters['degradation_rates']
        self.transcript_order = self.parameters['transcript_order']
        self.protein_order = self.parameters['protein_order']
        self.molecule_order = list(nucleotides.values())

        self.partial_transcripts = {
            transcript: 0
            for transcript in self.transcript_order}

        self.global_deriver_key = self.or_default(
            initial_parameters, 'global_deriver_key')

        self.ports = {
            'transcripts': self.transcript_order,
            'proteins': self.protein_order,
            'molecules': self.molecule_order,
            'global': ['mmol_to_counts']}

        super(RnaDegradation, self).__init__(self.ports, self.parameters)


    def ports_schema(self):
        default_state = {
            'transcripts': {
                transcript: 1e3
                for transcript in self.transcript_order},
            'proteins': {
                protein: 1e0
                for protein in self.protein_order},
            'molecules': {
                nucleotide: 1e4
                for nucleotide in self.molecule_order}}
        emit_keys = {
            'transcripts': self.transcript_order,
            'proteins': self.protein_order,
            'molecules': self.molecule_order,
            'global': []}

        schema = {}
        for port, states in self.ports.items():
            schema[port] = {state: {} for state in states}
            if port in default_state:
                for state_id, value in default_state[port].items():
                    schema[port][state_id]['_default'] = value
            if port in emit_keys:
                for state_id in emit_keys[port]:
                    schema[port][state_id]['_emit'] = True
                    
        return schema

    def derivers(self):
        return {
            self.global_deriver_key: {
                'deriver': 'globals',
                'port_mapping': {
                    'global': 'global'},
                'config': {
                    'width': 1.11}}}

    def next_update(self, timestep, states):
        transcripts = states['transcripts']
        proteins = states['proteins']
        molecules = states['molecules']
        mmol_to_counts = states['global']['mmol_to_counts'] * units.L / units.mmol

        delta_transcripts = {
            transcript: 0
            for transcript in self.transcript_order}

        for protein, kcat in self.catalysis_rates.items():
            for transcript, km in self.degradation_rates['transcripts'][protein].items():
                km *= units.mole / units.fL
                delta_transcripts[transcript] += kinetics(
                    proteins[protein] / mmol_to_counts,
                    transcripts[transcript] / mmol_to_counts,
                    kcat,
                    km)

        degradation_levels = {
            transcript: (
                level * mmol_to_counts * timestep).magnitude + self.partial_transcripts[transcript]
            for transcript, level in delta_transcripts.items()}

        transcript_counts = {
            transcript: -int(level)
            for transcript, level in degradation_levels.items()}

        self.partial_transcripts = {
            transcript: level - int(level)
            for transcript, level in degradation_levels.items()}

        delta_molecules = {
            molecule: 0
            for molecule in self.molecule_order}

        for transcript, count in transcript_counts.items():
            sequence = self.sequences[transcript]
            for base in sequence:
                delta_molecules[nucleotides[base]] -= count

        return {
            'transcripts': transcript_counts,
            'molecules': delta_molecules}


def test_rna_degradation(end_time=100):
    parameters = {
        'catalysis_rates': {
            'endoRNAse': 0.1}}
    rna_degradation = RnaDegradation(parameters)
    settings = {
        'timestep': 1,
        'total_time': end_time}
    return simulate_process(rna_degradation, settings)


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    plot_settings = {}
    timeseries = test_rna_degradation()
    plot_simulation_output(timeseries, plot_settings, out_dir)
