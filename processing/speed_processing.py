import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def add_interpolated_points(funscript_data, interval=0.1):
    """
    Interpolate funscript so that there's one value every interval seconds.
    """
    if len(funscript_data.x) < 2:
        raise ValueError("Need at least two points to interpolate.")

    x = np.array(funscript_data.x)
    y = np.array(funscript_data.y)

    start = int(x[0])
    end = int(x[-1])

    # Generate timestamps every interval seconds
    target_x = np.arange(start, end + 1, interval)

    # Interpolate positions at those timestamps
    interp_y = np.interp(target_x, x, y)

    # Update the funscript data
    funscript_data.x = target_x.tolist()
    funscript_data.y = interp_y.tolist()

    return funscript_data


def calculate_speed_windowed(funscript, window_seconds=5):
    """Calculate the rolling average speed of change over the last n seconds."""
    x = np.asarray(funscript.x, dtype=np.float64)
    y = np.asarray(funscript.y, dtype=np.float64)
    n = len(x)

    shift = int(window_seconds * 5)  # 5 points per second after interpolation

    # Uniform spacing is guaranteed by add_interpolated_points
    interval = x[1] - x[0]
    window_size = int(round(window_seconds / interval))

    # Instantaneous speed per segment: |dy|/dt (vectorized, O(n))
    point_speeds = np.abs(np.diff(y)) / interval  # shape: (n-1,)

    # Cumulative sum enables O(1) rolling window queries
    cs = np.empty(n, dtype=np.float64)
    cs[0] = 0.0
    np.cumsum(point_speeds, out=cs[1:])

    # Compute rolling mean for all outer-loop indices at once
    valid_i = np.arange(1 + shift, n)
    start_idx = np.maximum(valid_i - window_size, 0)
    counts = valid_i - start_idx
    avg_speeds = (cs[valid_i] - cs[start_idx]) / counts

    # Normalize to 0-1 range
    max_speed = avg_speeds.max() if len(avg_speeds) > 0 else 0.0
    if max_speed > 0:
        avg_speeds /= max_speed

    # Build output: leading zero, rolling averages (time-shifted by shift), trailing zero
    out_x = np.empty(len(valid_i) + 2, dtype=np.float64)
    out_y = np.empty(len(valid_i) + 2, dtype=np.float64)
    out_x[0] = x[0]
    out_y[0] = 0.0
    out_x[1:-1] = x[valid_i - shift]
    out_y[1:-1] = avg_speeds
    out_x[-1] = x[-1]
    out_y[-1] = 0.0

    return Funscript(out_x, out_y)


def convert_to_speed(funscript, window_seconds=5, interpolation_interval=0.1):
    """Convert a funscript to speed representation."""
    # Make a copy to avoid modifying the original
    fs_copy = funscript.copy()

    # Add interpolated points
    fs_copy = add_interpolated_points(fs_copy, interpolation_interval)

    # Calculate windowed speed
    speed_funscript = calculate_speed_windowed(fs_copy, window_seconds)

    return speed_funscript