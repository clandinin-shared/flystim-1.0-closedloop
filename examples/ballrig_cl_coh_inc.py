#!/usr/bin/env python3

# Example program showing rendering onto three subscreens

import logging

from flystim.draw import draw_screens
from flystim.trajectory import RectangleTrajectory
from flystim.screen import Screen
from flystim.stim_server import launch_stim_server
from flystim.util import latency_report

from time import sleep, time, strftime, localtime
import numpy as np
import math
from math import degrees
import itertools
import os, subprocess
import h5py
import socket
import select

import matplotlib.pyplot as plt

from ballrig_analysis.utils import fictrac_utils

FT_FRAME_NUM_IDX = 0
FT_THETA_IDX = 16
FT_TIMESTAMP_IDX = 21
FT_SQURE_IDX = 25

def dir_to_tri_list(dir):

    north_w = 2.956e-2
    side_w = 2.96e-2

    # set coordinates as a function of direction
    if dir == 'w':
       # set screen width and height
       h = 3.10e-2
       pts = [
            ((+0.4900, -0.3400), (-north_w/2, -side_w/2, -h/2)),
            ((+0.4900, -0.6550), (-north_w/2, +side_w/2, -h/2)),
            ((+0.2850, -0.6550), (-north_w/2, +side_w/2, +h/2)),
            ((+0.2850, -0.3400), (-north_w/2, -side_w/2, +h/2))
        ]
    elif dir == 'n':
       # set screen width and height
       h = 3.29e-2
       pts = [
            ((+0.1850, +0.5800), (-north_w/2, +side_w/2, -h/2)),
            ((+0.1850, +0.2800), (+north_w/2, +side_w/2, -h/2)),
            ((-0.0200, +0.2800), (+north_w/2, +side_w/2, +h/2)),
            ((-0.0200, +0.5800), (-north_w/2, +side_w/2, +h/2))
        ]

    elif dir == 'e':
        # set screen width and height
        h = 3.40e-2
        pts = [
            ((-0.1350, -0.3550), (+north_w/2, +side_w/2, -h/2)),
            ((-0.1350, -0.6550), (+north_w/2, -side_w/2, -h/2)),
            ((-0.3500, -0.6550), (+north_w/2, -side_w/2, +h/2)),
            ((-0.3500, -0.3550), (+north_w/2, +side_w/2, +h/2))
        ]
    else:
        raise ValueError('Invalid direction.')

    return Screen.quad_to_tri_list(*pts)

def make_tri_list():
    return dir_to_tri_list('w') + dir_to_tri_list('n') + dir_to_tri_list('e')

ft_buffer = ""
def fictrac_get_data(sock):
    global ft_buffer

    # if not select.select([sock], [], [])[0]:
    #     return fictrac_get_data(sock)
    ready = select.select([sock], [], [])[0]
    if ready:
        data = sock.recv(4098)
    else:
        return fictrac_get_data(sock)

    # Decode received data
    ogline = data.decode('UTF-8')
    line = ft_buffer + ogline
    endline = line.rfind("\n")
    if endline == -1: # there is no linebreak
        startline = line.rfind("FT")
        if startline != -1: #there is line start
            line = line[startline:]
        ft_buffer += line # add (perhaps) trimmed line to buffer
        logging.warning("No line end: %s", line)
        return fictrac_get_data(sock)
    else: # there is a linebreak
        ft_buffer = line[endline:] # write everything after linebreak to the buffer
        line = line[:endline]
        startline = line.rfind("FT")
        if startline == -1: #there is no line start... this shouldn't happen bc we have a buffer
            logging.warning("No line start: %s", line)
            return fictrac_get_data(sock)
        else: # start line exists as well as a linebreak, so trim to the start
            line = line[startline:]

    # There is a complete line!
    toks = line.split(", ")

    if len(toks) != 27:
        logging.warning("This should not happen: %s", str(len(toks)) + ' ' + line)
        return fictrac_get_data(sock)

    frame_num = int(toks[FT_FRAME_NUM_IDX+1])
    heading = float(toks[FT_THETA_IDX+1])
    ts = float(toks[FT_TIMESTAMP_IDX+1])#

    return (frame_num, heading, ts)#

def handle_fictrac_data(fictrac_sock, manager, theta_rad_0):
    frame_num, theta_rad_1, ts = fictrac_get_data(fictrac_sock)#
    theta_rad = theta_rad_1 - theta_rad_0 if theta_rad_0 is not None else 0
    theta_deg = degrees(theta_rad)
    manager.set_global_theta_offset(theta_deg)
    return frame_num, theta_rad_1, ts#

def load_txt(fpath):
    with open(fpath, 'r') as handler:
        return np.array([float(line) for line in handler])


def main():
    #####################################################
    # part 1: draw the screen configuration
    #####################################################

    #draw_screens(screen)

    #####################################################
    # part 2: User defined parameters
    #####################################################

    if len(sys.argv) > 1 and sys.argv[1] == "run":
        save_history = True
    else:
        save_history = False

    parent_path = os.getcwd()
    save_prefix = strftime('%Y%m%d_%H%M%S', localtime())
    save_path = os.path.join(parent_path, save_prefix)
    if save_history:
        os.mkdir(save_path)

    genotype = "isoD1-F"
    age = 5
    temperature = 35.5 #6.30=36.2  6.36=36  6.90=34 6.82=34.3  6.75=34.5(33.7) no hum   #7.10=34  7.00=34.2  6.97=34.5 @ 44%
    humidity = 30 #(29)

    rgb_power = [0, 0.9, 0.9]

    ft_frame_rate = 309 #Hz, higher
    fs_frame_rate = 120

    current_time = strftime('%Y%m%d_%H%M%S', localtime())

    #####################################################
    # part 3: stimulus definitions
    #####################################################

    # Trial structure
    n_repeats = 35
    trial_labels = np.array(["inc_r","inc_l","coh_r","coh_l"]) # visible, coherent. 00, 01, 10, 11
    trial_structure = np.random.permutation(np.repeat(trial_labels, n_repeats))
    n_trials = len(trial_structure)

    # Stimulus parameters
    stim_name = "coherent_incoherent"
    speed = 30 #degrees per sec
    presample_duration = 2 #seconds
    sample_duration = 5 #seconds
    preocc_duration = 1 #seconds
    occlusion_duration = 2 #seconds
    postocc_duration = 1 #seconds
    stim_duration = presample_duration + sample_duration + preocc_duration + occlusion_duration + postocc_duration
    iti = 2 #seconds

    background_color = 0

    bar_width = 15
    bar_height = 150
    bar_color = 1
    #bar_angle = 0

    inc_seed = 0
    inc_n_samples = 15 # how many random waypoints should there be for control
    inc_noise_scale = 5

    occluder_height = 150
    occluder_color = 0.5

    #######################
    # Stimulus construction

    # Bar start location
    start_theta = 0

    # Coherent bar trajectory
    coh_time = [0, presample_duration]
    coh_x = [0, 0]

    coh_sample_movement = speed*sample_duration
    coh_sample_end_theta = coh_sample_movement
    coh_time.append(presample_duration+sample_duration)
    coh_x.append(coh_sample_end_theta)

    coh_postsample_movement = speed*(stim_duration-presample_duration-sample_duration)
    coh_end_theta = coh_sample_end_theta + coh_postsample_movement
    coh_time.append(stim_duration)
    coh_x.append(coh_end_theta)

    # Incoherent bar trajectory
    inc_time = [0, presample_duration]
    inc_x = [0, 0]

    np.random.seed(inc_seed)
    inc_sample_slow_traj = np.linspace(0, coh_sample_movement/2, num=inc_n_samples-1, endpoint=True)
    inc_sample_noise = np.random.normal(0, scale=inc_noise_scale, size=inc_n_samples-1) # control trajectory is random gaussian noise with n_samples
    inc_sample_times = np.linspace(start=presample_duration, stop=presample_duration+sample_duration, num=inc_n_samples-1, endpoint=False) + presample_duration/inc_n_samples
    #inc_sample_normalizer = coh_sample_movement/np.sum(np.abs(inc_sample_noise)) # makes contrl movement (sum of abs) sums to total movement of exp
    #inc_sample_traj = list(zip(inc_sample_times, start_theta - inc_sample_noise*inc_sample_normalizer))
    inc_sample_x = inc_sample_noise + inc_sample_slow_traj
    inc_sample_end_theta = inc_sample_x[-1]
    inc_time.extend(inc_sample_times)
    inc_x.extend(inc_sample_x)

    inc_postsample_movement = speed*(stim_duration-presample_duration-sample_duration)
    inc_end_theta = inc_sample_end_theta + inc_postsample_movement
    inc_time.append(stim_duration)
    inc_x.append(inc_end_theta)


    # Compute location and width of the occluder per specification
    preocc_movement = speed*preocc_duration
    coh_occ_duration_start_theta = coh_sample_end_theta + preocc_movement # of the bar
    inc_occ_duration_start_theta = inc_sample_end_theta + preocc_movement # of the bar

    occluder_width = occlusion_duration*speed + bar_width # the last term ensures that the bar is completely hidden during the occlusion period
    coh_occluder_loc = coh_occ_duration_start_theta + occluder_width/2 - bar_width/2 # the last two terms account for widths of the bar and the occluder, such that the bar is completely hidden during occlusion period
    coh_occluder_time = [0, stim_duration]
    coh_occluder_x = [coh_occluder_loc, coh_occluder_loc]
    inc_occluder_loc = inc_occ_duration_start_theta + occluder_width/2 - bar_width/2
    inc_occluder_time = [0, stim_duration]
    inc_occluder_x = [inc_occluder_loc, inc_occluder_loc]

    coh_bar_traj_r = list(zip(coh_time, (start_theta - np.array(coh_x)).tolist()))
    coh_bar_traj_l = list(zip(coh_time, (start_theta + np.array(coh_x)).tolist()))
    inc_bar_traj_r = list(zip(inc_time, (start_theta - np.array(inc_x)).tolist()))
    inc_bar_traj_l = list(zip(inc_time, (start_theta + np.array(inc_x)).tolist()))
    coh_occluder_traj_r = list(zip(coh_occluder_time, (start_theta - np.array(coh_occluder_x)).tolist()))
    coh_occluder_traj_l = list(zip(coh_occluder_time, (start_theta + np.array(coh_occluder_x)).tolist()))
    inc_occluder_traj_r = list(zip(inc_occluder_time, (start_theta - np.array(inc_occluder_x)).tolist()))
    inc_occluder_traj_l = list(zip(inc_occluder_time, (start_theta + np.array(inc_occluder_x)).tolist()))

    # Create flystim trajectory objects
    coh_bar_r = RectangleTrajectory(x=coh_bar_traj_r, y=90, w=bar_width, h=bar_height, color=bar_color)
    coh_occluder_r_visible = RectangleTrajectory(x=coh_occluder_traj_r, y=90, w=occluder_width, h=occluder_height, color=occluder_color)
    coh_occluder_r_invisible = RectangleTrajectory(x=coh_occluder_traj_r, y=90, w=occluder_width, h=occluder_height, color=background_color)
    inc_bar_r = RectangleTrajectory(x=inc_bar_traj_r, y=90, w=bar_width, h=bar_height, color=bar_color)
    inc_occluder_r_visible = RectangleTrajectory(x=inc_occluder_traj_r, y=90, w=occluder_width, h=occluder_height, color=occluder_color)
    inc_occluder_r_invisible = RectangleTrajectory(x=inc_occluder_traj_r, y=90, w=occluder_width, h=occluder_height, color=background_color)

    coh_bar_l = RectangleTrajectory(x=coh_bar_traj_l, y=90, w=bar_width, h=bar_height, color=bar_color)
    coh_occluder_l_visible = RectangleTrajectory(x=coh_occluder_traj_l, y=90, w=occluder_width, h=occluder_height, color=occluder_color)
    coh_occluder_l_invisible = RectangleTrajectory(x=coh_occluder_traj_l, y=90, w=occluder_width, h=occluder_height, color=background_color)
    inc_bar_l = RectangleTrajectory(x=inc_bar_traj_l, y=90, w=bar_width, h=bar_height, color=bar_color)
    inc_occluder_l_visible = RectangleTrajectory(x=inc_occluder_traj_l, y=90, w=occluder_width, h=occluder_height, color=occluder_color)
    inc_occluder_l_invisible = RectangleTrajectory(x=inc_occluder_traj_l, y=90, w=occluder_width, h=occluder_height, color=background_color)

    if save_history:
        params = {'genotype':genotype, 'age':age, \
            'save_path':save_path, 'save_prefix': save_prefix, \
            'ft_frame_rate': ft_frame_rate, 'fs_frame_rate':fs_frame_rate, \
            'rgb_power':rgb_power, 'current_time':current_time, \
            'temperature':temperature, 'humidity':humidity, \
            'trial_labels':trial_labels.tolist(), 'trial_structure':trial_structure.tolist(), \
            'n_repeats':n_repeats, 'n_trials':n_trials, 'stim_name':stim_name, \
            'stim_name':stim_name, 'speed':speed, 'presample_duration':presample_duration, \
            'sample_duration':sample_duration, 'preocc_duration':preocc_duration, \
            'occlusion_duration':occlusion_duration, 'postocc_duration':postocc_duration, \
            'stim_duration':stim_duration, 'iti':iti, 'background_color':background_color, \
            'bar_width':bar_width, 'bar_height':bar_height, 'bar_color':bar_color, \
            'inc_seed':inc_seed, 'inc_n_samples':inc_n_samples, \
            'inc_noise_scale':inc_noise_scale, 'occluder_height':occluder_height, \
            'occluder_color':occluder_color, 'start_theta':start_theta}

        params['coh_bar_traj_r'] = coh_bar_traj_r
        params['coh_bar_traj_l'] = coh_bar_traj_l
        params['inc_bar_traj_r'] = inc_bar_traj_r
        params['inc_bar_traj_l'] = inc_bar_traj_l
        params['coh_occluder_traj_r'] = coh_occluder_traj_r
        params['coh_occluder_traj_l'] = coh_occluder_traj_l
        params['inc_occluder_traj_r'] = inc_occluder_traj_r
        params['inc_occluder_traj_l'] = inc_occluder_traj_l


    #####################################################################

    # Set up logging
    if save_history:
        logging.basicConfig(
            format='%(asctime)s %(message)s',
            filename="{}/{}.log".format(save_path, save_prefix),
            level=logging.DEBUG
        )

    # Set lightcrafter and GL environment settings
    os.system('/home/clandinin/miniconda3/bin/lcr_ctl --fps 120 --red_current ' + str(rgb_power[0]) + ' --blue_current ' + str(rgb_power[2]) + ' --green_current ' + str(rgb_power[1]))

    # Create screen object
    screen = Screen(server_number=1, id=1,fullscreen=True, tri_list=make_tri_list(), vsync=False, square_side=0.01, square_loc=(0.59,0.74))#square_side=0.08, square_loc='ur')
    #print(screen)

    FICTRAC_HOST = '127.0.0.1'  # The server's hostname or IP address
    FICTRAC_PORT = 33334         # The port used by the server
    FICTRAC_BIN =    "/home/clandinin/lib/fictrac211/bin/fictrac"
    FICTRAC_CONFIG = "/home/clandinin/lib/fictrac211/config_MC_cl.txt"

    # Start stim server
    manager = launch_stim_server(screen)
    if save_history:
        manager.set_save_history_params(save_history_flag=save_history, save_path=save_path, fs_frame_rate_estimate=fs_frame_rate, save_duration=stim_duration+iti*2)
    manager.set_idle_background(background_color)

    #####################################################
    # part 3: start the loop
    #####################################################

    p = subprocess.Popen([FICTRAC_BIN, FICTRAC_CONFIG, "-v","ERR"], start_new_session=True)
    sleep(2)

    fictrac_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fictrac_sock.bind((FICTRAC_HOST, FICTRAC_PORT))
    fictrac_sock.setblocking(0)

    if save_history:
        trial_start_times = []
        trial_start_ft_frames = []
        trial_end_times = []
        trial_end_ft_frames = []

    # Pretend previous trial ended here before trial 0
    t_iti_start = time()
    ft_frame_num_00,_,_ = fictrac_get_data(fictrac_sock)

    # Loop through trials
    for t in range(n_trials):
        # begin trial

        if trial_structure[t] == "inc_r": # invisible, incoherent_r. 00, 01, 10, 11
            bar_traj = inc_bar_r
            occ_traj = inc_occluder_r_invisible
        elif trial_structure[t] == "coh_r": # invisible, coherent_r. 00, 01, 10, 11
            bar_traj = coh_bar_r
            occ_traj = coh_occluder_r_invisible
        elif trial_structure[t] == "inc_l": # invisible, incoherent_l. 00, 01, 10, 11
            bar_traj = inc_bar_l
            occ_traj = inc_occluder_l_invisible
        elif trial_structure[t] == "coh_l": # invisible, coherent_l. 00, 01, 10, 11
            bar_traj = coh_bar_l
            occ_traj = inc_occluder_l_invisible

        while (time() - t_iti_start) < iti/2:
            _,_,_ = fictrac_get_data(fictrac_sock)

        if save_history:
            manager.start_saving_history()

        while (time() - t_iti_start) < iti:
            _,_,_ = fictrac_get_data(fictrac_sock)

        print(f"===== Trial {t}; type {trial_structure[t]} ======")

        manager.set_global_theta_offset(0)
        manager.load_stim('MovingPatch', trajectory=bar_traj.to_dict(), background=background_color, hold=True)
        manager.load_stim('MovingPatch', trajectory=occ_traj.to_dict(), background=None, hold=True)
        theta_rad_0 = None

        t_start = time()
        manager.start_stim()
        while (time() -  t_start) < stim_duration:
            ft_frame_num, theta_rad, ts = handle_fictrac_data(fictrac_sock, manager, theta_rad_0)
            if theta_rad_0 is None: # i.e. first trial
                ft_frame_num_0, theta_rad_0, ts_0 = ft_frame_num, theta_rad, ts
        manager.stop_stim()
        t_end = time()
        t_iti_start = t_end
        ft_frame_num_end = ft_frame_num + 1

        print(f"===== Trial end (FT dur: {(ts-ts_0)/1000:.{5}}s)======")
        while (time() - t_iti_start) < iti/2:
            _,_,_ = fictrac_get_data(fictrac_sock)
        if save_history:
            manager.stop_saving_history()

        # Save things
        if save_history:
            save_prefix_with_trial = save_prefix+"_t"+f'{t:03}'
            manager.set_save_prefix(save_prefix_with_trial)
            manager.save_history()

            trial_start_times.append(t_start)
            trial_start_ft_frames.append(ft_frame_num_0)
            trial_end_times.append(t_end)
            trial_end_ft_frames.append(ft_frame_num_end)

    # Burn off the second half of last ITI
    while (time() - t_iti_start) < iti:
        continue

    # close fictrac
    fictrac_sock.close()
    p.terminate()
    p.kill()

    # Plot fictrac summary and save png
    fictrac_files = sorted([x for x in os.listdir(parent_path) if x[0:7]=='fictrac'])[-2:]
    ft_summary_save_fn = os.path.join(parent_path, save_prefix+".png") if save_history else None
    fictrac_utils.plot_ft_session_summary(os.path.join(parent_path, fictrac_files[0]), label=save_prefix, show=False, save=ft_summary_save_fn, window_size=5)

    if save_history:
        # Move fictrac files
        print ("Moving " + str(len(fictrac_files)) + " fictrac files.")
        for i in range(len(fictrac_files)):
            os.rename(os.path.join(parent_path, fictrac_files[i]), os.path.join(save_path, fictrac_files[i]))

        # Move Fictrac summary
        os.rename(os.path.join(parent_path, save_prefix+".png"), os.path.join(save_path, save_prefix+".png"))

        # Open up fictrac file
        fictrac_data_fn = fictrac_files[0]
        ft_data_handler = open(os.path.join(save_path, fictrac_data_fn), 'r')

        # Create h5f file
        h5f = h5py.File(os.path.join(save_path, save_prefix + '.h5'), 'a')
        # params
        for (k,v) in params.items():
            h5f.attrs[k] = v
        # trials group
        trials = h5f.require_group('trials')

        # Process through ft_data_handler until it gets to the frame iti before first trial
        start_frame_next_trial = trial_start_ft_frames[0]
        ft_frame_next = []
        ft_theta_next = []
        ft_timestamps_next = []
        ft_square_next = []

        curr_frame = 0
        while curr_frame < ft_frame_num_00:
            ft_line = ft_data_handler.readline()
            ft_toks = ft_line.split(", ")
            curr_frame = int(ft_toks[0])

        while curr_frame < start_frame_next_trial:
            ft_line = ft_data_handler.readline()
            ft_toks = ft_line.split(", ")
            curr_frame = int(ft_toks[FT_FRAME_NUM_IDX])
            ft_frame_next.append(curr_frame)
            ft_theta_next.append(float(ft_toks[FT_THETA_IDX]))
            ft_timestamps_next.append(float(ft_toks[FT_TIMESTAMP_IDX]))
            ft_square_next.append(float(ft_toks[FT_SQURE_IDX]))

        # Loop through trials and create trial groups and datasets
        ft_line = ft_data_handler.readline()
        for t in range(n_trials):
            save_prefix_with_trial = save_prefix+"_t"+f'{t:03}'
            save_dir_prefix = os.path.join(save_path, save_prefix_with_trial)

            fs_square = load_txt(save_dir_prefix+'_fs_square.txt')
            fs_timestamps = load_txt(save_dir_prefix+'_fs_timestamps.txt')
            fs_stim_timestamps = load_txt(save_dir_prefix+'_fs_stim_timestamps.txt')
            fs_theta = load_txt(save_dir_prefix+'_fs_theta.txt')

            ft_frame = ft_frame_next
            ft_theta = ft_theta_next
            ft_timestamps = ft_timestamps_next
            ft_square = ft_square_next
            ft_frame_next = []
            ft_theta_next = []
            ft_timestamps_next = []
            ft_square_next = []

            if t < n_trials-1:
                start_frame_next_trial = trial_start_ft_frames[t+1]
            else: #t == n_trials-1
                start_frame_next_trial = np.infty

            while ft_line!="" and curr_frame < start_frame_next_trial:
                ft_toks = ft_line.split(", ")
                curr_frame = int(ft_toks[FT_FRAME_NUM_IDX])
                ft_frame.append(curr_frame)
                ft_theta.append(float(ft_toks[FT_THETA_IDX]))
                ft_timestamps.append(float(ft_toks[FT_TIMESTAMP_IDX]))
                ft_square.append(float(ft_toks[FT_SQURE_IDX]))
                if curr_frame >= trial_end_ft_frames[t]:
                    ft_frame_next.append(curr_frame)
                    ft_theta_next.append(float(ft_toks[FT_THETA_IDX]))
                    ft_timestamps_next.append(float(ft_toks[FT_TIMESTAMP_IDX]))
                    ft_square_next.append(float(ft_toks[FT_SQURE_IDX]))
                ft_line = ft_data_handler.readline()

            # trial
            trial = trials.require_group(f'{t:03}')

            # start time for trial
            trial.attrs['start_time'] = trial_start_times[t]
            trial.attrs['start_ft_frame'] = trial_start_ft_frames[t]
            trial.attrs['end_time'] = trial_end_times[t]
            trial.attrs['end_ft_frame'] = trial_end_ft_frames[t]
            trial.create_dataset("fs_square", data=fs_square)
            trial.create_dataset("fs_timestamps", data=fs_timestamps)
            trial.create_dataset("fs_stim_timestamps", data=fs_stim_timestamps)
            trial.create_dataset("fs_theta", data=fs_theta)
            trial.create_dataset("ft_frame", data=ft_frame)
            trial.create_dataset("ft_square", data=ft_square)
            trial.create_dataset("ft_timestamps", data=np.array(ft_timestamps)/1e3)
            trial.create_dataset("ft_theta", data=ft_theta)

        ft_data_handler.close()
        h5f.close()

        # Delete flystim txt output files
        fs_txt_files = [x for x in os.listdir(save_path) if x.startswith(save_prefix) and x.endswith('.txt')]
        for txt_fn in fs_txt_files:
            os.remove(os.path.join(save_path, txt_fn))

        # Move hdf5 file out to parent path
        os.rename(os.path.join(save_path, save_prefix + '.h5'), os.path.join(parent_path, save_prefix + '.h5'))

        # Latency report
        with h5py.File(os.path.join(parent_path, save_prefix + '.h5'), 'r') as h5f:
            for t in range(0,n_trials,int(np.ceil(n_trials/5))):
                trial = h5f['trials'][f'{t:03}']
                fs_square = trial['fs_square'][()]
                fs_timestamps = trial['fs_timestamps'][()]
                ft_square = trial['ft_square'][()]
                ft_timestamps = trial['ft_timestamps'][()]
                print ("===== Trial " + str(t) + " ======")
                latency_report(fs_timestamps, fs_square, ft_timestamps, ft_square, window_size=1)

        # #Plot sync means
        # fig_square = plt.figure()
        # plt.plot(ft_square)
        # fig_square.show()

    else: #not saving history
        # Delete fictrac files
        print ("Deleting " + str(len(fictrac_files)) + " fictrac files.")
        for i in range(len(fictrac_files)):
            os.remove(os.path.join(parent_path, fictrac_files[i]))


if __name__ == '__main__':
    main()
