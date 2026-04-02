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
    funscript_positions = seg_start_p + progress * (seg_end_p - seg_start_p)

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
    target_radius = 0.5 * radius_scale_per_seg[seg_idx]

    if algorithm == "top-left-right":
        # Map funscript position to angle: 1.0 → 0°, 0.0 → 270°
        theta = (1.0 - funscript_positions) * (3 * np.pi / 2)
    else:  # top-right-left
        # Map funscript position to angle: 1.0 → 0°, 0.0 → 90°
        theta = (1.0 - funscript_positions) * (np.pi / 2)

    x_out = 0.5 + target_radius * np.cos(theta)
    y_out = 0.5 + target_radius * np.sin(theta)

    return Funscript(t_global, x_out), Funscript(t_global, y_out)


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