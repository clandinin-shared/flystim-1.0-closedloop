import random
import numpy as np
import moderngl

from math import pi, radians, ceil, cos, sin

from flystim.base import BaseProgram
from flystim.glsl import Uniform, Function, Variable, Texture
from flystim.trajectory import RectangleTrajectory
import flystim.distribution as distribution

class ConstantBackground(BaseProgram):
    def __init__(self, screen):
        uniforms = [
            Uniform('background', float)
        ]

        calc_color = 'color = background;\n'

        super().__init__(screen=screen, uniforms=uniforms, calc_color=calc_color)

    def configure(self, background=0.0):
        """
        :param background
        """

        self.prog['background'].value = background

    def eval_at(self, t):
        pass


class PeriodicGrating(BaseProgram):
    def __init__(self, screen, grating):
        uniforms = [
            Uniform('face_color', float),
            Uniform('background', float),
            Uniform('k_theta', float),
            Uniform('k_phi', float),
            Uniform('omega', float),
            Uniform('offset', float),
            Uniform('t', float)
        ]

        calc_color = ''
        calc_color += 'float intensity = {}(k_theta*theta + k_phi*phi - omega*t + offset);\n'.format(grating.name)
        calc_color += 'color = mix(background, face_color, intensity);\n'

        super().__init__(screen=screen, uniforms=uniforms, functions=[grating], calc_color=calc_color)

    def configure(self, period=20, rate=10, color=1.0, background=0.0, angle=45.0):
        """
        Stimulus pattern in which a periodic grating moves as a wavefront
        :param period: Spatial period of the grating, in degrees.
        :param rate: Velocity of the grating movement, in degrees per second.  Can be positive or negative.
        :param color: Color shown at peak intensity.
        :param background: Color shown at minimum intensity.
        :param angle: Tilt angle (in degrees) of the grating.  0 degrees will align the grating with a line of
        longitude.
        """

        # save settings
        self.rate = radians(rate)
        self.offset = 0.0

        # compute wavevector
        self.k = 2*pi/radians(period)
        self.prog['k_theta'].value = self.k*cos(radians(angle))
        self.prog['k_phi'].value   = self.k*sin(radians(angle))

        # push omega and offset to graphics card
        self.push_changes()

        # set color uniforms
        self.prog['face_color'].value = color
        self.prog['background'].value = background

    def push_changes(self):
        self.prog['omega'].value = self.rate * self.k
        self.prog['offset'].value = self.offset

    def update_stim(self, rate, t):
        old_rate = self.rate
        new_rate = radians(rate)

        old_offset = self.offset
        new_offset = (new_rate - old_rate)*self.k*t + old_offset

        self.rate = new_rate
        self.offset = new_offset

        self.push_changes()

    def eval_at(self, t):
        self.prog['t'].value = t


class SineGrating(PeriodicGrating):
    def __init__(self, screen):
        # define grating function
        grating = Function(name='sine_grating',
                           in_vars=[Variable('phase', float)],
                           out_type=float,
                           code='return 0.5*sin(phase) + 0.5;')

        # call super constructor
        super().__init__(screen=screen, grating=grating)


class RectGrating(PeriodicGrating):
    def __init__(self, screen):
        # define grating function
        grating = Function(name='rect_grating',
                           in_vars=[Variable('phase', float)],
                           out_type=float,
                           uniforms=[Uniform('duty_cycle', float)],
                           code='return (fract(phase/(2.0*M_PI)) <= duty_cycle) ? 1.0 : 0.0;')

        # call super constructor
        super().__init__(screen=screen, grating=grating)


class RotatingBars(RectGrating):
    def configure(self, duty_cycle=0.5, **kwargs):
        """
        Stimulus pattern in which rectangular bars rotate around the viewer.
        :param duty_cycle: Duty cycle of each bar, which should be between 0 and 1.  A value of "0" means the bar has
        zero width, and a value of "1" means that it occupies the entire period.
        """

        # set uniform
        self.prog['duty_cycle'].value = duty_cycle

        # call configuration method from parent class
        super().configure(**kwargs)


class ExpandingEdges(RectGrating):
    def configure(self, init_width=2, expand_rate=10, period=15, rate=0, **kwargs):
        """
        Stimulus pattern in which bars surrounding the viewer get wider or narrower.
        :param width: Starting angular width of each bar.
        :param expand_rate: The rate at which each bar grows wider in the counter-clockwise direction.  Can be negative.
        :param period: Spatial period of the grating, in degrees.
        :param rate: Velocity of the grating movement, in degrees per second.  Typically left at zero for this stimulus.
        """

        # save settings
        self.init_width = init_width
        self.expand_rate = expand_rate
        self.period = period

        # call configuration method from parent class
        super().configure(period=period, rate=rate, **kwargs)

    def eval_at(self, t):
        # adjust duty cycle
        self.prog['duty_cycle'].value = (self.init_width + t*self.expand_rate)/self.period

        # call evaluation method of the parent class
        super().eval_at(t)


class MovingPatch(BaseProgram):
    def __init__(self, screen):
        uniforms = [
            Uniform('theta_center', float),
            Uniform('phi_center', float),
            Uniform('theta_width', float),
            Uniform('phi_width', float),
            Uniform('face_color', float),
            Uniform('angle', float),
            Uniform('background', float),
            Uniform('draw_background', float),
            Uniform('use_alpha', float)
        ]

        # reference for modular arithmetic: https://fgiesen.wordpress.com/2015/09/24/intervals-in-modular-arithmetic/

        calc_color = '''
            // compute relative x coordinates of pixel
            float rx = mod(theta-theta_center, 2*M_PI);
            if (rx >= M_PI) {
                rx -= 2*M_PI;
            }
            
            // compute relative y coordinates of pixel
            float ry = mod(phi-phi_center, 2*M_PI);
            if (ry >= M_PI) {
                ry -= 2*M_PI;
            }
            
            // compute displacement from center
            float dx = dot(vec2(+cos(angle), +sin(angle)), vec2(rx, ry));
            float dy = dot(vec2(-sin(angle), +cos(angle)), vec2(rx, ry));
               
            // check if pixel is within face
            if ((abs(dx) <= (0.5*theta_width)) && (abs(dy) <= (0.5*phi_width))){
                if (use_alpha == 0.0) {
                    color = face_color;
                } else {
                    color = background;
                    alpha = face_color;
                }
                
            } else if (draw_background == 1.0) {
                color = background;
            } else {
                alpha = 0.0;
            }
        '''

        super().__init__(screen=screen, uniforms=uniforms, calc_color=calc_color)

    def make_config_options(self, *args, trajectory=None, **kwargs):
        # set default
        if trajectory is None:
            trajectory = RectangleTrajectory().to_dict()

        # convert the input dictionary to a trajectory object
        trajectory = RectangleTrajectory.from_dict(trajectory)

        return super().make_config_options(*args, trajectory=trajectory, **kwargs)

    def configure(self, trajectory=None, background=0.0, vary='intensity'):
        """
        Stimulus consisting of a patch that moves along an arbitrary trajectory.
        :param background: Background color (0.0 to 1.0)
        :param trajectory: RectangleTrajectory converted to dictionary (to_dict method)
        """

        # set the trajectory
        self.trajectory = trajectory

        # set uniforms
        self.prog['use_alpha'].value = 0.0 if vary=='intensity' else 1.0
        self.prog['draw_background'].value = 1.0 if background is not None else 0.0
        if background is not None:
            self.prog['background'].value = background

    def eval_at(self, t):
        self.prog['theta_center'].value = radians(self.trajectory.x.eval_at(t))
        self.prog['phi_center'].value = radians(self.trajectory.y.eval_at(t))
        self.prog['theta_width'].value = radians(self.trajectory.w.eval_at(t))
        self.prog['phi_width'].value = radians(self.trajectory.h.eval_at(t))
        self.prog['angle'].value = radians(self.trajectory.angle.eval_at(t))
        self.prog['face_color'].value = self.trajectory.color.eval_at(t)

class RandomBars(BaseProgram):
    def __init__(self, screen, max_face_colors=64):
        self.max_face_colors = max_face_colors

        uniforms = [
            Uniform('phi_min', float),
            Uniform('phi_max', float),
            Uniform('theta_min', float),
            Uniform('theta_max', float),
            Uniform('theta_period', float),
            Uniform('theta_offset', float),
            Uniform('theta_duty', float),
            Uniform('background', float),
            Uniform('face_colors', float, max_face_colors)
        ]

        calc_color = '''
            float theta_rel = theta - theta_offset;
            if ((phi_min <= phi) && (phi <= phi_max) && (fract(theta_rel/theta_period) <= theta_duty)){
                if (theta_rel < 0) {
                    theta_rel += 2*M_PI;
                }
                color = face_colors[int(theta_rel/theta_period)];
            } else {
                color = background;
            }
        '''

        super().__init__(screen=screen, uniforms=uniforms, calc_color=calc_color)

    def configure(self, period=15, vert_extent=30, width=2, rand_min=0.0, rand_max=1.0, start_seed=0,
                  update_rate=60.0, background=0.5):
        """
        Bars surrounding the viewer change brightness randomly.
        :param period: Period of the bars surrounding the viewer.
        :param vert_extent: Vertical extent of each bar, in degrees.  With respect to the equator of the viewer, the
        top of each bar is at +vert_extent (degrees) and the bottom is at -vert_extent (degrees)
        :param width: Width of each bar in degrees.
        :param rand_min: Minimum output of random number generator
        :param rand_max: Maximum output of random number generator
        :param start_seed: Starting seed for the random number generator
        :param update_rate: Rate at which color is updated
        :param background: Monochromatic background color (0.0 is black, 1.0 is white)
        """

        # save settings
        self.rand_min = rand_min
        self.rand_max = rand_max
        self.start_seed = start_seed
        self.update_rate = update_rate

        # create the bars
        self.prog['phi_min'].value = pi/2-radians(vert_extent)
        self.prog['phi_max'].value = pi/2+radians(vert_extent)
        self.prog['theta_period'].value = radians(period)
        self.prog['theta_offset'].value = -radians(period)/2.0
        self.prog['theta_duty'].value = width/period
        self.prog['background'].value = background

    def eval_at(self, t):
        # set the seed
        seed = int(round(self.start_seed + t*self.update_rate))
        random.seed(seed)

        # compute the list of random values
        rand_colors = [random.uniform(self.rand_min, self.rand_max) for _ in range(self.max_face_colors)]

        # write to GPU
        self.prog['face_colors'].value = rand_colors

class SequentialBars(BaseProgram):
    def __init__(self, screen):
        uniforms = [
            Uniform('theta_offset', float),
            Uniform('theta_period', float),
            Uniform('thresh_first', float),
            Uniform('thresh_second', float),
            Uniform('color_first', float),
            Uniform('color_second', float),
            Uniform('background', float),
            Uniform('enable_first', bool),
            Uniform('enable_second', bool)
        ]

        calc_color = '''
            float theta_fract = fract((theta - theta_offset)/theta_period);
            if (enable_first && (theta_fract <= thresh_first)) {
                color = color_first;
            } else if (enable_second && (thresh_first < theta_fract) && (theta_fract <= thresh_second)) {
                color = color_second;
            } else {
                color = background;
            }
        '''

        super().__init__(screen=screen, uniforms=uniforms, calc_color=calc_color)

    def configure(self, width=5, period=20, offset=0, first_active_bright=True, second_active_bright=True,
                 first_active_time=1, second_active_time=2, background=0.5):
        """
        Stimulus in which one set of bars appears first, followed by a second set some time later.
        :param width: Width of the bars (same for the first and second set).
        :param period: Period of the bar pattern (same for the first and second set).
        :param offset: Offset in degrees of the bar pattern, which can be used to rotate the entire pattern
        around the viewer.
        :param first_active_bright: Boolean value.  If True, the first set of bars appear white when active.  If
        False, they will appear black when active.
        :param second_active_bright: Boolean value.  If True, the second set of bars appear white when active.  If
        False, they will appear black when active.
        :param first_active_time: Time in seconds when the first set of bars become active.
        :param second_active_time: Time in seconds when the second set of bars become active.
        :param background: Monochromatic background color (0.0 is black, 1.0 is white)
        """

        # save settings
        self.first_active_time  = first_active_time
        self.second_active_time = second_active_time

        # configure program
        self.prog['theta_offset'].value  = offset
        self.prog['theta_period'].value  = radians(period)
        self.prog['thresh_first'].value  = 1.0*width/period
        self.prog['thresh_second'].value = 2.0*width/period
        self.prog['color_first'].value = 1.0 if first_active_bright else 0.0
        self.prog['color_second'].value = 1.0 if second_active_time else 0.0
        self.prog['background'].value = background

    def eval_at(self, t):
        self.prog['enable_first'].value = (t >= self.first_active_time)
        self.prog['enable_second'].value = (t >= self.second_active_time)

class GridStim(BaseProgram):
    def __init__(self, screen, max_theta=256, max_phi=128):
        # initialize the random map
        self.max_theta = max_theta
        self.max_phi = max_phi

        uniforms = [
            Uniform('phi_period', float),
            Uniform('theta_period', float),
            Texture('grid_values')
        ]

        calc_color = '''
            if (theta < 0) {
                theta += 2*M_PI;
            } 
            
            int theta_int = int(theta/theta_period);
            int phi_int = int(phi/phi_period);
        
            color = texelFetch(grid_values, ivec2(theta_int, phi_int), 0).r;
        '''

        super().__init__(screen=screen, uniforms=uniforms, calc_color=calc_color)

    def initialize(self, ctx):
        # ref: https://github.com/cprogrammer1994/ModernGL/blob/6b0f5851539da4170596f62456bac0c22024e754/examples/conways_game_of_life.py
        patches = np.zeros((self.max_phi, self.max_theta)).astype('f4')
        self.texture = ctx.texture((self.max_theta, self.max_phi), 1, patches.tobytes(), dtype='f4')
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.texture.swizzle = 'RRR1'
        self.texture.use()

        super().initialize(ctx)


class RandomGrid(GridStim):
    def make_config_options(self, *args, distribution_data=None, **kwargs):
        if distribution_data is None:
            distribution_data = {'name':'Uniform',
                                 'args':[0, 1],
                                 'kwargs':{}}

        noise_distribution = getattr(distribution,distribution_data['name'])(*distribution_data.get('args',[]), **distribution_data.get('kwargs',{}))

        return super().make_config_options(*args, noise_distribution=noise_distribution, **kwargs)

    def configure(self, theta_period=15, phi_period=15, start_seed=0, update_rate=60.0,
                  noise_distribution = None):
        """
        Patches surrounding the viewer change brightness randomly.
        :param theta_period: Longitude period of the checkerboard patches (degrees)
        :param phi_period: Latitude period of the checkerboard patches (degrees)
        :param start_seed: Starting seed for the random number generator
        :param update_rate: Rate at which color is updated
        :param distribution_data: dict of distribution type and args, see flystim.distribution method
        """

        # save settings
        self.start_seed = start_seed
        self.update_rate = update_rate

        # write program settings
        self.prog['phi_period'].value = radians(phi_period)
        self.prog['theta_period'].value = radians(theta_period)
        
        # get the noise distribution
        self.noise_distribution = noise_distribution
        
    def eval_at(self, t):
        # set the seed
        seed = int(round(self.start_seed + t*self.update_rate))
        np.random.seed(seed)
        
        face_colors = self.noise_distribution.get_random_values((self.max_phi, self.max_theta))

        # write to GPU
        self.texture.write(face_colors.astype('f4'))
        self.texture.use()

class Checkerboard(GridStim):
    def configure(self, theta_period=2, phi_period=2):
        """
        Patches surrounding the viewer are arranged in a periodic checkerboard.
        :param theta_period: Longitude period of the checkerboard patches (degrees)
        :param phi_period: Latitude period of the checkerboard patches (degrees)
        """

        # write program settings
        self.prog['phi_period'].value = radians(phi_period)
        self.prog['theta_period'].value = radians(theta_period)

        # create the pattern
        # row = y (phi) coord
        # col = x (theta) coord
        face_colors  = np.zeros((self.max_phi, self.max_theta))
        face_colors[0::2, 0::2] = 1
        face_colors[1::2, 1::2] = 1

        # write the pattern
        self.texture.write(face_colors.astype('f4'))

    def eval_at(self, t):
        self.texture.use()