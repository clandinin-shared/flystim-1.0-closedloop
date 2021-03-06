# flystim

[![Build Status](https://travis-ci.com/ClandininLab/flystim.svg?branch=master)](https://travis-ci.com/ClandininLab/flystim)

**flystim** is a software package for generating visual stimuli for fruit fly experiments.  The stimuli are perspective-corrected and can be displayed across multiple screens.  Sample code, illustrating various use cases, is included in the **examples** directory.

# Prerequisites

**flystim** only supports Python3, so in the commands below, the **pip** and **python** commands should refer to a Python3 install.  You can either install Python3 directly or through a package manager like Conda.

On Linux, you'll also need to install a few packages via **apt-get**:
```shell
> sudo apt-get install build-essential libusb-1.0.0-dev libudev-dev
```

# Installation

1. Open a terminal, and note the current directory, since the **pip** commands below will clone some code from GitHub and place it in a subdirectory called **src**.  If you prefer to place the cloned code in a different directory, you can specify that by providing the **--src** flag to **pip**.
2. Clone and install [flyrpc](https://github.com/ClandininLab/flyrpc) if you haven't already:
```shell
> git clone https://github.com/ClandininLab/flyrpc.git
> cd flyrpc
> pip install -e .
> cd ..
```
3. Clone and install [flystim](https://github.com/ClandininLab/flystim):
```shell
> git clone https://github.com/ClandininLab/flystim.git
> cd flystim
> pip install -e .
> cd ..
```

If you get a permissions error when running the **pip** command, you can try adding the **--user** flag.  This will cause **pip** to install packages in your user directory rather than to a system-wide location.

# Running the Example Code

In a terminal tab, navigate to the examples directory and run one of the sample programs, such as **show_all.py**.

```shell
> cd flystim/examples
> python show_all.py
```

Each example can be exited at any time by pressing Ctrl+C.
