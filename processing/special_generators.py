import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def make_volume_ramp(input_funscript, ramp_percent_per_hour=15):
    """
    Create a volume ramp with 4 key points based on input funscript timing.
    Pattern: Start (0) → Rise (calculated) → Peak (1.0) → End (0)

    Args:
        input_funscript: Input funscript for timing reference
        ramp_percent_per_hour: Volume ramp rate percentage per hour (0-40)
    """
    if len(input_funscript.x) < 4:
        raise ValueError("Input funscript must have at least 4 actions to create volume ramp.")

    # Convert ramp percentage per hour to per second
    ramp_per_second = ramp_percent_per_hour / 3600.0

    # Set timing: Start, 10 seconds, second-to-last, and last
    start_time = input_funscript.x[0]
    second_time = start_time + 10.0  # Fixed at 10 seconds from start
    peak_time = input_funscript.x[-2]  # Second-to-last point (where value reaches 1.0)
    end_time = input_funscript.x[-1]   # Last point

    # Calculate duration from second point to peak
    duration_seconds = peak_time - second_time

    # Calculate ramp value at second point
    # Formula: 1 - (duration in seconds * ramp per second)
    ramp_value = 1.0 - (duration_seconds * ramp_per_second)

    # Clamp the ramp value between 0.0 and 1.0
    ramp_value = max(0.0, min(1.0, ramp_value))

    # Set timing and positions
    x = [start_time, second_time, peak_time, end_time]
    y = [0.0, ramp_value, 1.0, 0.0]

    return Funscript(x, y)