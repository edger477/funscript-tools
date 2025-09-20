import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def make_volume_ramp(input_funscript):
    """
    Create a volume ramp with 4 key points based on input funscript timing.
    Pattern: Start (0) → Rise (0.8) → Peak (1.0) → End (0)
    """
    if len(input_funscript.x) < 4:
        raise ValueError("Input funscript must have at least 4 actions to create volume ramp.")

    # Keep first 2 and last 2 timestamps
    x = [input_funscript.x[0], input_funscript.x[1], input_funscript.x[-2], input_funscript.x[-1]]

    # Set ramp positions
    y = [0.0, 0.8, 1.0, 0.0]

    return Funscript(x, y)