import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def detect_local_extremes(funscript, min_segment_duration=0.25):
    """
    Detect local minima and maxima in a funscript.

    Args:
        funscript: Input Funscript object
        min_segment_duration: Minimum time between extremes in seconds (default 0.25)

    Returns:
        list: List of tuples (index, time, position, type) where type is 'min' or 'max'
    """
    positions = funscript.y
    times = funscript.x
    extremes = []

    # Find local extremes
    for i in range(1, len(positions) - 1):
        # Check if this is a local maximum
        if positions[i] > positions[i-1] and positions[i] > positions[i+1]:
            extremes.append((i, times[i], positions[i], 'max'))
        # Check if this is a local minimum
        elif positions[i] < positions[i-1] and positions[i] < positions[i+1]:
            extremes.append((i, times[i], positions[i], 'min'))

    # Filter extremes that are too close together
    if min_segment_duration > 0 and len(extremes) > 1:
        filtered_extremes = [extremes[0]]
        for extreme in extremes[1:]:
            if extreme[1] - filtered_extremes[-1][1] >= min_segment_duration:
                filtered_extremes.append(extreme)
        return filtered_extremes

    return extremes


def find_surrounding_extremes_by_time(extremes, current_time):
    """
    Find the previous and next extreme relative to a given time.

    Args:
        extremes: List of extremes from detect_local_extremes()
        current_time: Time of current point

    Returns:
        tuple: (prev_extreme, next_extreme) or (None, None) if not found
    """
    prev_extreme = None
    next_extreme = None

    for extreme in extremes:
        _, extreme_time, _, _ = extreme

        # Find previous extreme (most recent one before current time)
        if extreme_time <= current_time:
            prev_extreme = extreme

        # Find next extreme (first one after current time)
        if extreme_time > current_time:
            if next_extreme is None:
                next_extreme = extreme
            break  # We found the first one after, so we're done

    return prev_extreme, next_extreme


def calculate_delay_at_time(extremes, time, delay_factor):
    """
    Calculate the delay for a given time based on surrounding extremes.

    Args:
        extremes: List of extremes from detect_local_extremes()
        time: Time to calculate delay for
        delay_factor: Delay as fraction of segment duration (0-1)

    Returns:
        float: Delay in seconds
    """
    prev_extreme, next_extreme = find_surrounding_extremes_by_time(extremes, time)

    # Calculate delay based on segment duration
    if prev_extreme is not None and next_extreme is not None:
        # Get times from extremes
        prev_time = prev_extreme[1]
        next_time = next_extreme[1]
        segment_duration = next_time - prev_time

        # Calculate delay as percentage of segment duration
        delay = segment_duration * delay_factor
    else:
        # No surrounding extremes (edge case at start/end)
        delay = 0.0

    return delay


def generate_phase_shifted_funscript(target_funscript, source_funscript,
                                     delay_percentage=10.0, min_segment_duration=0.25):
    """
    Generate a phase-shifted version of a funscript.

    The phase shift is calculated as a percentage of the local segment duration
    (time between surrounding local extremes in the SOURCE funscript). Points maintain
    their position values from TARGET funscript but have delayed timestamps.

    Args:
        target_funscript: Funscript to apply phase shift to (alpha/beta/e1-e4)
        source_funscript: Source funscript used for extreme detection and delay calculation
        delay_percentage: Percentage of segment duration to delay (0-100)
        min_segment_duration: Minimum time between extremes in seconds

    Returns:
        Funscript: New funscript with phase-shifted times and target positions
    """
    # Detect local extremes in SOURCE funscript
    extremes = detect_local_extremes(source_funscript, min_segment_duration)

    # Convert percentage to fraction
    delay_factor = delay_percentage / 100.0

    # Generate shifted points from TARGET funscript
    shifted_times = []
    shifted_positions = []

    for time, pos in zip(target_funscript.x, target_funscript.y):
        # Calculate delay based on SOURCE funscript extremes
        delay = calculate_delay_at_time(extremes, time, delay_factor)

        # Add point with delayed time and TARGET position
        shifted_times.append(time + delay)
        shifted_positions.append(pos)

    # Create new Funscript with shifted data
    return Funscript(np.array(shifted_times), np.array(shifted_positions))


def generate_all_phase_shifted_funscripts(funscript_dict, source_funscript,
                                          delay_percentage=10.0, min_segment_duration=0.25):
    """
    Generate phase-shifted versions for all funscripts in a dictionary.

    This function creates *-2.funscript versions (alpha-2, beta-2, e1-2, etc.)
    using the source funscript for extreme detection and delay calculation.

    Args:
        funscript_dict: Dictionary of funscripts {'alpha': funscript_obj, 'beta': funscript_obj, ...}
        source_funscript: Main funscript used for extreme detection
        delay_percentage: Percentage of segment duration to delay (0-100)
        min_segment_duration: Minimum time between extremes in seconds

    Returns:
        dict: Dictionary of phase-shifted funscripts with keys like 'alpha-2', 'beta-2', etc.
    """
    shifted_funscripts = {}

    for key, funscript in funscript_dict.items():
        if funscript is not None:
            # Generate phase-shifted version using source for delay calculation
            shifted = generate_phase_shifted_funscript(
                funscript,           # target funscript (alpha/beta/e1-e4)
                source_funscript,    # source funscript (for extreme detection)
                delay_percentage,
                min_segment_duration
            )

            # Store with -2 suffix
            shifted_key = f"{key}-2"
            shifted_funscripts[shifted_key] = shifted

    return shifted_funscripts

