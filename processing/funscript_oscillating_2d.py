import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def convert_funscript_oscillating(funscript, speed_funscript=None, points_per_second=25, algorithm="top-left-right", min_distance_from_center=0.1, speed_threshold_percent=50):
    """
    Convert a 1D funscript into 2D (alpha/beta) using oscillating algorithms.

    Args:
        funscript: Input Funscript object
        speed_funscript: Speed funscript for radius scaling (optional)
        points_per_second: Number of interpolated points per second
        algorithm: Oscillating algorithm - "top-left-right", "top-right-left"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_threshold_percent: Speed percentile threshold (0-100) for maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    at = funscript.x  # Time in seconds
    pos = funscript.y  # Position 0.0-1.0

    t_out = []
    x_out = []  # Alpha (x-axis)
    y_out = []  # Beta (y-axis)

    for i in range(len(pos) - 1):
        start_t, end_t = at[i:i+2]
        start_p, end_p = pos[i:i+2]

        # Calculate number of points for this segment
        n = int(np.clip(float((end_t - start_t) * points_per_second), 1, None))

        # Get speed value from speed funscript at segment start time
        if speed_funscript is not None:
            # Find closest timestamp in speed funscript
            time_diffs = np.abs(speed_funscript.x - start_t)
            closest_idx = np.argmin(time_diffs)
            speed_value = speed_funscript.y[closest_idx] * 100  # Convert 0-1 to 0-100
        else:
            # Fallback: calculate speed from position change
            segment_duration = end_t - start_t
            position_change = abs(end_p - start_p)
            current_speed = position_change / segment_duration if segment_duration > 0 else 0
            # Map to 0-100 range (assume max speed of 2.0 pos/sec)
            speed_value = min(current_speed / 2.0, 1.0) * 100

        # Map speed to radius using threshold
        if speed_value >= speed_threshold_percent:
            radius_scale = 1.0
        else:
            ratio = speed_value / speed_threshold_percent if speed_threshold_percent > 0 else 0
            radius_scale = min_distance_from_center + (1.0 - min_distance_from_center) * ratio

        # Create time array
        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)

        # Generate interpolated positions
        progress = np.linspace(0, 1, n, endpoint=False)
        funscript_positions = np.interp(progress, [0, 1], [start_p, end_p])

        # Scale radius based on speed: from min_distance to max (0.5 = edge of circle)
        target_radius = 0.5 * radius_scale  # Scale within 0 to 0.5 (circle boundary)

        if algorithm == "top-left-right":
            # Map funscript position to angle: 1.0 → 0°, 0.0 → 270°
            # This creates motion from top, through left, to bottom
            theta = (1.0 - funscript_positions) * (3*np.pi/2)
            x = 0.5 + target_radius * np.cos(theta)
            y = 0.5 + target_radius * np.sin(theta)

        elif algorithm == "top-right-left":
            # Map funscript position to angle: 1.0 → 0°, 0.0 → 90°
            # This creates motion from top, through right, to bottom
            theta = (1.0 - funscript_positions) * (np.pi/2)
            x = 0.5 + target_radius * np.cos(theta)
            y = 0.5 + target_radius * np.sin(theta)

        # Append to output arrays
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    # Create alpha and beta funscripts
    alpha_funscript = Funscript(t_out, x_out)
    beta_funscript = Funscript(t_out, y_out)

    return alpha_funscript, beta_funscript


def generate_alpha_beta_oscillating(main_funscript, speed_funscript=None, points_per_second=25, algorithm="top-left-right", min_distance_from_center=0.1, speed_threshold_percent=50):
    """
    Generate alpha and beta funscripts from a main 1D funscript using oscillating algorithms.

    Args:
        main_funscript: Input Funscript object
        speed_funscript: Speed funscript for radius scaling (optional)
        points_per_second: Number of interpolated points per second
        algorithm: Oscillating algorithm - "top-left-right", "top-right-left"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_threshold_percent: Speed percentile threshold (0-100) for maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    return convert_funscript_oscillating(main_funscript, speed_funscript, points_per_second, algorithm, min_distance_from_center, speed_threshold_percent)