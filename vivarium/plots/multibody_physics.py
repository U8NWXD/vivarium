from __future__ import absolute_import, division, print_function

import os
import math
import random

import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import hsv_to_rgb
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.collections import LineCollection



DEFAULT_BOUNDS = [10, 10]

# constants
PI = math.pi

# colors for phylogeny initial agents
HUES = [hue/360 for hue in np.linspace(0,360,30)]
DEFAULT_HUE = HUES[0]
DEFAULT_SV = [100.0/100.0, 70.0/100.0]

def check_plt_backend():
    # reset matplotlib backend for non-interactive plotting
    plt.close('all')
    if plt.get_backend() == 'TkAgg':
        matplotlib.use('Agg')


def plot_agent(ax, data, color):
    # location, orientation, length
    x_center = data['boundary']['location'][0]
    y_center = data['boundary']['location'][1]
    theta = data['boundary']['angle'] / PI * 180 + 90 # rotate 90 degrees to match field
    length = data['boundary']['length']
    width = data['boundary']['width']

    # get bottom left position
    x_offset = (width / 2)
    y_offset = (length / 2)
    theta_rad = math.radians(theta)
    dx = x_offset * math.cos(theta_rad) - y_offset * math.sin(theta_rad)
    dy = x_offset * math.sin(theta_rad) + y_offset * math.cos(theta_rad)

    x = x_center - dx
    y = y_center - dy

    # get color, convert to rgb
    rgb = hsv_to_rgb(color)

    # Create a rectangle
    rect = patches.Rectangle(
        (x, y), width, length, angle=theta, linewidth=2, edgecolor='w', facecolor=rgb)

    ax.add_patch(rect)


def plot_agents(ax, agents, agent_colors={}):
    '''
    - ax: the axis for plot
    - agents: a dict with {agent_id: agent_data} and
        agent_data a dict with keys location, angle, length, width
    - agent_colors: dict with {agent_id: hsv color}
    '''
    for agent_id, agent_data in agents.items():
        color = agent_colors.get(agent_id, [DEFAULT_HUE]+DEFAULT_SV)
        plot_agent(ax, agent_data, color)


def plot_snapshots(data, plot_config):
    '''
        - agents (dict): with {time: agent_data}
        - fields (dict): with {time: field_data}
        - config (dict): the environment config for the simulation
    '''
    check_plt_backend()

    n_snapshots = plot_config.get('n_snapshots', 6)
    out_dir = plot_config.get('out_dir', 'out')
    filename = plot_config.get('filename', 'snapshots')

    # get data
    agents = data.get('agents', {})
    fields = data.get('fields', {})
    config = data.get('config', {})
    bounds = config.get('bounds', DEFAULT_BOUNDS)
    edge_length_x = bounds[0]
    edge_length_y = bounds[1]

    # time steps that will be used
    if agents and fields:
        assert set(list(agents.keys())) == set(list(fields.keys())), 'agent and field times are different'
        time_vec = list(agents.keys())
    elif agents:
        time_vec = list(agents.keys())
    elif fields:
        time_vec = list(fields.keys())
    else:
        raise Exception('No agents or field data')

    time_indices = np.round(np.linspace(0, len(time_vec) - 1, n_snapshots)).astype(int)
    snapshot_times = [time_vec[i] for i in time_indices]

    # get fields id and range
    field_ids = []
    if fields:
        field_ids = list(fields[time_vec[0]].keys())
        field_range = {}
        for field_id in field_ids:
            field_min = min([field_data[field_id].min() for t, field_data in fields.items()])
            field_max = max([field_data[field_id].max() for t, field_data in fields.items()])
            field_range[field_id] = [field_min, field_max]

    # get agent ids
    agent_ids = set()
    if agents:
        for time, time_data in agents.items():
            current_agents = list(time_data.keys())
            agent_ids.update(current_agents)
        agent_ids = list(agent_ids)

        # set agent colors
        agent_colors = {}
        for agent_id in agent_ids:
            hue = random.choice(HUES)  # select random initial hue
            color = [hue] + DEFAULT_SV
            agent_colors[agent_id] = color

    # make the figure
    n_rows = max(len(field_ids), 1)
    n_cols = n_snapshots + 1  # one column for the colorbar
    fig = plt.figure(figsize=(12 * n_cols, 12 * n_rows))
    grid = plt.GridSpec(n_rows, n_cols, wspace=0.2, hspace=0.2)
    plt.rcParams.update({'font.size': 36})

    # plot snapshot data in each subsequent column
    for col_idx, (time_idx, time) in enumerate(zip(time_indices, snapshot_times)):
        if field_ids:
            for row_idx, field_id in enumerate(field_ids):

                ax = init_axes(fig, edge_length_x, edge_length_y, grid, row_idx, col_idx, time)

                # transpose field to align with agent
                field = np.transpose(np.array(fields[time][field_id])).tolist()
                vmin, vmax = field_range[field_id]
                im = plt.imshow(field,
                                origin='lower',
                                extent=[0, edge_length_x, 0, edge_length_y],
                                vmin=vmin,
                                vmax=vmax,
                                cmap='BuPu')

                if agents:
                    agents_now = agents[time]
                    plot_agents(ax, agents_now, agent_colors)

                # colorbar in new column after final snapshot
                if col_idx == n_snapshots-1:
                    cbar_col = col_idx + 1
                    ax = fig.add_subplot(grid[row_idx, cbar_col])
                    divider = make_axes_locatable(ax)
                    cax = divider.append_axes("left", size="5%", pad=0.0)
                    fig.colorbar(im, cax=cax, format='%.6f')
                    ax.axis('off')
        else:
            row_idx = 0
            ax = init_axes(fig, bounds[0], bounds[1], grid, row_idx, col_idx, time)
            if agents:
                agents_now = agents[time]
                plot_agents(ax, agents_now, agent_colors)

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


def plot_trajectory(agent_timeseries, config, out_dir='out', filename='trajectory'):
    check_plt_backend()

    bounds = config.get('bounds', DEFAULT_BOUNDS)
    field = config.get('field')
    x_length = bounds[0]
    y_length = bounds[1]
    y_ratio = y_length / x_length

    # get agents
    times = np.array(agent_timeseries['time'])
    agents = agent_timeseries['agents']

    # get each agent's trajectory
    trajectories = {}
    for agent_id, data in agents.items():
        trajectories[agent_id] = []
        for time_idx, time in enumerate(times):
            x, y = data['boundary']['location'][time_idx]
            theta = data['boundary']['angle'][time_idx]
            pos = [x, y, theta]
            trajectories[agent_id].append(pos)

    # make the figure
    fig = plt.figure(figsize=(8, 8*y_ratio))

    if field is not None:
        field = np.transpose(field)
        shape = field.shape
        im = plt.imshow(field,
                        origin='lower',
                        extent=[0, shape[1], 0, shape[0]],
                        # vmin=vmin,
                        # vmax=vmax,
                        cmap='Greys'
                        )

    for agent_id, agent_trajectory in trajectories.items():
        # convert trajectory to 2D array
        locations_array = np.array(agent_trajectory)
        x_coord = locations_array[:, 0]
        y_coord = locations_array[:, 1]

        # make multi-colored trajectory
        points = np.array([x_coord, y_coord]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=plt.get_cmap('cool'))
        lc.set_array(times)
        lc.set_linewidth(6)

        # plot line
        line = plt.gca().add_collection(lc)
        plt.plot(x_coord[0], y_coord[0], color=(0.0, 0.8, 0.0), marker='*')  # starting point
        plt.plot(x_coord[-1], y_coord[-1], color='r', marker='*')  # ending point

    plt.xlim((0, x_length))
    plt.ylim((0, y_length))

    # color bar
    cbar = plt.colorbar(line, ticks=[times[0], times[-1]])  # TODO --adjust this for full timeline
    cbar.set_label('time (s)', rotation=270)

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


def plot_motility(timeseries, out_dir='out', filename='motility_analysis'):
    check_plt_backend()

    expected_speed = 14.2  # um/s (Berg)
    expected_angle_between_runs = 68 # degrees (Berg)

    times = timeseries['time']
    agents = timeseries['agents']

    motility_analysis = {
        agent_id: {
            'speed': [],
            'angle': [],
            'thrust': [],
            'torque': []}
        for agent_id in list(agents.keys())}

    for agent_id, agent_data in agents.items():
        previous_location = [0,0]
        previous_time = times[0]

        # go through each time point for this agent
        for time_idx, time in enumerate(times):
            boundary_data = agent_data['boundary']
            angle = boundary_data['angle'][time_idx]
            location = boundary_data['location'][time_idx]
            thrust = boundary_data['thrust'][time_idx]
            torque = boundary_data['torque'][time_idx]

            # get speed since last time
            if time != times[0]:
                dt = time - previous_time
                distance = (
                    (location[0] - previous_location[0]) ** 2 +
                    (location[1] - previous_location[1]) ** 2
                        ) ** 0.5
                speed = distance / dt  # um/sec
            else:
                speed = 0.0

            # save data
            motility_analysis[agent_id]['speed'].append(speed)
            motility_analysis[agent_id]['angle'].append(angle)
            motility_analysis[agent_id]['thrust'].append(thrust)
            motility_analysis[agent_id]['torque'].append(torque)

            # save previous location and time
            previous_location = location
            previous_time = time

    # plot results
    cols = 1
    rows = 3
    fig = plt.figure(figsize=(6 * cols, 1.5 * rows))
    plt.rcParams.update({'font.size': 12})

    ax1 = plt.subplot(rows, cols, 1)
    for agent_id, analysis in motility_analysis.items():
        speed = analysis['speed']
        avg_speed = np.mean(speed)
        ax1.plot(times, speed, label=agent_id)
        # ax1.axhline(y=avg_speed, color='b', linestyle='dashed', label='mean')

    ax1.axhline(y=expected_speed, color='r', linestyle='dashed', label='expected mean')
    ax1.set_ylabel(u'speed \n (\u03bcm/sec)')
    ax1.set_xlabel('time')
    ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax2 = plt.subplot(rows, cols, 2)
    for agent_id, analysis in motility_analysis.items():
        thrust = analysis['thrust']
        ax2.plot(times, thrust, label=agent_id)
    ax2.set_ylabel('thrust')

    ax3 = plt.subplot(rows, cols, 3)
    for agent_id, analysis in motility_analysis.items():
        torque = analysis['torque']
        ax3.plot(times, torque, label=agent_id)
    ax3.set_ylabel('torque')

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


def init_axes(fig, edge_length_x, edge_length_y, grid, row_idx, col_idx, time):
    ax = fig.add_subplot(grid[row_idx, col_idx])
    if row_idx == 0:
        plot_title = 'time: {:.4f} s'.format(float(time))
        plt.title(plot_title, y=1.08)
    ax.set(xlim=[0, edge_length_x], ylim=[0, edge_length_y], aspect=1)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    return ax
