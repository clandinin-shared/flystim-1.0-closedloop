#!/usr/bin/env python3

# Example client program that randomly cycles through different rotation rates.
# The stim_type can be either SineGrating or RotatingBars.

from random import choice
from time import sleep

from flystim.screen import Screen
from flystim.stim_server import launch_stim_server

def main():
    manager = launch_stim_server(Screen(fullscreen=False))

    manager.load_stim(name='RotatingBars', rate=10, angle=0)

    for _ in range(10):
        rate = choice([-10, 10])
        print('chose rate: {}'.format(rate))

        manager.update_stim(rate=rate)
        manager.start_stim()
        print('started')
        sleep(1)
        manager.pause_stim()
        print('paused')
        sleep(1)

if __name__ == '__main__':
    main()
