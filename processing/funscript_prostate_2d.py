import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from processing.basic_transforms import invert_funscript, gaussian_smooth


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

        # Smoothing parameters (in samples at the given points_per_second):
        #   radius_smoothing: spreads radius transitions over ~200 ms so the output
        #     doesn't snap abruptly to/from center when motion slows or stops.
        #   output_smoothing: dampens large coordinate jumps over ~120 ms so alpha/beta
        #     never jumps across the circle in a single step.
        radius_smoothing = 5.0 * (points_per_second / 25.0)
        output_smoothing = 3.0 * (points_per_second / 25.0)

        alpha_funscript, beta_funscript = convert_funscript_radial(
            working_funscript,
            points_per_second=points_per_second,
            min_distance_from_center=0.1,
            radius_smoothing=radius_smoothing,
            output_smoothing=output_smoothing,
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


def _tear_radius(circle_radius, angle_deg, min_distance_from_center):
    """Variable radius for tear shape based on angle (degrees, 0-360)."""
    a = angle_deg % 360
    if a <= 120:
        progress = a / 120.0
        return circle_radius * (1.0 - progress * (1.0 - min_distance_from_center))
    elif a <= 240:
        return circle_radius * min_distance_from_center
    else:
        progress = (a - 240) / 120.0
        return circle_radius * (min_distance_from_center + progress * (1.0 - min_distance_from_center))


def _convert_tear_shaped(funscript_positions, min_distance_from_center):
    """
    Tear-shaped motion traced segment-by-segment between local extrema.

    Each monotone segment (consecutive extrema) has a fixed direction and a
    fixed center/radius derived from that segment's min and max values.
    Direction is assigned once per segment — never flipped mid-segment — which
    prevents the beta jump that occurred when point-by-point lookahead misread
    the direction near value 0.5.

    After all segments are computed a light Gaussian pass (sigma ≈ 2 samples)
    smooths the discontinuities at segment boundaries where adjacent stroke
    ranges differ.
    """
    n = len(funscript_positions)
    alpha_values = np.zeros(n)
    beta_values = np.zeros(n)

    extrema = _find_local_extrema(funscript_positions)

    if len(extrema) < 2:
        # Fallback: horizontal line at alpha position matching funscript value
        for i in range(n):
            pos = funscript_positions[i]
            alpha_values[i] = (0.5 - min_distance_from_center) + pos * (0.5 + min_distance_from_center)
            beta_values[i] = 0.5
        return np.clip(alpha_values, 0.0, 1.0), np.clip(beta_values, 0.0, 1.0)

    # Build boundary list: [virtual_start, extrema..., virtual_end]
    # Each consecutive pair defines one monotone segment with a known direction.
    boundaries = (
        [{'index': 0, 'value': funscript_positions[0]}]
        + [{'index': e['index'], 'value': e['value']} for e in extrema]
        + [{'index': n - 1, 'value': funscript_positions[n - 1]}]
    )

    for k in range(len(boundaries) - 1):
        b0 = boundaries[k]
        b1 = boundaries[k + 1]
        i0, i1 = b0['index'], b1['index']
        v0, v1 = b0['value'], b1['value']

        going_up = v1 >= v0
        local_min_val = min(v0, v1)
        local_max_val = max(v0, v1)
        range_size = local_max_val - local_min_val

        center_val = (local_max_val + local_min_val) / 2.0
        center_alpha = (0.5 - min_distance_from_center) + center_val * (0.5 + min_distance_from_center)
        circle_radius = min(range_size / 2.0, 0.5)

        for i in range(i0, i1 + 1):
            pos = funscript_positions[i]

            if range_size < 1e-6:
                angle = 0.0
            else:
                pos_in_range = np.clip((pos - local_min_val) / range_size, 0.0, 1.0)
                # Going up: angle sweeps 0 → π (right → top → left)
                # Going down: angle sweeps 2π → π (right ← bottom ← left, i.e. the return arc)
                angle = pos_in_range * np.pi if going_up else (2.0 * np.pi - pos_in_range * np.pi)

            angle_deg = np.degrees(angle) % 360
            radius = _tear_radius(circle_radius, angle_deg, min_distance_from_center)

            alpha_values[i] = center_alpha + radius * np.cos(angle)
            beta_values[i] = 0.5 + radius * np.sin(angle)

    # Light smoothing to bridge the discontinuities at segment boundaries
    # (adjacent strokes with different ranges produce different centers/radii).
    # sigma=2 ≈ 80 ms at 25 pps — smooths transitions without dulling motion.
    alpha_values = gaussian_smooth(alpha_values, sigma=2.0)
    beta_values = gaussian_smooth(beta_values, sigma=2.0)

    return np.clip(alpha_values, 0.0, 1.0), np.clip(beta_values, 0.0, 1.0)


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