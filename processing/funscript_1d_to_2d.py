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

    if len(at) < 2:
        return Funscript(np.array([]), np.array([])), Funscript(np.array([]), np.array([]))

    # Use the speed funscript's own timestamps as the output grid when available.
    # This guarantees perfect alignment with the speed grid in combine_funscripts (union1d
    # adds no new points), regardless of funscript start time or interpolation_interval.
    # Falls back to a uniform arange when no speed funscript is provided.
    if speed_funscript is not None:
        mask = (speed_funscript.x >= at[0] - 1e-9) & (speed_funscript.x <= at[-1] + 1e-9)
        t_global = speed_funscript.x[mask]
    else:
        step = 1.0 / points_per_second
        t_global = np.arange(at[0], at[-1], step)

    if len(t_global) == 0:
        return Funscript(at.copy(), pos.copy()), Funscript(at.copy(), pos.copy())

    # For each global time, find which segment it belongs to
    seg_idx = np.searchsorted(at, t_global, side='right') - 1
    seg_idx = np.clip(seg_idx, 0, len(at) - 2)

    # Segment boundaries
    seg_start_t = at[seg_idx]
    seg_end_t = at[seg_idx + 1]
    seg_start_p = pos[seg_idx]
    seg_end_p = pos[seg_idx + 1]

    # Progress within each segment [0.0, 1.0]
    seg_dur = seg_end_t - seg_start_t
    progress = np.where(seg_dur > 0, (t_global - seg_start_t) / seg_dur, 0.0)
    progress = np.clip(progress, 0.0, 1.0)

    # Linearly interpolated funscript position at each global time
    current_positions = seg_start_p + progress * (seg_end_p - seg_start_p)

    # Compute per-segment speed → radius mapping
    n_segs = len(at) - 1
    if speed_funscript is not None:
        seg_start_speeds = np.interp(at[:n_segs], speed_funscript.x, speed_funscript.y) * 100
    else:
        seg_durations_all = at[1:] - at[:n_segs]
        pos_changes_all = np.abs(pos[1:] - pos[:n_segs])
        seg_start_speeds = np.where(
            seg_durations_all > 0,
            np.minimum(pos_changes_all / seg_durations_all / 2.0, 1.0) * 100,
            0.0
        )

    speed_thresh = max(float(speed_threshold_percent), 1e-10)
    radius_scale_per_seg = np.where(
        seg_start_speeds >= speed_threshold_percent,
        1.0,
        min_distance_from_center + (1.0 - min_distance_from_center) * seg_start_speeds / speed_thresh
    )
    # Map per-segment radius to each global time point
    target_radius = 0.5 * radius_scale_per_seg[seg_idx]

    # Convert funscript position to angle (0-180 degrees for semicircle)
    # Position 1.0 -> 0°, Position 0.0 -> 180°
    position_angles = (1.0 - current_positions) * np.pi

    # Generate alpha (x-axis) and beta (y-axis) from global center
    x_out = 0.5 + target_radius * np.cos(position_angles)
    y_out = 0.5 + target_radius * np.sin(position_angles)

    return Funscript(t_global, x_out), Funscript(t_global, y_out)


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