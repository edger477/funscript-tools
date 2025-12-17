import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def convert_funscript_radial(funscript, speed_funscript=None, points_per_second=25, min_distance_from_center=0.1, speed_threshold_percent=50):
    """
    Convert a 1D funscript into 2D (alpha/beta) using circular conversion.

    Args:
        funscript: Input Funscript object
        speed_funscript: Speed funscript for radius scaling (optional, will calculate if None)
        points_per_second: Number of interpolated points per second
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

        # Create time and angle arrays
        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)
        theta = np.linspace(0, np.pi, n, endpoint=False)

        # Calculate radial conversion parameters
        center = (end_p + start_p) / 2
        stroke_amplitude = abs(start_p - end_p) / 2

        # Calculate base radius from global center (0.5, 0.5)
        # The stroke's center position determines the base radius
        base_radius = abs(center - 0.5)

        # Scale radius based on speed: from min_distance to max (0.5 = edge of circle)
        target_radius = 0.5 * radius_scale  # Scale within 0 to 0.5 (circle boundary)

        # Generate positions on a circle from global center
        # Map funscript position (start_p to end_p) to angle
        progress = np.linspace(0, 1, n, endpoint=False)
        current_positions = np.interp(progress, [0, 1], [start_p, end_p])

        # Convert funscript position to angle (0-180 degrees for semicircle)
        # Position 1.0 -> 0°, Position 0.0 -> 180°
        position_angles = (1.0 - current_positions) * np.pi

        # Generate alpha (x-axis) and beta (y-axis) from global center
        x = 0.5 + target_radius * np.cos(position_angles)
        y = 0.5 + target_radius * np.sin(position_angles)

        # Append to output arrays
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    # Create alpha and beta funscripts
    alpha_funscript = Funscript(t_out, x_out)
    beta_funscript = Funscript(t_out, y_out)

    return alpha_funscript, beta_funscript


def convert_funscript_restim_original(funscript, random_direction_change_probability=0.1):
    """
    Convert a 1D funscript into 2D (alpha/beta) using the original restim algorithm.

    This is the original algorithm from diglet48's restim repository.
    It uses stroke-relative circular motion with random direction changes.

    Args:
        funscript: Input Funscript object
        random_direction_change_probability: Probability of direction flip (0.0-1.0)

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    at = funscript.x  # Time in seconds
    pos = funscript.y  # Position 0.0-1.0

    dir = 1  # Direction multiplier for y-axis

    t_out = []
    x_out = []  # Alpha (x-axis)
    y_out = []  # Beta (y-axis)

    for i in range(len(pos) - 1):
        start_t, end_t = at[i:i + 2]
        start_p, end_p = pos[i:i + 2]

        duration = end_t - start_t

        # Adaptive point density based on duration
        if start_p == end_p:
            n = 1
        else:
            if duration <= 0.100:
                n = 2
            elif duration <= 0.200:
                n = 3
            elif duration <= 0.300:
                n = 4
            elif duration <= 0.400:
                n = 5
            else:
                n = 6

        # Create time and angle arrays
        t = np.linspace(0.0, duration, n, endpoint=False)
        theta = np.linspace(0, np.pi, n, endpoint=False)

        # Calculate stroke-relative center and radius
        center = (end_p + start_p) / 2
        r = (start_p - end_p) / 2

        # Random direction change for alternating motion
        if np.random.random() < random_direction_change_probability:
            dir = dir * -1

        # Generate circular motion relative to stroke center
        x = center + r * np.cos(theta)
        y = r * dir * np.sin(theta) + 0.5

        # Append to output arrays
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    # Create alpha and beta funscripts
    alpha_funscript = Funscript(t_out, x_out)
    beta_funscript = Funscript(t_out, y_out)

    return alpha_funscript, beta_funscript


def generate_alpha_beta_from_main(main_funscript, speed_funscript=None, points_per_second=25, algorithm="circular", min_distance_from_center=0.1, speed_threshold_percent=50, direction_change_probability=0.1):
    """
    Generate alpha and beta funscripts from a main 1D funscript.

    Args:
        main_funscript: Input Funscript object
        speed_funscript: Speed funscript for radius scaling (optional)
        points_per_second: Number of interpolated points per second
        algorithm: Conversion algorithm - "circular", "top-left-right", "top-right-left", "restim-original"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_threshold_percent: Speed percentile threshold (0-100) for maximum radius
        direction_change_probability: Probability of direction flip per segment for restim-original (0.0-1.0)

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    # Import version info for metadata
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from version import __version__, __app_name__, __url__

    # Generate funscripts based on algorithm
    if algorithm == "circular":
        alpha_funscript, beta_funscript = convert_funscript_radial(main_funscript, speed_funscript, points_per_second, min_distance_from_center, speed_threshold_percent)
    elif algorithm == "top-left-right":
        # Import the oscillating module
        from .funscript_oscillating_2d import generate_alpha_beta_oscillating
        alpha_funscript, beta_funscript = generate_alpha_beta_oscillating(main_funscript, speed_funscript, points_per_second, algorithm, min_distance_from_center, speed_threshold_percent)
    elif algorithm == "top-right-left":
        # Use top-left-right algorithm and then invert beta for vertical mirror
        from .funscript_oscillating_2d import generate_alpha_beta_oscillating
        from .basic_transforms import invert_funscript

        # Generate using top-left-right algorithm
        alpha_funscript, beta_funscript = generate_alpha_beta_oscillating(
            main_funscript, speed_funscript, points_per_second, "top-left-right", min_distance_from_center, speed_threshold_percent
        )

        # Invert beta to create vertical mirror effect
        beta_inverted = invert_funscript(beta_funscript)
        alpha_funscript, beta_funscript = alpha_funscript, beta_inverted
    elif algorithm == "restim-original":
        # Use the original restim algorithm with random direction changes
        alpha_funscript, beta_funscript = convert_funscript_restim_original(main_funscript, direction_change_probability)
    else:
        # Default to circular if unknown algorithm
        alpha_funscript, beta_funscript = convert_funscript_radial(main_funscript, speed_funscript, points_per_second, min_distance_from_center, speed_threshold_percent)

    # Add metadata to generated funscripts
    algorithm_names = {
        "circular": "Circular (0°-180°)",
        "top-left-right": "Top-Left-Bottom-Right (0°-90°)",
        "top-right-left": "Top-Right-Bottom-Left (0°-270°)",
        "restim-original": "Restim Original (0°-360°)"
    }

    base_metadata = {
        "creator": __app_name__,
        "description": f"Generated by {__app_name__} v{__version__} using {algorithm_names.get(algorithm, algorithm)} motion algorithm",
        "url": __url__,
        "metadata": {
            "generator": __app_name__,
            "generator_version": __version__,
            "motion_algorithm": algorithm,
            "points_per_second": points_per_second
        }
    }

    # Add algorithm-specific metadata
    if algorithm != "restim-original":
        base_metadata["metadata"]["min_distance_from_center"] = min_distance_from_center
        base_metadata["metadata"]["speed_threshold_percent"] = speed_threshold_percent
    else:
        base_metadata["metadata"]["direction_change_probability"] = direction_change_probability

    alpha_funscript.metadata = base_metadata.copy()
    alpha_funscript.metadata["title"] = "Alpha (Horizontal) Axis"

    beta_funscript.metadata = base_metadata.copy()
    beta_funscript.metadata["title"] = "Beta (Vertical) Axis"

    return alpha_funscript, beta_funscript