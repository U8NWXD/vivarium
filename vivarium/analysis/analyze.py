from __future__ import absolute_import, division, print_function

import argparse
import json
import os

from pymongo import MongoClient

from vivarium.plots.multibody_physics import plot_snapshots
from vivarium.core.composition import plot_agents_multigen
from vivarium.core.emitter import (
    get_atlas_client,
    get_local_client,
    data_from_database,
    get_atlas_database_emitter_config,
    SECRETS_PATH,
)


OUT_DIR = 'out'


def plot(args):
    if args.atlas:
        client = get_atlas_client(SECRETS_PATH)
    else:
        client = get_local_client(args.port, args.database_name)
    data, environment_config = data_from_database(
        args.experiment_id, client)
    del data[0]

    out_dir = os.path.join(OUT_DIR, args.experiment_id)
    if os.path.exists(out_dir):
        if not args.force:
            raise IOError('Directory {} already exists'.format(out_dir))
    else:
        os.makedirs(out_dir)

    if args.snapshots:
        agents = {
            time: timepoint['agents']
            for time, timepoint in data.items()
        }
        fields = {
            time: timepoint['fields']
            for time, timepoint in data.items()
        }
        snapshots_data = {
            'agents': agents,
            'fields': fields,
            'config': environment_config,
        }
        plot_config = {
            'out_dir': out_dir,
            'filename': 'snapshot',
        }
        plot_snapshots(snapshots_data, plot_config)

    if args.timeseries:
        plot_settings = {
            'agents_key': 'agents',
            'title_size': 10,
            'tick_label_size': 10,
        }
        plot_agents_multigen(data, plot_settings, out_dir)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'experiment_id',
        help='Experiment ID as recorded in the database',
    )
    parser.add_argument(
        '--snapshots', '-s',
        action='store_true',
        default=False,
        help='Plot snapshots',
    )
    parser.add_argument(
        '--timeseries', '-t',
        action='store_true',
        default=False,
        help='Generate line plot for each variable over time',
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        default=False,
        help=(
            'Write plots even if output directory already exists. This '
            'could overwrite your existing plots'
        ),
    )
    parser.add_argument(
        '--atlas', '-a',
        action='store_true',
        default=False,
        help=(
            'Read data from an mongoDB Atlas instead of a local mongoDB. '
            'Credentials, cluster subdomain, and database name should be '
            'specified in {}.'.format(SECRETS_PATH)
        )
    )
    parser.add_argument(
        '--port', '-p',
        default=27017,
        type=int,
        help=(
            'Port at which to access local mongoDB instance.'
        ),
    )
    parser.add_argument(
        '--database_name', '-d',
        default='simulations',
        type=str,
        help=(
            'Name of database on local mongoDB instance to read from.'
        )
    )
    args = parser.parse_args()
    plot(args)


if __name__ == '__main__':
    run()
