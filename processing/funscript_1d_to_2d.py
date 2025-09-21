import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def convert_funscript_radial(funscript, points_per_second=25, min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    """
    Convert a 1D funscript into 2D (alpha/beta) using circular conversion.

    Args:
        funscript: Input Funscript object
        points_per_second: Number of interpolated points per second
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_at_edge_hz: Speed in Hz at which dot reaches maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    at = funscript.x  # Time in seconds
    pos = funscript.y  # Position 0.0-1.0

    t_out = []
    x_out = []  # Alpha (x-axis)
    y_out = []  # Beta (y-axis)

    # Convert speed_at_edge_hz to time needed to go from 0 to 1
    # If speed_at_edge_hz = 2Hz, then full range (0 to 1) takes 0.5 seconds
    max_speed_threshold = abs(1.0) / (1.0 / speed_at_edge_hz)  # Speed for full range in 1/Hz seconds

    for i in range(len(pos) - 1):
        start_t, end_t = at[i:i+2]
        start_p, end_p = pos[i:i+2]

        # Calculate number of points for this segment
        n = int(np.clip(float((end_t - start_t) * points_per_second), 1, None))

        # Calculate speed for this segment (position change per second)
        segment_duration = end_t - start_t
        position_change = abs(end_p - start_p)
        current_speed = position_change / segment_duration if segment_duration > 0 else 0

        # Map speed to radius (min_distance_from_center to 1.0)
        speed_ratio = min(current_speed / max_speed_threshold, 1.0)  # Clamp to 1.0
        radius_scale = min_distance_from_center + (1.0 - min_distance_from_center) * speed_ratio

        # Create time and angle arrays
        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)
        theta = np.linspace(0, np.pi, n, endpoint=False)

        # Calculate radial conversion parameters
        center = (end_p + start_p) / 2
        r = (start_p - end_p) / 2

        # Apply speed-based radius scaling
        r = r * radius_scale

        # Generate alpha (x-axis) and beta (y-axis) coordinates
        x = center + r * np.cos(theta)
        y = r * np.sin(theta) + 0.5

        # Append to output arrays
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    # Create alpha and beta funscripts
    alpha_funscript = Funscript(t_out, x_out)
    beta_funscript = Funscript(t_out, y_out)

    return alpha_funscript, beta_funscript


def generate_alpha_beta_from_main(main_funscript, points_per_second=25, algorithm="circular", min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    """
    Generate alpha and beta funscripts from a main 1D funscript.

    Args:
        main_funscript: Input Funscript object
        points_per_second: Number of interpolated points per second
        algorithm: Conversion algorithm - "circular", "top-left-right", "top-right-left"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_at_edge_hz: Speed in Hz at which dot reaches maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    if algorithm == "circular":
        return convert_funscript_radial(main_funscript, points_per_second, min_distance_from_center, speed_at_edge_hz)
    elif algorithm in ["top-left-right", "top-right-left"]:
        # Import the oscillating module
        from .funscript_oscillating_2d import generate_alpha_beta_oscillating
        return generate_alpha_beta_oscillating(main_funscript, points_per_second, algorithm, min_distance_from_center, speed_at_edge_hz)
    else:
        # Default to circular if unknown algorithm
        return convert_funscript_radial(main_funscript, points_per_second, min_distance_from_center, speed_at_edge_hz)