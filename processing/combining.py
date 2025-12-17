import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


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
        # Find transitions from rest to active
        # Prepend True to detect rest at start, append False to detect rest at end
        is_rest_padded = np.concatenate(([True], is_rest, [False]))
        rest_to_active = (~is_rest_padded[:-1]) & (is_rest_padded[1:])

        # For each point, calculate time since last rest->active transition
        time_since_rest_end = np.full_like(x, np.inf)

        for i in range(len(x)):
            if not is_rest[i]:
                # Find the most recent rest->active transition at or before this point
                # Look backwards to find where rest ended
                for j in range(i, -1, -1):
                    if is_rest[j]:
                        # Found the rest period, transition happens at j+1
                        if j + 1 <= i:
                            time_since_rest_end[i] = x[i] - x[j + 1]
                        break
                else:
                    # No rest period found before this point (active from start)
                    time_since_rest_end[i] = np.inf

        # Calculate ramp multiplier (goes from rest_level to 1.0 over ramp_up_duration)
        # ramp_progress: 0.0 at start of ramp, 1.0 after ramp_up_duration
        ramp_progress = np.clip(time_since_rest_end / ramp_up_duration, 0.0, 1.0)

        # Interpolate from rest_level to 1.0
        ramp_multiplier = rest_level + (1.0 - rest_level) * ramp_progress

        # Apply ramp multiplier only to active (non-rest) points
        y_final = np.where(is_rest, y_with_rest, y * ramp_multiplier)
    else:
        # No ramp-up, use immediate rest_level application
        y_final = y_with_rest

    return Funscript(x, y_final)


def multiply_funscripts(left_funscript, right_funscript):
    """Multiply two funscripts point-wise."""
    x = np.union1d(left_funscript.x, right_funscript.x)
    y = np.interp(x, left_funscript.x, left_funscript.y) * np.interp(x, right_funscript.x, right_funscript.y)
    return Funscript(x, y)