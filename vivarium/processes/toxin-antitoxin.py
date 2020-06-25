from __future__ import absolute_import, division, print_function

import os

import numpy as np

from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)


NAME = 'toxin_antitoxin'

class ToxinAntitoxin(Process):
    mazF = 4
    defaults = {
        'initial_state': {
            'DNA': 1,
            'DNA_bound': 0,
            'mRNA': 0,
            'mazE': 2,
            'mazF': mazF,
            'mazEF': 0,
        },
        'parameters': {
            'mRNA_deg': np.log(2) / (2 * 60),
            'mazE_deg': np.log(2) / (30 * 60),
            'mazF_deg': np.log(2) / (4 * 60 * 60),
            'c_EFassoc': np.log(2) / 60,
            'c_EFdiss': np.log(2) / 30,
            'c_DNAassoc': np.log(2) / (25),  # taken from hipAB rate
            'c_DNAdiss': np.log(2) / (1),  # taken from hipAB rate
            'c_trsc': 0.0005,
            'c_trl_max': 1,
            'mazF_inhib': 1 + 20 / mazF,
        }
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        parameters = initial_parameters.get(
            'parameters', self.defaults['parameters'])

        super(ToxinAntitoxin, self).__init__(parameters)

    def ports_schema(self):
        schema = {'internal': {}}
        for state, value in self.defaults['initial_state'].items():
            schema['internal'][state] = {
                '_default': value,
                '_emit': True,
                '_updater': 'set',
            }
        return schema

    def next_update(self, timestep, states):
        internal = states['internal']
        DNA = internal['DNA']
        DNA_bound = internal['DNA_bound']
        mRNA = internal['mRNA']
        mazE = internal['mazE']
        mazF = internal['mazF']
        mazEF = internal['mazEF']


        # dynamic rates
        if mazF > 0:
            mazF_inhib = 1 + mazF / 30
        else:
            mazF_inhib = 1

        # # reduce trl rate  # TODO -- make this into a timeline
        # if step > 35000:
        #     c_trl_max = 0.1 / mazF_inhib
        # else:
        #     c_trl_max = 1 / mazF_inhib

        c_trl_mazE = 0.101 * self.parameters['c_trl_max']/mazF_inhib  # 1.01 from model
        c_trl_mazF = 0.039 * self.parameters['c_trl_max']/mazF_inhib  # .39 from model


        a = np.ndarray((10))
        # TODO change to a dictionary to avoid confusion
        a[0] = self.parameters['c_trsc'] * DNA
        a[1] = self.parameters['mRNA_deg'] * mRNA
        a[2] = c_trl_mazE * mRNA
        a[3] = c_trl_mazF * mRNA
        a[4] = self.parameters['mazE_deg'] * mazE
        a[5] = self.parameters['mazF_deg'] * mazF
        a[6] = self.parameters['c_EFassoc'] * mazE * mazF
        a[7] = self.parameters['c_EFdiss'] * mazEF
        a[8] = self.parameters['c_DNAassoc'] * mazEF * DNA
        a[9] = self.parameters['c_DNAdiss'] * DNA_bound

        atot = sum(a)

        r1 = np.random.random(1)
        r2 = np.random.random(1)

        tau = 1 / atot * np.log(1 / r1)
        pcut = atot * r2

        # choose reaction
        for n in range(len(a)):
            if np.cumsum(a)[n] > pcut:
                q = n
                break

        # execute reaction
        if q == 0:
            mRNA += 1
        elif q == 1:
            mRNA -= 1
        elif q == 2:
            mazE += 1
        elif q == 3:
            mazF += 1
        elif q == 4:
            mazE -= 1
        elif q == 5:
            mazF -= 1
        elif q == 6:
            if (mazE >= 2) & (mazF >= 4):
                mazEF += 1
                mazE -= 2
                mazF -= 4
        elif q == 7:
            mazEF -= 1
            mazE += 2
            mazF += 4
        elif q == 8:
            DNA_bound += 1
            DNA -= 1
            mazEF -= 1
        elif q == 9:
            DNA_bound -= 1
            DNA += 1
            mazEF += 1

        # t += tau  # TODO -- is this supports to change the timestep????
        # cell division
        # if t > division_time[-1] + 1800:
        # 	division_time.append(t[0])
        # 	mazE = divide_molecule(mazE)
        # 	mazF = divide_molecule(mazF)
        # 	mazEF = divide_molecule(mazEF)
        # 	mRNA = divide_molecule(mRNA)


        update = {
            'internal': {
                'mRNA': mRNA,
                'mazE': mazE,
                'mazF': mazF,
                'mazEF': mazEF,
                'DNA': DNA,
                'DNA_bound': DNA_bound,
            },
        }
        return update



def test_toxin_antitoxin(time=10):
    toxin_antitoxin = ToxinAntitoxin({})
    settings = {'total_time': time}
    return simulate_process(toxin_antitoxin, settings)



if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    timeseries = test_toxin_antitoxin(10000)
    plot_simulation_output(timeseries, {}, out_dir)
