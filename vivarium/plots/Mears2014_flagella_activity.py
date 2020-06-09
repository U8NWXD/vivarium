from __future__ import absolute_import, division, print_function

import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.patches import Patch



def plot_activity(output, out_dir='out', filename='motor_control'):
    # receptor_activities = output['receptor_activities']
    CheY_vec = output['internal']['CheY']
    CheY_P_vec = output['internal']['CheY_P']
    cw_bias_vec = output['internal']['cw_bias']
    motile_state_vec = output['internal']['motile_state']
    motile_force_vec = output['internal']['motile_force']
    flagella_activity = output['flagella_activity']['flagella']
    time_vec = output['time']

    # get flagella ids by order appearance
    flagella_ids = []
    for state in flagella_activity:
        flg_ids = list(state.keys())
        for flg_id in flg_ids:
            if flg_id not in flagella_ids:
                flagella_ids.append(flg_id)

    # make flagella activity grid
    activity_grid = np.zeros((len(flagella_ids), len(time_vec)))
    total_CW = np.zeros((len(time_vec)))
    for time_index, flagella_state in enumerate(flagella_activity):
        for flagella_id, rotation_states in flagella_state.items():

            # get this flagella's index
            flagella_index = flagella_ids.index(flagella_id)

            modified_rotation_state = 0
            CW_rotation_state = 0
            if rotation_states == -1:
                modified_rotation_state = 1
            elif rotation_states == 1:
                modified_rotation_state = 2
                CW_rotation_state = 1

            activity_grid[flagella_index, time_index] = modified_rotation_state
            total_CW += np.array(CW_rotation_state)

    # grid for cell state
    motile_state_grid = np.zeros((1, len(time_vec)))
    motile_state_grid[0, :] = motile_state_vec

    # set up colormaps
    # cell motile state
    cmap1 = colors.ListedColormap(['steelblue', 'lightgray', 'darkorange'])
    bounds1 = [-1, -1/3, 1/3, 1]
    norm1 = colors.BoundaryNorm(bounds1, cmap1.N)
    motile_legend_elements = [
        Patch(facecolor='steelblue', edgecolor='k', label='Run'),
        Patch(facecolor='darkorange', edgecolor='k', label='Tumble'),
        Patch(facecolor='lightgray', edgecolor='k', label='N/A')]

    # rotational state
    cmap2 = colors.ListedColormap(['lightgray', 'steelblue', 'darkorange'])
    bounds2 = [0, 0.5, 1.5, 2]
    norm2 = colors.BoundaryNorm(bounds2, cmap2.N)
    rotational_legend_elements = [
        Patch(facecolor='steelblue', edgecolor='k', label='CCW'),
        Patch(facecolor='darkorange', edgecolor='k', label='CW'),
        Patch(facecolor='lightgray', edgecolor='k', label='N/A')]

    # plot results
    cols = 1
    rows = 5
    plt.figure(figsize=(4 * cols, 1.5 * rows))

    # define subplots
    ax1 = plt.subplot(rows, cols, 1)
    ax2 = plt.subplot(rows, cols, 2)
    ax3 = plt.subplot(rows, cols, 3)
    ax4 = plt.subplot(rows, cols, 4)
    ax5 = plt.subplot(rows, cols, 5)

    # plot Che-P state
    ax1.plot(time_vec, CheY_vec, label='CheY')
    ax1.plot(time_vec, CheY_P_vec, label='CheY_P')
    ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax1.set_xticks([])
    ax1.set_xlim(time_vec[0], time_vec[-1])
    ax1.set_ylabel('concentration \n (uM)')

    # plot CW bias
    ax2.plot(time_vec, cw_bias_vec)
    ax2.set_xticks([])
    ax2.set_xlim(time_vec[0], time_vec[-1])
    ax2.set_ylabel('CW bias')

    # plot flagella states in a grid
    if len(activity_grid) > 0:
        ax3.imshow(activity_grid,
                   interpolation='nearest',
                   aspect='auto',
                   cmap=cmap2,
                   norm=norm2,
                   # extent=[-1,1,-1,1]
                   extent=[time_vec[0], time_vec[-1], len(flagella_ids)+0.5, 0.5]
                   )
        plt.locator_params(axis='y', nbins=len(flagella_ids))
        ax3.set_yticks(list(range(1, len(flagella_ids) + 1)))
        ax3.set_xticks([])
        ax3.set_ylabel('flagella #')

        # legend
        ax3.legend(
            handles=rotational_legend_elements,
            loc='center left',
            bbox_to_anchor=(1, 0.5))
    else:
        # no flagella
        ax3.set_axis_off()

    # plot cell motile state
    ax4.imshow(motile_state_grid,
               interpolation='nearest',
               aspect='auto',
               cmap=cmap1,
               norm=norm1,
               extent=[time_vec[0], time_vec[-1], 0, 1])
    ax4.set_yticks([])
    ax4.set_xticks([])
    ax4.set_ylabel('cell motile state')

    # legend
    ax4.legend(
        handles=motile_legend_elements,
        loc='center left',
        bbox_to_anchor=(1, 0.5))

    # plot motor thrust
    ax5.plot(time_vec, motile_force_vec)
    ax5.set_xlim(time_vec[0], time_vec[-1])
    ax5.set_ylabel('total motor thrust (pN)')
    ax5.set_xlabel('time (sec)')


    # save figure
    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.3)
    plt.savefig(fig_path + '.png', bbox_inches='tight')


def plot_motor_PMF(output, out_dir='out', figname='motor_PMF'):
    motile_state = output['motile_state']
    motile_force = output['motile_force']
    motile_torque = output['motile_torque']
    PMF = output['PMF']

    # plot results
    cols = 1
    rows = 1
    plt.figure(figsize=(10 * cols, 2 * rows))

    # define subplots
    ax1 = plt.subplot(rows, cols, 1)

    # plot motile_state
    ax1.plot(PMF, motile_force)
    ax1.set_xlabel('PMF (mV)')
    ax1.set_ylabel('force')

    # save figure
    fig_path = os.path.join(out_dir, figname)
    plt.subplots_adjust(wspace=0.7, hspace=0.3)
    plt.savefig(fig_path + '.png', bbox_inches='tight')