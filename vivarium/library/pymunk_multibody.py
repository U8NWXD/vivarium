from __future__ import absolute_import, division, print_function

import os

# os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# import pygame
# from pygame.locals import *
# from pygame.color import *

# Python imports
import random
import math
import numpy as nppython

# pymunk imports
import pymunkoptions
pymunkoptions.options["debug"] = False
import pymunk
# import pymunk.pygame_util


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
        'damping': 0.5,  # 1 is no damping, 0 is full damping
        'angular_damping': 0.8,
        'friction': 0.9,  # does this do anything?
        'physics_dt': 0.001,
        'force_scaling': 1e2,  # scales from pN
        # configured parameters
        'jitter_force': 1e-3,  # pN
        'bounds': [20, 20],
        'barriers': False,
        # 'debug': False,
        'initial_agents': {},
    }

    def __init__(self, config):
        # hardcoded parameters
        self.elasticity = self.defaults['elasticity']
        self.friction = self.defaults['friction']
        self.damping = self.defaults['damping']
        self.angular_damping = self.defaults['angular_damping']
        self.physics_dt = self.defaults['physics_dt']
        self.force_scaling = self.defaults['force_scaling']

        # configured parameters
        self.jitter_force = config.get('jitter_force', self.defaults['jitter_force'])
        self.bounds = config.get('bounds', self.defaults['bounds'])
        barriers = config.get('barriers', self.defaults['barriers'])

        # initialize pymunk space
        self.space = pymunk.Space()

        # # debug screen with pygame
        # self.pygame_viz = config.get('debug', self.defaults['debug'])
        # if self.pygame_viz:
        #     pygame.init()
        #     self._screen = pygame.display.set_mode((
        #         int(self.bounds[0]),
        #         int(self.bounds[1])),
        #         RESIZABLE)
        #     self._clock = pygame.time.Clock()
        #     self._draw_options = pymunk.pygame_util.DrawOptions(self._screen)

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

        # if self.pygame_viz:
        #     self._update_screen()

    def apply_motile_force(self, body):
        width, length = body.dimensions

        # motile forces
        motile_location = (width / 2, 0)  # apply force at back end of body
        thrust = 0.0
        torque = 0.0
        motile_force = [thrust, torque]

        if hasattr(body, 'thrust'):
            thrust = body.thrust
            torque = body.torque
            motile_force = [thrust, 0.0]

            # add directly to angular velocity
            body.angular_velocity += torque

            # # force-based torque
            # if torque != 0.0:
            #     motile_force = get_force_with_angle(thrust, torque)

        scaled_motile_force = [force * self.force_scaling for force in motile_force]
        body.apply_impulse_at_local_point(scaled_motile_force, motile_location)
        # body.apply_force_at_local_point(scaled_motile_force, motile_location)

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
        body.velocity = body.velocity * self.damping
        body.angular_velocity = body.angular_velocity * self.angular_damping

        # body.velocity -= body.force / body.mass
        # body.angular_velocity -= body.torque / body.moment

    def add_barriers(self, bounds, barriers):
        """ Create static barriers """
        thickness = 2.0
        offset = thickness
        x_bound = bounds[0]
        y_bound = bounds[1]

        static_body = self.space.static_body
        static_lines = [
            pymunk.Segment(
                static_body,
                (0.0-offset, 0.0-offset),
                (x_bound+offset, 0.0-offset),
                thickness),
            pymunk.Segment(
                static_body,
                (x_bound+offset, 0.0-offset),
                (x_bound+offset, y_bound+offset),
                thickness),
            pymunk.Segment(
                static_body,
                (x_bound+offset, y_bound+offset),
                (0.0-offset, y_bound+offset),
                thickness),
            pymunk.Segment(
                static_body,
                (0.0-offset, y_bound+offset),
                (0.0-offset, 0.0-offset),
                thickness),
        ]

        if barriers:
            spacer_thickness = barriers.get('spacer_thickness', 0.1)
            channel_height = barriers.get('channel_height')
            channel_space = barriers.get('channel_space')
            n_lines = math.floor(x_bound/channel_space)

            machine_lines = [
                pymunk.Segment(
                    static_body,
                    (channel_space * line, 0),
                    (channel_space * line, channel_height), spacer_thickness)
                for line in range(n_lines)]
            static_lines += machine_lines

        for line in static_lines:
            line.elasticity = 0.0  # bounce
            line.friction = 0.8
        self.space.add(static_lines)

    def add_body_from_center(self, body_id, specs):
        boundary = specs['boundary']
        width = boundary['width']
        length = boundary['length']
        mass = boundary['mass']
        center_position = boundary['location']
        angle = boundary['angle']
        angular_velocity = boundary.get('angular_velocity', 0.0)

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
            center_position[0],
            center_position[1])
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
        boundary = specs['boundary']
        length = boundary['length']
        width = boundary['width']
        mass = boundary['mass']
        thrust = boundary['thrust']
        torque = boundary['torque']

        body, shape = self.bodies[body_id]
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
        new_body.velocity = body.velocity
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
        self.bodies[body_id] = (new_body, new_shape)

    def update_bodies(self, bodies):
        # if an agent has been removed from the agents store,
        # remove it from space and bodies
        removed_bodies = [
            body_id for body_id in self.bodies.keys()
            if body_id not in bodies.keys()]
        for body_id in removed_bodies:
            body, shape = self.bodies[body_id]
            self.space.remove(body, shape)
            del self.bodies[body_id]

        # update agents, add new agents
        for body_id, specs in bodies.items():
            if body_id in self.bodies:
                self.update_body(body_id, specs)
            else:
                self.add_body_from_center(body_id, specs)

    def get_body_position(self, agent_id):
        body, shape = self.bodies[agent_id]
        return {
            'location': [pos for pos in body.position],
            'angle': body.angle,
        }

    def get_body_positions(self):
        return {
            body_id: {
                'boundary': self.get_body_position(body_id)}
            for body_id in self.bodies.keys()}

    # ## pygame visualization (for debugging)
    # def _process_events(self):
    #     for event in pygame.event.get():
    #         if event.type == QUIT:
    #             self._running = False
    #         elif event.type == KEYDOWN and event.key == K_ESCAPE:
    #             self._running = False
    #
    # def _clear_screen(self):
    #     self._screen.fill(THECOLORS["white"])
    #
    # def _draw_objects(self):
    #     self.space.debug_draw(self._draw_options)
    #
    # def _update_screen(self):
    #     self._process_events()
    #     self._clear_screen()
    #     self._draw_objects()
    #     pygame.display.flip()
    #     # Delay fixed time between frames
    #     self._clock.tick(2)


def test_multibody(
        total_time=2,
        debug=False):
    bounds = [500, 500]
    center_location = [0.5*loc for loc in bounds]
    agents = {
        '1': {
            'boundary': {
                'location': center_location,
                'angle': PI/2,
                'volume': 15,
                'length': 30,
                'width': 10,
                'mass': 1,
                'thrust': 1e3,
                'torque': 0.0}}}
    config = {
        'jitter_force': 1e1,
        'bounds': bounds,
        'barriers': False,
        'initial_agents': agents,
        # 'debug': debug
    }
    multibody = MultiBody(config)

    # run simulation
    time = 0
    time_step = 0.1
    while time < total_time:
        time += time_step
        multibody.run(time_step)


if __name__ == '__main__':
    test_multibody(10, True)
