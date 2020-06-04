from __future__ import absolute_import, division, print_function

import os
import random
import copy

import numpy as np
from numpy import linspace
import matplotlib.pyplot as plt

from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    PROCESS_OUT_DIR,
)


NAME = 'Vladimirov2008_motor'

class MotorActivity(Process):
    '''
    Model of motor activity from:
        Vladimirov, N., Lovdok, L., Lebiedz, D., & Sourjik, V. (2008).
        Dependence of bacterial chemotaxis on gradient shape and adaptation rate.
    '''

    defaults = {
        'parameters': {
            # 'k_A': 5.0,  #
            'k_y': 100.0,  # 1/uM/s
            'k_z': 30.0,  # / CheZ,
            'gamma_Y': 0.1,
            'k_s': 0.45,  # scaling coefficient
            'adapt_precision': 3,  # scales CheY_P to cluster activity
            # motor
            'mb_0': 0.65,  # steady state motor bias (Cluzel et al 2000)
            'n_motors': 5,
            'cw_to_ccw': 0.83,  # 1/s (Block1983) motor bias, assumed to be constant
            'timestep': 0.1,
        },
        'initial_state': {
            'internal': {
                # response regulator proteins
                'CheY_tot': 9.7,  # (uM) #0.0097,  # (mM) 9.7 uM = 0.0097 mM
                'CheY_P': 0.5,
                'CheZ': 0.01*100,  # (uM) #phosphatase 100 uM = 0.1 mM (0.01 scaling from RapidCell1.4.2)
                'CheA': 0.01*100,  # (uM) #100 uM = 0.1 mM (0.01 scaling from RapidCell1.4.2)
                # sensor activity
                'chemoreceptor_activity': 1/3,
                # motor activity
                'ccw_motor_bias': 0.5,
                'ccw_to_cw': 0.5,
                'motor_state': 1,  # motor_state 1 for tumble, 0 for run
            },
            'boundary': {
                'thrust': 0,
                'torque': 0,
            }}
    }

    def __init__(self, initial_parameters={}):

        ports = {
            'internal': [
                'chemoreceptor_activity',
                'CheA',
                'CheZ',
                'CheY_tot',
                'CheY_P',
                'ccw_motor_bias',
                'ccw_to_cw',
                'motor_state'],
            'boundary': [
                'thrust',
                'torque'],
            'external': []}

        parameters = self.defaults['parameters']
        parameters.update(initial_parameters)

        super(MotorActivity, self).__init__(ports, parameters)

    def ports_schema(self):
        default_state = self.defaults['initial_state']
        set_states = {
            'internal': [
                'ccw_motor_bias',
                'ccw_to_cw',
                'motor_state',
                'CheA',
                'CheY_P'],
            'boundary': [
                'thrust',
                'torque']}
        emitter_states = {
            'internal': [
                'ccw_motor_bias',
                'ccw_to_cw',
                'motor_state',
                'CheA',
                'CheY_P'],
            'boundary': [
                'thrust',
                'torque']}

        schema = {}
        for port, states in self.ports.items():
            schema[port] = {state: {} for state in states}
            if port in set_states:
                for state_id in set_states[port]:
                    schema[port][state_id]['_updater'] = 'set'
            if port in emitter_states:
                for state_id in emitter_states[port]:
                    schema[port][state_id]['_emit'] = True
            if port in default_state:
                for state_id, value in default_state[port].items():
                    schema[port][state_id]['_default'] = value
        return schema

    def next_update(self, timestep, states):
        '''
        CheY phosphorylation model from:
            Kollmann, M., Lovdok, L., Bartholome, K., Timmer, J., & Sourjik, V. (2005).
            Design principles of a bacterial signalling network. Nature.
        Motor switching model from:
            Scharf, B. E., Fahrner, K. A., Turner, L., and Berg, H. C. (1998).
            Control of direction of flagellar rotation in bacterial chemotaxis. PNAS.

        An increase of attractant inhibits CheA activity (chemoreceptor_activity),
        but subsequent methylation returns CheA activity to its original level.
        TODO -- add CheB phosphorylation
        '''

        internal = states['internal']
        P_on = internal['chemoreceptor_activity']
        motor_state_current = internal['motor_state']

        # parameters
        adapt_precision = self.parameters['adapt_precision']
        k_y = self.parameters['k_y']
        k_s = self.parameters['k_s']
        k_z = self.parameters['k_z']
        gamma_Y = self.parameters['gamma_Y']
        mb_0 = self.parameters['mb_0']
        cw_to_ccw = self.parameters['cw_to_ccw']

        ## Kinase activity
        # relative steady-state concentration of phosphorylated CheY.
        CheY_P = adapt_precision * k_y * k_s * P_on / (k_y * k_s * P_on + k_z + gamma_Y)  # CheZ cancels out of k_z

        ## Motor switching
        # CCW corresponds to run. CW corresponds to tumble
        ccw_motor_bias = mb_0 / (CheY_P * (1 - mb_0) + mb_0)  # (1/s)
        ccw_to_cw = cw_to_ccw * (1 / ccw_motor_bias - 1)  # (1/s)

        if motor_state_current == 0:  # 0 for run
            # switch to tumble (cw)?
            prob_switch = ccw_to_cw * timestep
            if np.random.random(1)[0] <= prob_switch:
                motor_state = 1
                thrust, torque = tumble()
            else:
                motor_state = 0
                thrust, torque = run()

        elif motor_state_current == 1:  # 1 for tumble
            # switch to run (ccw)?
            prob_switch = cw_to_ccw * timestep
            if np.random.random(1)[0] <= prob_switch:
                motor_state = 0
                [thrust, torque] = run()
            else:
                motor_state = 1
                [thrust, torque] = tumble()

        return {
            'internal': {
                'ccw_motor_bias': ccw_motor_bias,
                'ccw_to_cw': ccw_to_cw,
                'motor_state': motor_state,
                'CheY_P': CheY_P},
            'boundary': {
                'thrust': thrust,
                'torque': torque
            }}

def tumble():
    thrust = 100  # pN
    tumble_jitter = 2.5  # added to angular velocity
    torque = random.normalvariate(0, tumble_jitter)
    return [thrust, torque]

def run():
    # average thrust = 200 pN according to:
    # Berg, Howard C. E. coli in Motion. Under "Torque-Speed Dependence"
    thrust  = 250  # pN
    torque = 0.0
    return [thrust, torque]


def test_motor_control(total_time=10):
    motor = MotorActivity({})
    experiment_settings = {
        'total_time': total_time,
        'timestep': 0.01}
    return simulate_process_in_experiment(motor, experiment_settings)

def test_variable_receptor():
    motor = MotorActivity()
    state = motor.default_state()
    timestep = 1
    receptor_activities = linspace(0.0, 1.0, 501).tolist()
    CheY_P_vec = []
    ccw_motor_bias_vec = []
    ccw_to_cw_vec = []
    motor_state_vec = []
    for activity in receptor_activities:
        state['internal']['chemoreceptor_activity'] = activity
        update = motor.next_update(timestep, state)
        CheY_P = update['internal']['CheY_P']
        ccw_motor_bias = update['internal']['ccw_motor_bias']
        ccw_to_cw = update['internal']['ccw_to_cw']
        motile_state = update['internal']['motor_state']

        CheY_P_vec.append(CheY_P)
        ccw_motor_bias_vec.append(ccw_motor_bias)
        ccw_to_cw_vec.append(ccw_to_cw)
        motor_state_vec.append(motile_state)

    # check ccw_to_cw bias is strictly increasing with increased receptor activity
    assert all(i < j for i, j in zip(ccw_to_cw_vec, ccw_to_cw_vec[1:]))

    return {
        'receptor_activities': receptor_activities,
        'CheY_P_vec': CheY_P_vec,
        'ccw_motor_bias_vec': ccw_motor_bias_vec,
        'ccw_to_cw_vec': ccw_to_cw_vec,
        'motor_state_vec': motor_state_vec}

def plot_motor_control(timeseries, out_dir='out'):
    # TODO -- make this into an analysis figure
    expected_run = 0.42  # s (Berg) expected run length without chemotaxis
    expected_tumble = 0.14  # s (Berg)

    # receptor_activities = output['receptor_activities']
    CheY_P_vec = timeseries['internal']['CheY_P']
    ccw_motor_bias_vec = timeseries['internal']['ccw_motor_bias']
    ccw_to_cw_vec = timeseries['internal']['ccw_to_cw']
    motor_state_vec = timeseries['internal']['motor_state']
    time_vec = timeseries['time']

    # plot results
    cols = 1
    rows = 4
    plt.figure(figsize=(6 * cols, 1 * rows))

    ax1 = plt.subplot(rows, cols, 1)
    ax2 = plt.subplot(rows, cols, 2)
    ax3 = plt.subplot(rows, cols, 3)
    ax4 = plt.subplot(rows, cols, 4)

    ax1.plot(CheY_P_vec, 'b')
    ax2.plot(ccw_motor_bias_vec, 'b', label='ccw_motor_bias')
    ax2.plot(ccw_to_cw_vec, 'g', label='ccw_to_cw')

    # get length of runs, tumbles
    run_lengths = []
    tumble_lengths = []
    prior_state = 0
    state_start_time = 0
    for state, time in zip(motor_state_vec,time_vec):
        if state == 0:  # run
            if prior_state != 0:
                tumble_lengths.append(time - state_start_time)
                state_start_time = time
        elif state == 1:  # tumble
            if prior_state != 1:
                run_lengths.append(time - state_start_time)
                state_start_time = time
        prior_state = state

    avg_run_lengths = sum(run_lengths) / len(run_lengths)
    avg_tumble_lengths = sum(tumble_lengths) / len(tumble_lengths)

    # plot run distributions
    max_length = max(run_lengths + [1])
    bins = np.linspace(0, max_length, 30)
    ax3.hist([run_lengths], bins=bins, label=['run_lengths'], color=['b'])
    ax3.axvline(x=avg_run_lengths, color='k', linestyle='dashed', label='mean run')
    ax3.axvline(x=expected_run, color='r', linestyle='dashed', label='expected run')

    # plot tumble distributions
    max_length = max(tumble_lengths + [1])
    bins = np.linspace(0, max_length, 30)
    ax4.hist([tumble_lengths], bins=bins, label=['tumble_lengths'], color=['m'])
    ax4.axvline(x=avg_tumble_lengths, color='k', linestyle='dashed', label='mean tumble')
    ax4.axvline(x=expected_tumble, color='r', linestyle='dashed', label='expected tumble')

    # labels
    ax1.set_xticklabels([])
    ax1.set_ylabel("CheY_P", fontsize=10)

    ax2.set_xticklabels([])
    ax2.set_ylabel("motor bias", fontsize=10)
    ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax3.set_xlabel("motor state length (sec)")
    ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax4.set_xlabel("motor state length (sec)")
    ax4.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # save the figure
    fig_path = os.path.join(out_dir, 'motor_control')
    plt.subplots_adjust(wspace=0.7, hspace=0.5)
    plt.savefig(fig_path + '.png', bbox_inches='tight')

def plot_variable_receptor(output, out_dir='out'):
    receptor_activities = output['receptor_activities']
    CheY_P_vec = output['CheY_P_vec']
    ccw_motor_bias_vec = output['ccw_motor_bias_vec']
    ccw_to_cw_vec = output['ccw_to_cw_vec']

    # plot results
    cols = 1
    rows = 2
    plt.figure(figsize=(6 * cols, 1 * rows))

    ax1 = plt.subplot(rows, cols, 1)
    ax2 = plt.subplot(rows, cols, 2)

    ax1.plot(receptor_activities, CheY_P_vec, 'b')
    ax2.plot(receptor_activities, ccw_motor_bias_vec, 'b', label='ccw_motor_bias')
    ax2.plot(receptor_activities, ccw_to_cw_vec, 'g', label='ccw_to_cw')

    ax1.set_xticklabels([])
    ax1.set_ylabel("CheY_P", fontsize=10)
    ax2.set_xlabel("receptor activity \n P(on) ", fontsize=10)
    ax2.set_ylabel("motor bias", fontsize=10)
    ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    fig_path = os.path.join(out_dir, 'motor_variable_receptor')
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path + '.png', bbox_inches='tight')


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    output1 = test_motor_control(200)
    plot_motor_control(output1, out_dir)

    output2 = test_variable_receptor()
    plot_variable_receptor(output2, out_dir)
