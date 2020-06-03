from __future__ import absolute_import, division, print_function

import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pygame.locals import *
from pygame.color import *

# Python imports
import random
import math
import numpy as np

# pymunk imports
import pymunkoptions
pymunkoptions.options["debug"] = False
import pymunk
import pymunk.pygame_util


PI = math.pi

DEBUG_SIZE = 600  # size of the pygame debug screen

def get_force_with_angle(force, angle):
    x = force * math.cos(angle)
    y = force * math.sin(angle)
    return [x, y]


def front_from_corner(width, length, corner_position, angle):
    half_width = width/2
    dx = length * math.cos(angle) + half_width * math.cos(angle + PI/2)  # PI/2 gives a half-rotation for the width component
    dy = length * math.sin(angle) + half_width * math.sin(angle + PI/2)
    front_position = [corner_position[0] + dx, corner_position[1] + dy]
    return np.array([front_position[0], front_position[1], angle])


def corner_from_center(width, length, center_position, angle):
    half_length = length/2
    half_width = width/2
    dx = half_length * math.cos(angle) + half_width * math.cos(angle + PI/2)
    dy = half_length * math.sin(angle) + half_width * math.sin(angle + PI/2)
    corner_position = [center_position[0] - dx, center_position[1] - dy]
    return np.array([corner_position[0], corner_position[1], angle])


def random_body_position(body):
    ''' pick a random point along the boundary'''
    width, length = body.dimensions
    if random.randint(0, 1) == 0:
        # force along ends
        if random.randint(0, 1) == 0:
            # force on the left end
            location = (random.uniform(0, width), 0)
        else:
            # force on the right end
            location = (random.uniform(0, width), length)
    else:
        # force along length
        if random.randint(0, 1) == 0:
            # force on the bottom end
            location = (0, random.uniform(0, length))
        else:
            # force on the top end
            location = (width, random.uniform(0, length))
    return location



class MultiBody(object):
    """
    Multibody object for interfacing with pymunk
    """

    defaults = {
        # hardcoded parameters
        'elasticity': 0.9,
        'damping': 0.05,  # simulates viscous forces (1 = no damping, 0 = full damping)
        'angular_damping': 0.7,  # less damping for angular velocity seems to improve behavior
        'friction': 0.9,  # TODO -- does this do anything?
        'physics_dt': 0.005,
        'force_scaling': 100,  # scales from pN

        # configured parameters
        'jitter_force': 1e-3,  # pN
        'bounds': [20, 20],
        'barriers': False,
        'debug': False,
        'initial_agents': {},
    }

    def __init__(self, config):
        # hardcoded parameters
        self.elasticity = self.defaults['elasticity']
        self.friction = self.defaults['friction']
        self.damping = self.defaults['damping']
        self.angular_damping = self.defaults['angular_damping']
        self.force_scaling = self.defaults['force_scaling']
        self.physics_dt = self.defaults['physics_dt']

        # configured parameters
        self.jitter_force = config.get('jitter_force', self.defaults['jitter_force'])
        self.bounds = config.get('bounds', self.defaults['bounds'])
        barriers = config.get('barriers', self.defaults['barriers'])

        # initialize pymunk space
        self.space = pymunk.Space()

        # debug screen with pygame
        self.pygame_viz = config.get('debug', self.defaults['debug'])
        self.pygame_scale = 1  # pygame_scale scales the debug screen
        if self.pygame_viz:
            max_bound = max(self.bounds)
            self.pygame_scale = DEBUG_SIZE / max_bound
            self.force_scaling *= self.pygame_scale
            pygame.init()
            self._screen = pygame.display.set_mode((
                int(self.bounds[0]*self.pygame_scale),
                int(self.bounds[1]*self.pygame_scale)), RESIZABLE)
            self._clock = pygame.time.Clock()
            self._draw_options = pymunk.pygame_util.DrawOptions(self._screen)

        # add static barriers
        self.add_barriers(self.bounds, barriers)

        # initialize agents
        initial_agents = config.get('initial_agents', self.defaults['initial_agents'])
        self.bodies = {}
        for agent_id, specs in initial_agents.items():
            self.add_body_from_center(agent_id, specs)

    def run(self, timestep):
        assert self.physics_dt < timestep

        time = 0
        while time < timestep:
            time += self.physics_dt

            # apply forces
            for body in self.space.bodies:
                self.apply_jitter_force(body)
                self.apply_motile_force(body)
                self.apply_viscous_force(body)

            # run for a physics timestep
            self.space.step(self.physics_dt)

        if self.pygame_viz:
            self._update_screen()

    def apply_motile_force(self, body):
        width, length = body.dimensions

        # motile forces
        motile_location = (width / 2, 0)  # apply force at back end of body
        thrust = 0.0
        torque = 0.0

        if hasattr(body, 'thrust'):
            thrust = body.thrust
            torque = body.torque

            # add directly to angular velocity
            body.angular_velocity += torque
            # force-based torque
            # if torque != 0.0:
            #     motile_force = get_force_with_angle(thrust, torque)

        scaled_motile_force = [thrust * self.force_scaling, 0.0]
        body.apply_force_at_local_point(scaled_motile_force, motile_location)

    def apply_jitter_force(self, body):
        jitter_location = random_body_position(body)
        jitter_force = [
            random.normalvariate(0, self.jitter_force),
            random.normalvariate(0, self.jitter_force)]
        scaled_jitter_force = [
            force * self.force_scaling
            for force in jitter_force]
        body.apply_force_at_local_point(
            scaled_jitter_force,
            jitter_location)

    def apply_viscous_force(self, body):
        # dampen the velocity
        body.velocity = body.velocity * self.damping + (body.force / body.mass) * self.physics_dt
        body.angular_velocity = body.angular_velocity * self.angular_damping + body.torque / body.moment * self.physics_dt

    def add_barriers(self, bounds, barriers):
        """ Create static barriers """
        thickness = 0.2

        x_bound = bounds[0] * self.pygame_scale
        y_bound = bounds[1] * self.pygame_scale

        static_body = self.space.static_body
        static_lines = [
            pymunk.Segment(static_body, (0.0, 0.0), (x_bound, 0.0), thickness),
            pymunk.Segment(static_body, (x_bound, 0.0), (x_bound, y_bound), thickness),
            pymunk.Segment(static_body, (x_bound, y_bound), (0.0, y_bound), thickness),
            pymunk.Segment(static_body, (0.0, y_bound), (0.0, 0.0), thickness),
        ]

        if barriers:
            import ipdb; ipdb.set_trace()

            channel_height = barriers.get('channel_height') * self.pygame_scale
            channel_space = barriers.get('channel_space') * self.pygame_scale

            n_lines = math.floor(x_bound/channel_space)

            machine_lines = [
                pymunk.Segment(
                    static_body,
                    (channel_space * line, 0),
                    (channel_space * line, channel_height), thickness)
                for line in range(n_lines)]
            static_lines += machine_lines

        for line in static_lines:
            line.elasticity = 0.0  # no bounce
            line.friction = 0.9
        self.space.add(static_lines)

    def add_body_from_center(self, body_id, body):
        width = body['width'] * self.pygame_scale
        length = body['length'] * self.pygame_scale
        mass = body['mass']
        center_position = body['location']
        angle = body['angle']
        angular_velocity = body.get('angular_velocity', 0.0)

        half_length = length / 2
        half_width = width / 2

        shape = pymunk.Poly(None, (
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width)))

        inertia = pymunk.moment_for_poly(mass, shape.get_vertices())
        body = pymunk.Body(mass, inertia)
        shape.body = body

        body.position = (
            center_position[0] * self.pygame_scale,
            center_position[1] * self.pygame_scale)
        body.angle = angle
        body.dimensions = (width, length)
        body.angular_velocity = angular_velocity

        shape.elasticity = self.elasticity
        shape.friction = self.friction

        # add body and shape to space
        self.space.add(body, shape)

        # add body to agents dictionary
        self.bodies[body_id] = (body, shape)

    def update_body(self, body_id, specs):
        global_specs = specs['global']
        boundary_specs = specs['boundary']

        length = global_specs['length'] * self.pygame_scale
        width = global_specs['width'] * self.pygame_scale
        mass = global_specs['mass'].magnitude
        thrust = boundary_specs['thrust']
        torque = boundary_specs['torque']

        body, shape = self.agent_bodies[body_id]
        position = body.position
        angle = body.angle

        # make shape, moment of inertia, and add a body
        half_length = length/2
        half_width = width/2
        new_shape = pymunk.Poly(None, (
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width)))

        inertia = pymunk.moment_for_poly(mass, new_shape.get_vertices())
        new_body = pymunk.Body(mass, inertia)
        new_shape.body = new_body

        new_body.position = position
        new_body.angle = angle
        new_body.angular_velocity = body.angular_velocity
        new_body.dimensions = (width, length)
        new_body.thrust = thrust
        new_body.torque = torque

        new_shape.elasticity = shape.elasticity
        new_shape.friction = shape.friction

        # swap bodies
        self.space.remove(body, shape)
        self.space.add(new_body, new_shape)

        # update body
        self.agent_bodies[body_id] = (new_body, new_shape)

    def get_body_position(self, agent_id):
        body, shape = self.agent_bodies[agent_id]
        position = body.position
        rescaled_position = [
            position[0] / self.pygame_scale,
            position[1] / self.pygame_scale]

        # enforce bounds
        rescaled_position = [
            0 if pos<0 else pos
            for idx, pos in enumerate(rescaled_position)]
        rescaled_position = [
            self.bounds[idx] if pos>self.bounds[idx] else pos
            for idx, pos in enumerate(rescaled_position)]

        return {
            'location': rescaled_position,
            'angle': body.angle}

    ## pygame visualization (for debugging)
    def _process_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self._running = False

    def _clear_screen(self):
        self._screen.fill(THECOLORS["white"])

    def _draw_objects(self):
        self.space.debug_draw(self._draw_options)

    def _update_screen(self):
        self._process_events()
        self._clear_screen()
        self._draw_objects()
        pygame.display.flip()
        # Delay fixed time between frames
        self._clock.tick(2)


def test_multibody(total_time=2, debug=False):
    bounds = [10, 10]
    agents = {
        '1': {
            'location': [0.5, 0.5],
            'angle': PI/2,
            'volume': 1,
            'length': 2,
            'width': 1,
            'mass': 1,
            'thrust': 1e3,
            'torque': 0.0}}
    config = {
        'jitter_force': 1e1,
        'bounds': bounds,
        'barriers': False,
        'initial_agents': agents,
        'debug': debug}
    multibody = MultiBody(config)

    # run simulation
    time = 0
    time_step = 0.1
    while time < total_time:
        time += time_step
        multibody.run(time_step)


if __name__ == '__main__':
    test_multibody(10, True)