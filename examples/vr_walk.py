#!/usr/bin/env python3
from flystim.stim_server import launch_stim_server
from flystim.screen import Screen
from flystim.trajectory import Trajectory
import numpy as np
from flystim.draw import draw_screens

from time import sleep

def main():
    pa = ((-1, -1), (-0.1, 0.2, -0.1))
    pb = ((+1, -1), (0.1, 0.2, -0.1))
    pc = ((-1, +1), (-0.1, 0.2, 0.1))
    p4 = ((+1, +1), (0.1, 0.2, 0.1))


    triangles = Screen.quad_to_tri_list(pa, pb, pc, p4)

    screen = Screen(tri_list=triangles, id=0, fullscreen=False, vsync=True, square_size=(0.18, 0.25), square_loc=(0.78, -0.86), name='Left', horizontal_flip=False)

    draw_screens(screen)

    manager = launch_stim_server(screen)


    manager.load_stim(name='ConstantBackground', color = [0.5, 0.5, 0.5, 1.0], side_length=100)
    manager.load_stim(name='Floor', color=[0.5, 0.5, 0.5, 1.0], z_level=-0.25, side_length=5, hold=True)

    z_level = -0.2
    manager.load_stim(name='Tower', color=[1, 0, 0, 1.0], cylinder_location=[-0.25, +1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) # red, +y, left
    manager.load_stim(name='Tower', color=[0, 1, 0, 1.0], cylinder_location=[0.0, +1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) # green, +y, center
    manager.load_stim(name='Tower', color=[0, 0, 1, 1], cylinder_location=[+0.25, +1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) # blue, +y, right

    manager.load_stim(name='Tower', color=[1, 1, 0, 1.0], cylinder_location=[-0.25, -1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) # -y, left
    manager.load_stim(name='Tower', color=[0, 1, 1, 1.0], cylinder_location=[0.0, -1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) #g-b -y, center
    manager.load_stim(name='Tower', color=[1, 0, 1, 1], cylinder_location=[+0.25, -1, z_level],  cylinder_height=0.1, cylinder_radius=0.05, hold=True) #purple -y, right


    tt = np.arange(0, 12, 0.01) # seconds
    velocity_x = 0.0 # meters per sec
    velocity_y = 0.2

    xx = tt * velocity_x
    yy = tt * velocity_y

    # dtheta = 0.0*np.random.normal(size=len(tt))
    dtheta = tt * 0.0
    theta = np.cumsum(dtheta)

    fly_x_trajectory = Trajectory(list(zip(tt, xx))).to_dict()
    fly_y_trajectory = Trajectory(list(zip(tt, yy))).to_dict()
    fly_theta_trajectory = Trajectory(list(zip(tt, theta))).to_dict()
    manager.set_fly_trajectory(fly_x_trajectory,
                               fly_y_trajectory,
                               fly_theta_trajectory)

    sleep(0.5)

    manager.start_stim()
    sleep(8)

    manager.stop_stim(print_profile=True)
    sleep(0.5)

if __name__ == '__main__':
    main()
