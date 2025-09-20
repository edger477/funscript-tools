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
    x = []
    y = []
    max_speed = 0
    time_window = window_seconds
    shift = int(time_window * 5)  # 5 points per second after interpolation

    # Start with zero speed
    x.append(funscript.x[0])
    y.append(0)

    for i in range(1 + shift, len(funscript.x)):
        current_time = funscript.x[i]

        # Initialize variables for rolling sum
        total_speed = 0
        count = 0

        # Look back at all points within the last n seconds
        for j in range(i, -1, -1):
            if current_time - funscript.x[j] > time_window:
                break  # Stop if we're outside the n-second window

            if j == 0:
                break

            time_diff = funscript.x[j] - funscript.x[j-1]  # Time difference in seconds
            pos_diff = abs(funscript.y[j] - funscript.y[j-1])  # Absolute position change

            # Avoid division by zero if time_diff is zero
            if time_diff != 0:
                speed = pos_diff / time_diff  # Speed (change per second)
                total_speed += speed
                count += 1

        # Calculate the average speed over the rolling window
        avg_speed = (total_speed / count) if count > 0 else 0

        if avg_speed > max_speed:
            max_speed = avg_speed

        # Append with shift compensation
        x.append(funscript.x[i-shift])
        y.append(avg_speed)

    # Add final point with zero speed
    x.append(funscript.x[len(funscript.x)-1])
    y.append(0)

    # Normalize to 0-1 range
    if max_speed > 0:
        factor = 1 / max_speed
        for i in range(len(y)):
            y[i] = y[i] * factor

    return Funscript(x, y)


def convert_to_speed(funscript, window_seconds=5, interpolation_interval=0.1):
    """Convert a funscript to speed representation."""
    # Make a copy to avoid modifying the original
    fs_copy = funscript.copy()

    # Add interpolated points
    fs_copy = add_interpolated_points(fs_copy, interpolation_interval)

    # Calculate windowed speed
    speed_funscript = calculate_speed_windowed(fs_copy, window_seconds)

    return speed_funscript