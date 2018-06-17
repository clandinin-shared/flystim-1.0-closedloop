# ref: https://github.com/cprogrammer1994/ModernGL/blob/master/examples/julia_fractal.py

import moderngl
import numpy as np
import os.path

class SineOpts:
    def __init__(self, a_coeff, b_coeff, c_coeff, d_coeff):
        # save settings
        self.a_coeff = a_coeff
        self.b_coeff = b_coeff
        self.c_coeff = c_coeff
        self.d_coeff = d_coeff

class SineProgram:
    def __init__(self, screen):
        # save settings
        self.screen = screen

    def initialize(self, ctx):
        # save context
        self.ctx = ctx

        # find path to shader directory
        this_file_path = os.path.realpath(os.path.expanduser(__file__))
        shader_dir = os.path.join(os.path.dirname(os.path.dirname(this_file_path)), 'shaders')

        # load vertex shader
        self.prog = self.ctx.program(
            vertex_shader = open(os.path.join(shader_dir, 'rect.vert'), 'r').read(),
            fragment_shader = open(os.path.join(shader_dir, 'sine.frag'), 'r').read()
        )

        # create VBO to represent vertex positions
        vert_data = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        vbo_vert = self.ctx.buffer(vert_data.astype('f4').tobytes())

        # create VBO to represent instance data
        inst_data = np.array([-1.0, +1.0, -1.0, +1.0, 0.0])
        vbo_inst = self.ctx.buffer(inst_data.astype('f4').tobytes())

        # create the layout of input data
        vao_content = [
            (vbo_vert, '2f', 'pos'),
            (vbo_inst, '1f 1f 1f 1f 1f/i', 'x_min', 'x_max', 'y_min', 'y_max', 'color')
        ]

        # create vertex array object
        self.vao = self.ctx.vertex_array(self.prog, vao_content)

        # write screen parameters
        self.prog['screen_offset'].value = tuple(self.screen.offset)
        self.prog['screen_vector'].value = tuple(self.screen.vector)
        self.prog['screen_height'].value = self.screen.height

    def paint(self, sine_opts, background_color):
        self.ctx.clear(*background_color)

        self.prog['a_coeff'].value = sine_opts.a_coeff
        self.prog['b_coeff'].value = sine_opts.b_coeff
        self.prog['c_coeff'].value = sine_opts.c_coeff
        self.prog['d_coeff'].value = sine_opts.d_coeff

        self.vao.render(mode=moderngl.TRIANGLE_STRIP, instances=1)