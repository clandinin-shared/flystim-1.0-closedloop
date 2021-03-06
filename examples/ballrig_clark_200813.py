#!/usr/bin/env python3

# Example program showing rendering onto three subscreens

import logging
#import PySpin

from flystim.draw import draw_screens
from flystim.trajectory import RectangleTrajectory
from flystim.screen import Screen
from flystim.stim_server import launch_stim_server

from time import sleep, time
import numpy as np
import math
import socket
import os, subprocess
import json

import matplotlib.pyplot as plt

def dir_to_tri_list(dir):

    north_w = 3.0e-2
    side_w = 2.96e-2

    # set coordinates as a function of direction
    if dir == 'w':
       # set screen width and height
       h = 2.94e-2
       pts = [
            ((+0.4925, -0.3750), (-north_w/2, -side_w/2, -h/2)),
            ((+0.4800, -0.6975), (-north_w/2, +side_w/2, -h/2)),
            ((+0.2875, -0.6800), (-north_w/2, +side_w/2, +h/2)),
            ((+0.2925, -0.3550), (-north_w/2, -side_w/2, +h/2))
        ]
    elif dir == 'n':
       # set screen width and height
       h = 3.29e-2
       pts = [
            ((+0.1700, +0.5700), (-north_w/2, +side_w/2, -h/2)),
            ((+0.1700, +0.2675), (+north_w/2, +side_w/2, -h/2)),
            ((-0.0275, +0.2675), (+north_w/2, +side_w/2, +h/2)),
            ((-0.0300, +0.5675), (-north_w/2, +side_w/2, +h/2))
        ]

    elif dir == 'e':
        # set screen width and height
        h = 3.18e-2
        pts = [
            ((-0.1600, -0.3275), (+north_w/2, +side_w/2, -h/2)),
            ((-0.1500, -0.6200), (+north_w/2, -side_w/2, -h/2)),
            ((-0.3575, -0.6500), (+north_w/2, -side_w/2, +h/2)),
            ((-0.3675, -0.3500), (+north_w/2, +side_w/2, +h/2))
        ]
    else:
        raise ValueError('Invalid direction.')

    return Screen.quad_to_tri_list(*pts)

def make_tri_list():
    return dir_to_tri_list('w') + dir_to_tri_list('n') + dir_to_tri_list('e')

def fictrac_get_data(sock):
    data = sock.recv(1024)

    # Decode received data
    line = data.decode('UTF-8')
    endline = line.find("\n")
    line = line[:endline]
    toks = line.split(", ")

    #logging.debug("Received from fictrac socket: %s", line)

    # Fixme: sometimes we read more than one line at a time,
    # should handle that rather than just dropping extra data...
    if ((len(toks) < 7) | (toks[0] != "FT")):
        logging.warning("Bad read, too few tokens: %s", line)
        return fictrac_get_data(sock)
        #continue

    if len(toks) > 7:
        logging.warning("Bad read, too many tokens: %s", line)
        return fictrac_get_data(sock)

    posx = float(toks[1])
    posy = float(toks[2])
    heading = float(toks[3])
    timestamp = float(toks[4])
    sync_mean = float(toks[5])

    return (posx, posy, heading, timestamp, sync_mean)


def main():
    # Set lightcrafter and GL environment settings
    os.system('/home/clandinin/miniconda3/bin/lcr_ctl --fps 120 --blue_current 2.1 --green_current 2.1')
    os.system('bash /home/clandinin/flystim/src/flystim/examples/closed_loop_GL_env_set.sh')
    '''
    #Camera boundaries
    CAM_WIDTH = 752
    CAM_HEIGHT = 616
    CAM_OFFSET_X = 328
    CAM_OFFSET_Y = 336

    try:
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        assert cam_list.GetSize() == 1
        cam = cam_list[0]
        cam.Init()
        nodemap = cam.GetNodeMap()
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
            node_width.SetValue(CAM_WIDTH)
            print('Cam Width set to %i...' % node_width.GetValue())
        else:
            print('Cam Width not available...')
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
            node_height.SetValue(CAM_HEIGHT)
            print('Cam Height set to %i...' % node_height.GetValue())
        else:
            print('Cam Height not available...')
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
            node_offset_x.SetValue(CAM_OFFSET_X)
            print('Cam OffsetX set to %i...' % node_offset_x.GetValue())
        else:
            print('Cam OffsetX not available...')
        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
            node_offset_y.SetValue(CAM_OFFSET_Y)
            print('Cam OffsetY set to %i...' % node_offset_y.GetValue())
        else:
            print('Cam OffsetY not available...')
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
    '''
    # Create screen object
    screen = Screen(server_number=1, id=1,fullscreen=True, tri_list=make_tri_list(), vsync=False, square_side=0.01, square_loc=(0.59,0.74))#square_side=0.08, square_loc='ur')
    print(screen)

    FICTRAC_HOST = '127.0.0.1'  # The server's hostname or IP address
    FICTRAC_PORT = 33334         # The port used by the server
    RADIUS = 0.0045 # in meters; i.e. 4.5mm

    #####################################################
    # part 1: draw the screen configuration
    #####################################################

    #draw_screens(screen)

    #####################################################
    # part 2: User defined parameters
    #####################################################


    trial_labels = np.array([0,1]) # visible, coherent. 00, 01, 10, 11
    n_repeats = 1
    save_history = True
    save_path = "/home/clandinin/minseung/ballrig_data"
    save_prefix = "200818_clark_test4"
    save_path = save_path + os.path.sep + save_prefix
    if save_history:
        os.mkdir(save_path)

    genotype = "isoA1-F"
    age = 3

    ft_frame_rate = 250 #Hz, higher
    fs_frame_rate = 120

    stim_duration = 10
    speed = 30 #degrees per sec
    iti = 5 #seconds

    background_color = 0.5

    params = {'genotype':genotype, 'age':age, 'n_repeats':n_repeats, 'save_path':save_path, 'save_prefix': save_prefix, 'ft_frame_rate': ft_frame_rate, 'speed': speed, 'background_color': background_color}

    #####################################################
    # part 3: stimulus definitions
    #####################################################

    # Trial structure
    trial_structure = np.random.permutation(np.repeat(trial_labels, n_repeats))
    n_trials = len(trial_structure)
    params['n_trials'] = n_trials
    params['trial_structure'] = np.array2string(trial_structure, precision=1, separator=',')

    # Create flystim trajectory objects
    #exp_bar = RectangleTrajectory(x=exp_traj, y=90, w=bar_width, h=bar_height, color=bar_color)

    if save_history:
        with open(save_path+os.path.sep+save_prefix+'_params.txt', "w") as text_file:
            print(json.dumps(params), file=text_file)

    # Set up logging
    logging.basicConfig(
        format='%(asctime)s %(message)s',
        filename="{}/{}.log".format(save_path, save_prefix),
        level=logging.DEBUG
    )

    # Start stim server
    manager = launch_stim_server(screen)
    if save_history:
        manager.set_save_history_params(save_history_flag=save_history, save_path=save_path, fs_frame_rate_estimate=fs_frame_rate, stim_duration=stim_duration)
    manager.set_idle_background(background_color)

    #####################################################
    # part 3: start the loop
    #####################################################

    #p = subprocess.Popen(["/home/clandinin/fictrac_test/bin/fictrac","/home/clandinin/fictrac_test/config1.txt"], start_new_session=True)
    p = subprocess.Popen(["/home/clandinin/fictrac_test/bin/fictrac","/home/clandinin/fictrac_test/config_smaller_window.txt","-v","ERR"], start_new_session=True)
    sleep(2)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fictrac_sock:
        fictrac_sock.connect((FICTRAC_HOST, FICTRAC_PORT))

        t_iti_start = time()
        for t in range(n_trials):
            # begin trial
            ft_sync_means = []
            ft_timestamps = []
            ft_posx = []
            ft_posy = []
            ft_theta = []

            while (time() - t_iti_start) < iti:
                _ = fictrac_get_data(fictrac_sock)

            manager.load_stim(name='SineGrating', rate=10, background=background_color, hold=True)

            print ("===== Trial " + str(t) + " ======")
            t_start = time()
            manager.start_stim()
            posx_0, posy_0, theta_0, _, _ = fictrac_get_data(fictrac_sock)

            while (time() -  t_start) < stim_duration:
                posx, posy, theta_rad, timestamp, sync_mean = fictrac_get_data(fictrac_sock)
                posx = posx - posx_0
                posy = posy - posy_0
                theta_rad = -(theta_rad - theta_0)
                ft_sync_means.append(sync_mean)
                ft_timestamps.append(time())
                ft_posx.append(posx)
                ft_posy.append(posy)
                ft_theta.append(theta_rad)

            manager.stop_stim()
            # Save things
            if save_history:
                save_prefix_with_trial = save_prefix+"_t"+f'{t:03}'
                manager.set_save_prefix(save_prefix_with_trial)
                manager.save_history()
                np.savetxt(save_path+os.path.sep+save_prefix_with_trial+'_ft_square.txt', np.array(ft_sync_means), delimiter='\n')
                np.savetxt(save_path+os.path.sep+save_prefix_with_trial+'_ft_timestamps.txt', np.array(ft_timestamps), delimiter='\n')
                np.savetxt(save_path+os.path.sep+save_prefix_with_trial+'_ft_posx.txt', np.array(ft_posx), delimiter='\n')
                np.savetxt(save_path+os.path.sep+save_prefix_with_trial+'_ft_posy.txt', np.array(ft_posy), delimiter='\n')
                np.savetxt(save_path+os.path.sep+save_prefix_with_trial+'_ft_theta.txt', np.array(ft_theta), delimiter='\n')

            #sleep(2)
            t_iti_start = time()

    p.terminate()
    p.kill()

    #plt.plot(ft_sync_means)
    #plt.show()

if __name__ == '__main__':
    main()
