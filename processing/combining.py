import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def combine_funscripts(left_funscript, right_funscript, ratio, rest_level=0.5):
    """
    Combine two funscripts using weighted average.

    Args:
        left_funscript: First funscript
        right_funscript: Second funscript
        ratio: Combining ratio (2 for 50/50, 4 for 75/25, etc)
        rest_level: Multiplier when either input is 0
    """
    # Get union of all timestamps
    x = np.union1d(left_funscript.x, right_funscript.x)

    # Interpolate both signals to common timestamps
    y_left = np.interp(x, left_funscript.x, left_funscript.y)
    y_right = np.interp(x, right_funscript.x, right_funscript.y)

    # Calculate the weighted average
    y = (y_left * (ratio - 1) + y_right) / ratio

    # Apply rest_level when either input is 0
    y = np.where((y_left == 0) | (y_right == 0), y * rest_level, y)

    return Funscript(x, y)


def multiply_funscripts(left_funscript, right_funscript):
    """Multiply two funscripts point-wise."""
    x = np.union1d(left_funscript.x, right_funscript.x)
    y = np.interp(x, left_funscript.x, left_funscript.y) * np.interp(x, right_funscript.x, right_funscript.y)
    return Funscript(x, y)