#!/usr/bin/env python3

# Example program showing rendering onto three subscreens

from flystim.draw import draw_screens
from flystim.trajectory import RectangleTrajectory
from flystim.screen import Screen
from flystim.stim_server import launch_stim_server

from time import sleep

def dir_to_tri_list(dir):
    # set screen width and height
    w = 1
    h = 1

    # set coordinates as a function of direction
    if dir == 'w':
        pts = [
            ((-0.6, -0.6), (-w/2, -w/2, -h/2)),
            ((-0.2, -0.6), (-w/2, +w/2, -h/2)),
            ((-0.2, -0.2), (-w/2, +w/2, +h/2)),
            ((-0.6, -0.2), (-w/2, -w/2, +h/2))
        ]
    elif dir == 'n':
        pts = [
            ((-0.6, +0.2), (-w/2, +w/2, -h/2)),
            ((-0.2, +0.2), (+w/2, +w/2, -h/2)),
            ((-0.2, +0.6), (+w/2, +w/2, +h/2)),
            ((-0.6, +0.6), (-w/2, +w/2, +h/2))
        ]

    elif dir == 'e':
        pts = [
            ((+0.2, +0.2), (+w/2, +w/2, -h/2)),
            ((+0.6, +0.2), (+w/2, -w/2, -h/2)),
            ((+0.6, +0.6), (+w/2, -w/2, +h/2)),
            ((+0.2, +0.6), (+w/2, +w/2, +h/2))
        ]
    else:
        raise ValueError('Invalid direction.')

    return Screen.quad_to_tri_list(*pts)

def make_tri_list():
    return dir_to_tri_list('w') + dir_to_tri_list('n') + dir_to_tri_list('e')

def main():
    screen = Screen(fullscreen=False, tri_list=make_tri_list())

    #####################################################
    # part 1: draw the screen configuration
    #####################################################

    draw_screens(screen)

    #####################################################
    # part 2: display a stimulus
    #####################################################

    manager = launch_stim_server(screen)

    trajectory = RectangleTrajectory(x=[(0,0),(10,360)], y=90, w=30, h=180)

    manager.load_stim(name='MovingPatch', trajectory=trajectory.to_dict())
    sleep(1)

    manager.start_stim()
    sleep(5)

    manager.stop_stim()
    sleep(1)

if __name__ == '__main__':
    main()
