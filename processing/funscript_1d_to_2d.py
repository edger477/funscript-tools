import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def convert_funscript_radial(funscript, points_per_second=25):
    """
    Convert a 1D funscript into 2D (alpha/beta) using radial conversion.

    Args:
        funscript: Input Funscript object
        points_per_second: Number of interpolated points per second

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

        # Create time and angle arrays
        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)
        theta = np.linspace(0, np.pi, n, endpoint=False)

        # Calculate radial conversion parameters
        center = (end_p + start_p) / 2
        r = (start_p - end_p) / 2

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


def generate_alpha_beta_from_main(main_funscript, points_per_second=25):
    """
    Generate alpha and beta funscripts from a main 1D funscript.

    Args:
        main_funscript: Input Funscript object
        points_per_second: Number of interpolated points per second

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    return convert_funscript_radial(main_funscript, points_per_second)