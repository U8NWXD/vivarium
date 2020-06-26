from __future__ import absolute_import, division, print_function

import os
import math
import random

import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.lines as mlines
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
BASELINE_TAG_COLOR = [220/360, 1.0, 0.2]  # HSV
FLOURESCENT_SV = [0.5, 1.0]  # SV for fluorescent colors

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
    '''Plot snapshots of the simulation over time

    The snapshots depict the agents and environmental molecule
    concentrations.

    Arguments:
        data (dict): A dictionary with the following keys:
            * **agents** (:py:class:`dict`): A mapping from times to
              dictionaries of agent data at that timepoint. Agent data
              dictionaries should have the same form as the hierarchy
              tree rooted at ``agents``.
            * **fields** (:py:class:`dict`): A mapping from times to
              dictionaries of environmental field data at that
              timepoint.  Field data dictionaries should have the same
              form as the hierarchy tree rooted at ``fields``.
            * **config** (:py:class:`dict`): The environmental
              configuration dictionary  with the following keys:
                * **bounds** (:py:class:`tuple`): The dimensions of the
                  environment.
        plot_config (dict): Accepts the following configuration options.
            Any options with a default is optional.
            * **n_snapshots** (:py:class:`int`): Number of snapshots to
              show per row (i.e. for each molecule). Defaults to 6.
            * **out_dir** (:py:class:`str`): Output directory, which is
              ``out`` by default.
            * **filename** (:py:class:`str`): Base name of output file.
              ``snapshots`` by default.
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
            field_min = min([min(min(field_data[field_id])) for t, field_data in fields.items()])
            field_max = max([max(max(field_data[field_id])) for t, field_data in fields.items()])
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
    figsize = (12 * n_cols, 12 * n_rows)
    max_dpi = min([2**16 // dim for dim in figsize]) - 1
    fig = plt.figure(figsize=figsize, dpi=min(max_dpi, 100))
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

def get_fluorescent_color(baseline_hsv, tag_color, intensity):
    # move color towards bright fluoresence color when intensity = 1
    new_hsv = baseline_hsv[:]
    distance = [a - b for a, b in zip(tag_color, new_hsv)]

    # if hue distance > 180 degrees, go around in the other direction
    if distance[0] > 0.5:
        distance[0] = 1 - distance[0]
    elif distance[0] < -0.5:
        distance[0] = 1 + distance[0]

    new_hsv = [a + intensity * b for a, b in zip(new_hsv, distance)]
    new_hsv[0] = new_hsv[0] % 1

    return new_hsv

def plot_tags(data, plot_config):
    '''Plot snapshots of the simulation over time

    The snapshots depict the agents and the levels of tagged molecules
    in each agent by agent color intensity.

    Arguments:
        data (dict): A dictionary with the following keys:
            * **agents** (:py:class:`dict`): A mapping from times to
              dictionaries of agent data at that timepoint. Agent data
              dictionaries should have the same form as the hierarchy
              tree rooted at ``agents``.
            * **config** (:py:class:`dict`): The environmental
              configuration dictionary  with the following keys:
                * **bounds** (:py:class:`tuple`): The dimensions of the
                  environment.
        plot_config (dict): Accepts the following configuration options.
            Any options with a default is optional.
            * **n_snapshots** (:py:class:`int`): Number of snapshots to
              show per row (i.e. for each molecule). Defaults to 6.
            * **out_dir** (:py:class:`str`): Output directory, which is
              ``out`` by default.
            * **filename** (:py:class:`str`): Base name of output file.
              ``tags`` by default.
            * **tagged_molecules** (:py:class:`Iterable`): The tagged
              molecules whose concentrations will be indicated by agent
              color. Each molecule should be specified as a
              :py:class:`tuple` of the store in the agent's boundary
              where the molecule's count can be found and the name of
              the molecule's count variable.
    '''
    check_plt_backend()

    n_snapshots = plot_config.get('n_snapshots', 6)
    out_dir = plot_config.get('out_dir', 'out')
    filename = plot_config.get('filename', 'tags')
    tagged_molecules = plot_config['tagged_molecules']

    if tagged_molecules == []:
        raise ValueError('At least one molecule must be tagged.')

    # get data
    agents = data['agents']
    config = data.get('config', {})
    bounds = config['bounds']
    edge_length_x, edge_length_y = bounds

    # time steps that will be used
    time_vec = list(agents.keys())
    time_indices = np.round(
        np.linspace(0, len(time_vec) - 1, n_snapshots)
    ).astype(int)
    snapshot_times = [time_vec[i] for i in time_indices]

    # get tag ids and range
    tag_ranges = {}
    tag_colors = {}

    for time, time_data in agents.items():
        for agent_id, agent_data in time_data.items():
            volume = agent_data['boundary']['volume']
            for tag_id in tagged_molecules:
                report_type, molecule = tag_id
                count = agent_data['boundary'][report_type][molecule]
                conc = count / volume if volume else 0
                if tag_id in tag_ranges:
                    tag_ranges[tag_id] = [
                        min(tag_ranges[tag_id][0], conc),
                        max(tag_ranges[tag_id][1], conc)]
                else:
                    # add new tag
                    tag_ranges[tag_id] = [conc, conc]

                    # select random initial hue
                    hue = random.choice(HUES)
                    tag_color = [hue] + FLOURESCENT_SV
                    tag_colors[tag_id] = tag_color

    # make the figure
    n_rows = len(tagged_molecules)
    n_cols = n_snapshots + 1  # one column for the colorbar
    figsize = (12 * n_cols, 12 * n_rows)
    max_dpi = min([2**16 // dim for dim in figsize]) - 1
    fig = plt.figure(figsize=figsize, dpi=min(max_dpi, 100))
    grid = plt.GridSpec(n_rows, n_cols, wspace=0.2, hspace=0.2)
    plt.rcParams.update({'font.size': 36})

    # plot tags
    for col_idx, (time_idx, time) in enumerate(
        zip(time_indices, snapshot_times)
    ):
        for row_idx, tag_id in enumerate(tag_ranges.keys()):
            ax = init_axes(
                fig, edge_length_x, edge_length_y, grid,
                row_idx, col_idx, time
            )
            ax.set_facecolor('black')  # set background color

            # update agent colors based on tag_level
            agent_tag_colors = {}
            for agent_id, agent_data in agents[time].items():
                agent_color = BASELINE_TAG_COLOR

                # get current tag concentration, and determine color
                report_type, molecule = tag_id
                counts = agent_data['boundary'][report_type][molecule]
                volume = agent_data['boundary']['volume']
                level = counts / volume if volume else 0
                min_tag, max_tag = tag_ranges[tag_id]
                if min_tag != max_tag:
                    intensity = max((level - min_tag), 0)
                    intensity = min(intensity / (max_tag - min_tag), 1)
                    tag_color = tag_colors[tag_id]
                    agent_color = get_fluorescent_color(
                        BASELINE_TAG_COLOR, tag_color, intensity)

                agent_tag_colors[agent_id] = agent_color

            plot_agents(ax, agents[time], agent_tag_colors)

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)

def initialize_spatial_figure(bounds, fontsize=18):

    x_length = bounds[0]
    y_length = bounds[1]

    # set up figure
    n_ticks = 4
    plot_buffer = 0.02
    buffer = plot_buffer * min(bounds)
    min_edge = min(x_length, y_length)
    x_scale = x_length/min_edge
    y_scale = y_length/min_edge

    # make the figure
    fig = plt.figure(figsize=(8*x_scale, 8*y_scale))
    plt.rcParams.update({'font.size': fontsize, "font.family": "Times New Roman"})

    plt.xlim((0-buffer, x_length+buffer))
    plt.ylim((0-buffer, y_length+buffer))
    plt.xlabel(u'\u03bcm')
    plt.ylabel(u'\u03bcm')

    # specify the number of ticks for each edge
    [x_bins, y_bins] = [int(n_ticks * edge / min_edge) for edge in [x_length, y_length]]
    plt.locator_params(axis='y', nbins=y_bins)
    plt.locator_params(axis='x', nbins=x_bins)

    return fig

def plot_agent_trajectory(agent_timeseries, config, out_dir='out', filename='trajectory'):
    check_plt_backend()

    # trajectory plot settings
    legend_fontsize = 18
    markersize = 30

    bounds = config.get('bounds', DEFAULT_BOUNDS)
    field = config.get('field')
    rotate_90 = config.get('rotate_90', False)

    # get agents
    times = np.array(agent_timeseries['time'])
    agents = agent_timeseries['agents']

    if rotate_90:
        field = rotate_field_90(field)
        for agent_id, series in agents.items():
            agents[agent_id] = rotate_agent_series_90(series, bounds)
        bounds = rotate_bounds_90(bounds)

    # get each agent's trajectory
    trajectories = {}
    for agent_id, data in agents.items():
        trajectories[agent_id] = []
        for time_idx, time in enumerate(times):
            x, y = data['boundary']['location'][time_idx]
            theta = data['boundary']['angle'][time_idx]
            pos = [x, y, theta]
            trajectories[agent_id].append(pos)

    # initialize a spatial figure
    fig = initialize_spatial_figure(bounds, legend_fontsize)

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

        # plot line
        plt.plot(x_coord, y_coord, linewidth=2, label=agent_id)
        plt.plot(x_coord[0], y_coord[0],
                 color=(0.0, 0.8, 0.0), marker='.', markersize=markersize)  # starting point
        plt.plot(x_coord[-1], y_coord[-1],
                 color='r', marker='.', markersize=markersize)  # ending point

    # create legend for agent ids
    first_legend = plt.legend(
        title='agent ids', loc='center left', bbox_to_anchor=(1.01, 0.5), prop={'size': legend_fontsize})
    ax = plt.gca().add_artist(first_legend)

    # create a legend for start/end markers
    start = mlines.Line2D([], [],
            color=(0.0, 0.8, 0.0), marker='.', markersize=markersize, linestyle='None', label='start')
    end = mlines.Line2D([], [],
            color='r', marker='.', markersize=markersize, linestyle='None', label='end')
    plt.legend(
        handles=[start, end], loc='upper right', prop={'size': legend_fontsize})

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


def rotate_bounds_90(bounds):
    return [bounds[1], bounds[0]]

def rotate_field_90(field):
    return np.rot90(field, 3)  # rotate 3 times for 270

def rotate_agent_series_90(series, bounds):
    location_series = series['boundary']['location']  #[time_idx]
    angle_series = series['boundary']['angle']  #[time_idx]
    series['boundary']['location'] = [[y, bounds[0] - x] for [x, y] in location_series]
    series['boundary']['angle'] = [theta + PI / 2 for theta in angle_series]
    return series

def plot_temporal_trajectory(agent_timeseries, config, out_dir='out', filename='temporal'):
    check_plt_backend()

    bounds = config.get('bounds', DEFAULT_BOUNDS)
    field = config.get('field')
    rotate_90 = config.get('rotate_90', False)

    # get agents
    times = np.array(agent_timeseries['time'])
    agents = agent_timeseries['agents']

    if rotate_90:
        field = rotate_field_90(field)
        for agent_id, series in agents.items():
            agents[agent_id] = rotate_agent_series_90(series, bounds)
        bounds = rotate_bounds_90(bounds)

    # get each agent's trajectory
    trajectories = {}
    for agent_id, series in agents.items():
        trajectories[agent_id] = []
        for time_idx, time in enumerate(times):
            x, y = series['boundary']['location'][time_idx]
            theta = series['boundary']['angle'][time_idx]
            pos = [x, y, theta]
            trajectories[agent_id].append(pos)

    # initialize a spatial figure
    fig = initialize_spatial_figure(bounds)

    if field is not None:
        field = np.transpose(field)
        shape = field.shape
        im = plt.imshow(field,
                        origin='lower',
                        extent=[0, shape[1], 0, shape[0]],
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

    # color bar
    cbar = plt.colorbar(line, ticks=[times[0], times[-1]], aspect=90, shrink=0.4)
    cbar.set_label('time (s)', rotation=270)

    fig_path = os.path.join(out_dir, filename)
    plt.subplots_adjust(wspace=0.7, hspace=0.1)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close(fig)


def plot_motility(timeseries, out_dir='out', filename='motility_analysis'):
    check_plt_backend()

    expected_velocity = 14.2  # um/s (Berg)
    expected_angle_between_runs = 68 # degrees (Berg)

    times = timeseries['time']
    agents = timeseries['agents']

    motility_analysis = {
        agent_id: {
            'velocity': [],
            'angular_velocity': [],
            'angle_between_runs': [],
            'angle': [],
            'thrust': [],
            'torque': []}
        for agent_id in list(agents.keys())}

    for agent_id, agent_data in agents.items():
        boundary_data = agent_data['boundary']
        cell_data = agent_data['cell']
        previous_time = times[0]
        previous_angle = boundary_data['angle'][0]
        previous_location = boundary_data['location'][0]
        previous_run_angle = boundary_data['angle'][0]
        previous_motor_state = cell_data['motor_state'][0]  # 1 for tumble, 0 for run

        # go through each time point for this agent
        for time_idx, time in enumerate(times):
            motor_state = cell_data['motor_state'][time_idx]
            angle = boundary_data['angle'][time_idx]
            location = boundary_data['location'][time_idx]
            thrust = boundary_data['thrust'][time_idx]
            torque = boundary_data['torque'][time_idx]

            # get velocity
            if time != times[0]:
                dt = time - previous_time
                distance = (
                    (location[0] - previous_location[0]) ** 2 +
                    (location[1] - previous_location[1]) ** 2
                        ) ** 0.5
                velocity = distance / dt  # um/sec

                angle_change = ((angle - previous_angle) / PI * 180) % 360
                if angle_change > 180:
                    angle_change = 360 - angle_change
                angular_velocity = angle_change/ dt
            else:
                velocity = 0.0
                angular_velocity = 0.0

            # get angle change between runs
            angle_between_runs = None
            if motor_state == 0:  # run
                if previous_motor_state == 1:
                    angle_between_runs = angle - previous_run_angle
                previous_run_angle = angle

            # save data
            motility_analysis[agent_id]['velocity'].append(velocity)
            motility_analysis[agent_id]['angular_velocity'].append(angular_velocity)
            motility_analysis[agent_id]['angle'].append(angle)
            motility_analysis[agent_id]['thrust'].append(thrust)
            motility_analysis[agent_id]['torque'].append(torque)
            motility_analysis[agent_id]['angle_between_runs'].append(angle_between_runs)

            # save previous location and time
            previous_location = location
            previous_angle = angle
            previous_time = time
            previous_motor_state = motor_state

    # plot results
    cols = 1
    rows = 5
    fig = plt.figure(figsize=(6 * cols, 1.5 * rows))
    plt.rcParams.update({'font.size': 12})

    ax1 = plt.subplot(rows, cols, 1)
    for agent_id, analysis in motility_analysis.items():
        velocity = analysis['velocity']
        mean_velocity = np.mean(velocity)
        ax1.plot(times, velocity, label=agent_id)
        ax1.axhline(y=mean_velocity, linestyle='dashed', label='mean_' + agent_id)
    ax1.axhline(y=expected_velocity, color='r', linestyle='dashed', label='expected mean')
    ax1.set_ylabel(u'velocity \n (\u03bcm/sec)')
    ax1.set_xlabel('time')
    # ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax2 = plt.subplot(rows, cols, 2)
    for agent_id, analysis in motility_analysis.items():
        angular_velocity = analysis['angular_velocity']
        ax2.plot(times, angular_velocity, label=agent_id)
    ax2.set_ylabel(u'angular velocity \n (degrees/sec)')
    ax2.set_xlabel('time')
    # ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax3 = plt.subplot(rows, cols, 3)
    for agent_id, analysis in motility_analysis.items():
        # convert to degrees
        angle_between_runs = [
            (angle / PI * 180) % 360 if angle is not None else None
            for angle in analysis['angle_between_runs']]
        # pair with time
        run_angle_points = [
            [t, angle] if angle < 180 else [t, 360 - angle]
            for t, angle in dict(zip(times, angle_between_runs)).items()
            if angle is not None]

        plot_times = [point[0] for point in run_angle_points]
        plot_angles = [point[1] for point in run_angle_points]
        mean_angle_change = np.mean(plot_angles)
        ax3.scatter(plot_times, plot_angles, label=agent_id)
        ax3.axhline(y=mean_angle_change, linestyle='dashed') #, label='mean_' + agent_id)
    ax3.set_ylabel(u'degrees \n between runs')
    ax3.axhline(y=expected_angle_between_runs, color='r', linestyle='dashed', label='expected')
    ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    ax4 = plt.subplot(rows, cols, 4)
    for agent_id, analysis in motility_analysis.items():
        thrust = analysis['thrust']
        ax4.plot(times, thrust, label=agent_id)
    ax4.set_ylabel('thrust')

    ax5 = plt.subplot(rows, cols, 5)
    for agent_id, analysis in motility_analysis.items():
        torque = analysis['torque']
        ax5.plot(times, torque, label=agent_id)
    ax5.set_ylabel('torque')

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
