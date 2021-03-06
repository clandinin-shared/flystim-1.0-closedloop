from math import sin, cos
from numbers import Number

import numpy as np
from scipy.interpolate import interp1d

from warnings import warn

def listify(x, type_):
    if isinstance(x, (list, tuple)):
        return x

    if isinstance(x, type_):
        return [x]

    raise ValueError('Unknown input type: {}'.format(type(x)))

def normalize(vec):
    return vec / np.linalg.norm(vec)

# rotation matrix reference:
# https://en.wikipedia.org/wiki/Rotation_matrix

def rotx(pts, th):
    return rotx_mat(th).dot(pts)

def rotx_mat(th):
    return np.array([[1,       0,         0],
                     [0, +cos(th), -sin(th)],
                     [0, +sin(th), +cos(th)]], dtype=float)

def roty(pts, th):
    return roty_mat(th).dot(pts)

def roty_mat(th):
    return np.array([[+cos(th), 0, +sin(th)],
                     [0,        1,        0],
                     [-sin(th), 0, +cos(th)]], dtype=float)

def rotz(pts, th):
    return rotz_mat(th).dot(pts)

def rotz_mat(th):
    return np.array([[+cos(th), -sin(th), 0],
                     [+sin(th), +cos(th), 0],
                     [       0,        0, 1]], dtype=float)

def scale(pts, amt):
    return np.multiply(amt, pts)

def translate(pts, amt):
    # convert point(s) and translate amount to numpy arrays
    pts = np.array(pts, dtype=float)
    amt = np.array(amt, dtype=float)

    # add offset in a manner that depends on whether the input is 1D or 2D
    if len(pts.shape) == 1:
        return pts + amt
    elif len(pts.shape) == 2:
        return pts + amt[:, np.newaxis]

def get_rgba(val, def_alpha=1):
    # interpret string as RGB
    if isinstance(val, str):
        if val.lower() == 'red':
            val = (1, 0, 0)
        elif val.lower() == 'green':
            val = (0, 1, 0)
        elif val.lower() == 'blue':
            val = (0, 0, 1)
        elif val.lower() == 'yellow':
            val = (1, 1, 0)
        elif val.lower() == 'magenta':
            val = (1, 0, 1)
        elif val.lower() == 'cyan':
            val = (0, 1, 1)
        elif val.lower() == 'white':
            val = (1, 1, 1)
        elif val.lower() == 'black':
            val = (0, 0, 0)
        else:
            raise ValueError(f'Unknown color: {val}')

    # if a single number is given treat as monochrome
    if isinstance(val, Number):
        return (val, val, val, def_alpha)

    # otherwise if three numbers are given add the default alpha
    if len(val) == 3:
        return (val[0], val[1], val[2], def_alpha)
    elif len(val) == 4:
        return val
    else:
        raise ValueError(f'Cannot use value with length {len(val)}.')


def latency_report(flystim_timestamps, flystim_sync, fictrac_timestamps, fictrac_sync,
                   window_size=10, n_windows=32):
    """ Latency analysis report


    Args:
      flystim_timestamps: list of timestamps when sync square was updated - (n_fs,)
        units: seconds
      flystim_sync: list of sync square states, as recorded by flystim - (n_fs,)
      fictrac_timestamps: list of timestamps when fictrac captured a frame - (n_ft,)
        units: seconds
      fictrac_sync: list of sync square states, as captured by fictrac - (n_ft,)
      window_size: size of window to use for local latency analysis
      n_windows: number of windows to compute lag for

    """
    assert len(flystim_timestamps) == len(flystim_sync)
    assert len(fictrac_timestamps) == len(fictrac_sync)

    flystim_timestamps = np.asarray(flystim_timestamps)
    flystim_sync = np.asarray(flystim_sync)
    fictrac_timestamps = np.asarray(fictrac_timestamps)
    fictrac_sync = np.asarray(fictrac_sync)

    # TODO: why are non-zero values recorded
    # truncate non-zero values
    fs_mask = flystim_timestamps.astype(bool)
    flystim_timestamps = flystim_timestamps[fs_mask]
    flystim_sync = flystim_sync[fs_mask]

    ft_mask = fictrac_timestamps.astype(bool)
    fictrac_timestamps = fictrac_timestamps[ft_mask]
    fictrac_sync = fictrac_sync[ft_mask]

    template = "{:^20} | {:^16.4f} | {:^16.4f}"
    table_width = 60

    print("{:^20} | {:^16} | {:^16}".format("statistic", "flystim", "fictrac"))
    print("=" * table_width)

    print(
        template.format(
            "mean fps",
            1 / np.mean(np.diff(flystim_timestamps)),
            1 / np.mean(np.diff(fictrac_timestamps))
        )
    )
    print('-' * table_width)

    print(
        template.format(
            "mean frame length",
            np.mean(np.diff(flystim_timestamps)),
            np.mean(np.diff(fictrac_timestamps))
        )
    )
    print('-' * table_width)

    print(
        template.format(
            "std frame length",
            np.std(np.diff(flystim_timestamps)),
            np.std(np.diff(fictrac_timestamps))
        )
    )
    print('-' * table_width)

    print(
        template.format(
            "min frame length",
            np.min(np.diff(flystim_timestamps)),
            np.min(np.diff(fictrac_timestamps))
        )
    )
    print('-' * table_width)

    print(
        template.format(
            "max frame length",
            np.max(np.diff(flystim_timestamps)),
            np.max(np.diff(fictrac_timestamps))
        )
    )
    print('-' * table_width)

    # resample both traces to fictrac fps
    flystim_interp = interp1d(flystim_timestamps, flystim_sync)
    fictrac_interp = interp1d(fictrac_timestamps, fictrac_sync)

    resample_frame_len = np.mean(np.diff(fictrac_timestamps))

    time_bounds = (
        max(min(flystim_timestamps), min(fictrac_timestamps)),
        min(max(flystim_timestamps), max(fictrac_timestamps)),
    )
    trial_duration = time_bounds[1] - time_bounds[0]

    num_samples = 1 + int((time_bounds[1] - time_bounds[0]) / resample_frame_len)
    time_grid = np.linspace(*time_bounds, num_samples, endpoint=True)

    resampled_fs_sync = flystim_interp(time_grid)
    resampled_ft_sync = fictrac_interp(time_grid)

    global_lag = calculate_lag(resampled_fs_sync, resampled_ft_sync)

    print("Globally optimal lag: {:.1f}ms".format(global_lag * resample_frame_len * 1000))

    local_lags = []

    if window_size >= trial_duration:
        warn("window_size is larger than trial duration! try a smaller window_size")

    for start_time in np.linspace(time_bounds[0], time_bounds[1] - window_size, n_windows):
        time_grid = np.linspace(
            start_time,
            start_time + window_size,
            1  + int(window_size / resample_frame_len),
            endpoint=True
        )

        local_lags.append(
            calculate_lag(
                flystim_interp(time_grid),
                fictrac_interp(time_grid)
            ) * resample_frame_len * 1000
        )


    print("Local lag ({} {}s windows): {:.1f}ms mean, {:.1f}ms std".format(
        n_windows, window_size, np.mean(local_lags), np.std(local_lags)
    ))

    print("Total length of recording: {:1f} s".format(time_bounds[1] - time_bounds[0]))

# TODO: test!
# TODO: mean zero sequences?
def calculate_lag(ground_truth, lagged):
    """ Calculate delay between sequences that optimally aligns them

    Args:
      ground_truth: ground truth sequence to align against
      lagged: delayed ground truth sequence, perhaps with some added noise

    Returns
      lag: in units of indices!! - int
    """
    cross_corr = np.correlate(lagged, ground_truth, mode='full')
    return np.argmax(cross_corr) - len(ground_truth) + 1
