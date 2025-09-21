import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def invert_funscript(funscript):
    """Invert all position values (pos = 1.0 - pos). Funscript stores values in 0-1 range internally."""
    new_x = funscript.x.copy()
    new_y = 1.0 - funscript.y
    return Funscript(new_x, new_y)


def map_funscript(funscript, new_min, new_max):
    """Linearly map funscript values to a new range."""
    # Find current min and max
    current_min = np.min(funscript.y)
    current_max = np.max(funscript.y)

    # Avoid division by zero
    if current_max == current_min:
        # All values are the same, map to middle of new range
        new_y = np.full_like(funscript.y, (new_min + new_max) / 2)
    else:
        # Apply linear mapping formula
        new_y = (funscript.y - current_min) / (current_max - current_min) * (new_max - new_min) + new_min

    return Funscript(funscript.x.copy(), new_y)


def limit_funscript(funscript, new_min, new_max):
    """Limit funscript values to a specified range."""
    new_y = np.clip(funscript.y, new_min, new_max)
    return Funscript(funscript.x.copy(), new_y)


def normalize_funscript(funscript):
    """Normalize funscript by shifting all values to maximize range usage."""
    max_pos = np.max(funscript.y)
    shift = 1.0 - max_pos

    # Shift all positions up, cap at 1.0
    new_y = np.minimum(1.0, funscript.y + shift)
    return Funscript(funscript.x.copy(), new_y)


def mirror_up_funscript(funscript, threshold):
    """Mirror values below threshold above it."""
    new_y = np.where(funscript.y < threshold, 2 * threshold - funscript.y, funscript.y)
    return Funscript(funscript.x.copy(), new_y)