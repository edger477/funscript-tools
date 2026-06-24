import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from processing.basic_transforms import map_funscript


def combine_funscripts(left_funscript, right_funscript, ratio, rest_level=0.5, ramp_up_duration=0.0):
    """
    Combine two funscripts using weighted average.

    Args:
        left_funscript: First funscript
        right_funscript: Second funscript
        ratio: Combining ratio (2 for 50/50, 4 for 75/25, etc)
        rest_level: Multiplier when either input is 0
        ramp_up_duration: Duration in seconds to ramp from rest_level back to normal after rest (0 = instant)
    """
    # Get union of all timestamps
    x = np.union1d(left_funscript.x, right_funscript.x)

    # Interpolate both signals to common timestamps
    y_left = np.interp(x, left_funscript.x, left_funscript.y)
    y_right = np.interp(x, right_funscript.x, right_funscript.y)

    # Calculate the weighted average
    y = (y_left * (ratio - 1) + y_right) / ratio

    # Determine which points are at rest (either input is 0)
    is_rest = (y_left == 0) | (y_right == 0)

    # Apply rest_level immediately when at rest
    y_with_rest = np.where(is_rest, y * rest_level, y)

    # Apply ramp-up after rest periods if duration > 0
    if ramp_up_duration > 0:
        half_duration = ramp_up_duration / 2.0

        # Find rest->active transition indices (vectorized)
        transition_indices = np.where(is_rest[:-1] & ~is_rest[1:])[0] + 1
        transition_arr = x[transition_indices]  # sorted, since x is sorted

        time_relative_to_transition = np.full(len(x), np.inf)

        if len(transition_arr) > 0:
            # For each point x[i], find the first transition t where t ∈ [x[i]-hd, x[i]+hd].
            # Since transition_arr is sorted, use searchsorted for O(n log M) instead of O(n×M).
            left_idx = np.searchsorted(transition_arr, x - half_duration, side='left')
            valid = left_idx < len(transition_arr)
            candidate_t = transition_arr[np.minimum(left_idx, len(transition_arr) - 1)]
            in_window = valid & (candidate_t <= x + half_duration)
            time_relative_to_transition = np.where(in_window, x - candidate_t, np.inf)

        ramp_progress = np.clip(
            (time_relative_to_transition + half_duration) / ramp_up_duration, 0.0, 1.0
        )
        ramp_multiplier = rest_level + (1.0 - rest_level) * ramp_progress
        in_ramp_window = np.isfinite(time_relative_to_transition)
        y_final = np.where(in_ramp_window, y * ramp_multiplier, y_with_rest)
    else:
        # No ramp-up, use immediate rest_level application
        y_final = y_with_rest

    return Funscript(x, y_final)



def blend_supplied_volume(generated, external, ratio, output_min=0.0, output_max=1.0):
    """Combine 2: blend generated volume (from ramp+speed combine) with external volume."""
    blended = combine_funscripts(generated, external, ratio, rest_level=1.0, ramp_up_duration=0.0)
    if output_min != 0.0 or output_max != 1.0:
        blended = map_funscript(blended, output_min, output_max)
    return blended


def multiply_funscripts(left_funscript, right_funscript):
    """Multiply two funscripts point-wise."""
    x = np.union1d(left_funscript.x, right_funscript.x)
    y = np.interp(x, left_funscript.x, left_funscript.y) * np.interp(x, right_funscript.x, right_funscript.y)
    return Funscript(x, y)