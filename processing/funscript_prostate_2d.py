import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from processing.basic_transforms import invert_funscript


def convert_funscript_prostate(funscript, points_per_second=25, algorithm="standard",
                              min_distance_from_center=0.5, generate_from_inverted=True):
    """
    Convert 1D funscript to 2D for prostate stimulation using specialized algorithms.

    Args:
        funscript: Input Funscript object
        points_per_second: Interpolation density (1-100, default 25)
        algorithm: "standard" or "tear-shaped" (default "standard")
        min_distance_from_center: Distance for tear-shaped constant zone (0.3-0.9, default 0.5)
        generate_from_inverted: Whether to invert funscript before conversion (default True)

    Returns:
        tuple: (alpha_funscript, beta_funscript) for prostate stimulation
    """
    # Apply inversion if requested
    if generate_from_inverted:
        working_funscript = invert_funscript(funscript)
    else:
        working_funscript = funscript

    if len(working_funscript.x) < 2:
        raise ValueError("Funscript must have at least 2 actions for prostate conversion.")

    # Convert to alpha and beta based on algorithm
    if algorithm == "tear-shaped":
        # Create interpolated timeline for tear-shaped algorithm
        start_time = working_funscript.x[0]
        end_time = working_funscript.x[-1]
        duration = end_time - start_time
        num_points = int(duration * points_per_second)

        if num_points < 2:
            num_points = 2

        new_times = np.linspace(start_time, end_time, num_points)

        # Interpolate positions
        interpolated_positions = np.interp(new_times, working_funscript.x, working_funscript.y)

        alpha_values, beta_values = _convert_tear_shaped(
            interpolated_positions, min_distance_from_center
        )

        # Create Funscript objects (values already in 0-1 range, as expected by Funscript class)
        alpha_funscript = Funscript(new_times.tolist(), alpha_values.tolist())
        beta_funscript = Funscript(new_times.tolist(), beta_values.tolist())

    else:  # standard - use the same circular algorithm as basic tab
        # Import the basic circular conversion function
        from processing.funscript_1d_to_2d import convert_funscript_radial

        # Use the basic circular algorithm directly with the working funscript
        # Uses defaults: speed_threshold_percent=50, min_distance_from_center=0.1
        alpha_funscript, beta_funscript = convert_funscript_radial(
            working_funscript,
            points_per_second=points_per_second,
            min_distance_from_center=0.1  # Use basic algorithm default
        )

    return alpha_funscript, beta_funscript




def _find_local_extrema(positions):
    """Find local minima and maxima in the position data."""
    extrema = []

    if len(positions) < 3:
        return extrema

    for i in range(1, len(positions) - 1):
        prev_val = positions[i-1]
        curr_val = positions[i]
        next_val = positions[i+1]

        # Local maximum
        if curr_val > prev_val and curr_val > next_val:
            extrema.append({'index': i, 'value': curr_val, 'type': 'max'})
        # Local minimum
        elif curr_val < prev_val and curr_val < next_val:
            extrema.append({'index': i, 'value': curr_val, 'type': 'min'})

    return extrema


def _convert_tear_shaped(funscript_positions, min_distance_from_center):
    """
    Tear-shaped motion with dynamic centers based on local minima/maxima.

    2D Circle Coordinate System:
    - Alpha=0.5, Beta=0.5 = center of circle (diameter = 1.0)
    - Alpha=1.0, Beta=0.5 = top (0°)
    - Circle boundary: distance from center = 0.5

    Input Mapping:
    - input=1.0 → Alpha=1.0, Beta=0.5 (top of circle)
    - input=0.0 → Alpha=0.5-min_distance, Beta=0.5 (left of center on horizontal line)

    Algorithm:
    1. Find local min/max pairs
    2. Set center at halfway between adjacent min/max (always at Beta=0.5)
    3. Create tear shape around each center:
       - Top of tear = local maximum position
       - Point of tear = local minimum position
       - Counter-clockwise movement with variable radius:
         * 0°-120°: radius decreases linearly to min_distance
         * 120°-240°: radius stays at min_distance
         * 240°-360°: radius increases linearly back to full
    4. Move directly to next center when changing segments
    """
    n_points = len(funscript_positions)
    alpha_values = np.zeros(n_points)
    beta_values = np.zeros(n_points)

    # Find local extrema
    extrema = _find_local_extrema(funscript_positions)

    if len(extrema) < 2:
        # Fallback: simple linear mapping without extrema
        for i in range(n_points):
            pos = funscript_positions[i]
            # Direct mapping based on input range
            alpha_values[i] = (0.5 - min_distance_from_center) + pos * (0.5 + min_distance_from_center)
            beta_values[i] = 0.5  # Always on horizontal line

        # Clamp to valid range
        alpha_values = np.clip(alpha_values, 0.0, 1.0)
        beta_values = np.clip(beta_values, 0.0, 1.0)
        return alpha_values, beta_values

    # Create extrema pairs for tear shape centers
    extrema_pairs = []
    for i in range(0, len(extrema) - 1, 2):
        if i + 1 < len(extrema):
            current_extremum = extrema[i]
            next_extremum = extrema[i + 1]

            # Determine which is max and which is min
            if current_extremum['type'] == 'max' and next_extremum['type'] == 'min':
                local_max = current_extremum
                local_min = next_extremum
            elif current_extremum['type'] == 'min' and next_extremum['type'] == 'max':
                local_max = next_extremum
                local_min = current_extremum
            else:
                # Handle case where we don't have a proper min/max pair
                if current_extremum['value'] > next_extremum['value']:
                    local_max = current_extremum
                    local_min = next_extremum
                else:
                    local_max = next_extremum
                    local_min = current_extremum

            extrema_pairs.append({
                'local_max': local_max,
                'local_min': local_min,
                'center_index': (local_max['index'] + local_min['index']) // 2
            })

    if not extrema_pairs:
        # No valid pairs, use fallback
        for i in range(n_points):
            pos = funscript_positions[i]
            alpha_values[i] = (0.5 - min_distance_from_center) + pos * (0.5 + min_distance_from_center)
            beta_values[i] = 0.5
        return np.clip(alpha_values, 0.0, 1.0), np.clip(beta_values, 0.0, 1.0)

    # Process all points sequentially
    for i in range(n_points):
        pos = funscript_positions[i]

        # Find the closest extrema pair for this point
        if len(extrema_pairs) == 1:
            closest_pair = extrema_pairs[0]
        else:
            # Find the pair with center closest to current index
            closest_pair = min(extrema_pairs, key=lambda p: abs(p['center_index'] - i))

        local_max = closest_pair['local_max']
        local_min = closest_pair['local_min']

        # Calculate center between this pair (always at Beta=0.5)
        center_value = (local_max['value'] + local_min['value']) / 2.0
        center_alpha = (0.5 - min_distance_from_center) + center_value * (0.5 + min_distance_from_center)
        center_beta = 0.5

        # Calculate circle radius based on local range: radius = (max - min) / 2
        local_range = abs(local_max['value'] - local_min['value'])
        circle_radius = local_range / 2.0
        circle_radius = min(circle_radius, 0.5)

        # Find where we are in the current segment progression
        # Look at nearby points to determine if we're moving up or down
        direction = 1  # 1 = moving toward max, -1 = moving toward min

        # Simple direction detection: compare with next few positions if available
        if i < n_points - 3:
            future_trend = np.mean(funscript_positions[i+1:i+4]) - pos
            if future_trend > 0:
                direction = 1  # moving up toward max
            else:
                direction = -1  # moving down toward min

        # Map position to progress within the tear shape cycle
        # Each cycle goes: max -> min -> max (full tear shape)
        range_size = local_max['value'] - local_min['value']
        if range_size < 1e-6:  # Avoid division by zero
            angle = 0.0
        else:
            pos_in_range = (pos - local_min['value']) / range_size
            pos_in_range = np.clip(pos_in_range, 0.0, 1.0)

            if direction == 1:
                # Moving up (toward max): map to first half of tear (0° to 180°)
                angle = pos_in_range * np.pi
            else:
                # Moving down (toward min): map to second half of tear (360° to 180°, backwards)
                # When pos_in_range=0 (at min), we want 360° (top of right side)
                # When pos_in_range=1 (at max), we want 180° (bottom)
                angle = 2 * np.pi - pos_in_range * np.pi

        angle_deg = np.degrees(angle) % 360

        # Calculate radius based on angle (proper tear shape)
        if angle_deg <= 120:
            # 0°-120°: radius decreases linearly from full to min_distance
            progress = angle_deg / 120.0
            radius = circle_radius * (1.0 - progress * (1.0 - min_distance_from_center))
        elif angle_deg <= 240:
            # 120°-240°: radius stays at min_distance (constant zone)
            radius = circle_radius * min_distance_from_center
        else:
            # 240°-360°: radius increases linearly from min_distance back to full
            progress = (angle_deg - 240) / 120.0
            radius = circle_radius * (min_distance_from_center + progress * (1.0 - min_distance_from_center))

        # Calculate final coordinates around the center
        alpha_values[i] = center_alpha + radius * np.cos(angle)
        beta_values[i] = center_beta + radius * np.sin(angle)

    # Clamp to valid range
    alpha_values = np.clip(alpha_values, 0.0, 1.0)
    beta_values = np.clip(beta_values, 0.0, 1.0)

    return alpha_values, beta_values


def generate_alpha_beta_prostate_from_main(main_funscript, points_per_second=25,
                                          algorithm="standard", min_distance_from_center=0.5,
                                          generate_from_inverted=True):
    """
    Generate alpha-prostate and beta-prostate funscripts from main funscript.

    Args:
        main_funscript: Input Funscript object
        points_per_second: Interpolation density (default 25)
        algorithm: "standard" or "tear-shaped" (default "standard")
        min_distance_from_center: Distance for tear-shaped constant zone (default 0.5)
        generate_from_inverted: Whether to invert before conversion (default True)

    Returns:
        tuple: (alpha_prostate_funscript, beta_prostate_funscript)
    """
    # Import version info for metadata
    from version import __version__, __app_name__, __url__

    alpha_funscript, beta_funscript = convert_funscript_prostate(
        main_funscript, points_per_second, algorithm,
        min_distance_from_center, generate_from_inverted
    )

    # Add metadata to generated funscripts
    algorithm_names = {
        "standard": "Standard Prostate Motion",
        "tear-shaped": "Tear-Shaped Prostate Motion"
    }

    base_metadata = {
        "creator": __app_name__,
        "description": f"Generated by {__app_name__} v{__version__} using {algorithm_names.get(algorithm, algorithm)} for prostate stimulation",
        "url": __url__,
        "metadata": {
            "generator": __app_name__,
            "generator_version": __version__,
            "prostate_algorithm": algorithm,
            "points_per_second": points_per_second,
            "min_distance_from_center": min_distance_from_center,
            "generated_from_inverted": generate_from_inverted
        }
    }

    alpha_funscript.metadata = base_metadata.copy()
    alpha_funscript.metadata["title"] = "Alpha-Prostate (Horizontal) Axis"

    beta_funscript.metadata = base_metadata.copy()
    beta_funscript.metadata["title"] = "Beta-Prostate (Vertical) Axis"

    return alpha_funscript, beta_funscript