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


def _convert_tear_shaped(funscript_positions, min_distance_from_center,
                          stroke_threshold=0.25):
    """
    Tear-shaped 2D motion from a 1D funscript.

    Each monotone stroke is mapped to a sine arc in beta around the
    beta=0.5 axis:
      - Upstrokes arc ABOVE beta=0.5 (wide side of the tear).
      - Downstrokes arc BELOW beta=0.5 scaled by min_distance_from_center
        (narrow side of the tear).

    Alpha tracks the funscript position directly (0→1 = left→right).
    Because sin(0) = sin(π) = 0, beta is exactly 0.5 at every stroke
    extremum — consecutive strokes connect with zero discontinuity and the
    tear never "resets" mid-oscillation.

    Strokes shorter than stroke_threshold produce no arc (beta stays 0.5)
    so short oscillations glide smoothly without tiny restart loops.

    Parameters:
        min_distance_from_center: ratio of narrow-side bulge to wide-side
            bulge (0.0 = flat return, 1.0 = symmetric oval, default 0.5).
        stroke_threshold: minimum stroke range (0–1) to trigger the arc
            (default 0.25).
    """
    n = len(funscript_positions)
    alpha_values = np.asarray(funscript_positions, dtype=float).copy()
    beta_values = np.full(n, 0.5)

    extrema = _find_local_extrema(funscript_positions)

    if len(extrema) < 2:
        return np.clip(alpha_values, 0.0, 1.0), beta_values.copy()

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

        stroke_range = abs(v1 - v0)
        if stroke_range < stroke_threshold or stroke_range < 1e-9:
            # Short stroke: alpha = position, beta = 0.5 (already initialised)
            continue

        going_up = v1 > v0
        bulge_wide = min(stroke_range / 2.0, 0.5)
        beta_dir = bulge_wide if going_up else -(bulge_wide * min_distance_from_center)

        for i in range(i0, i1 + 1):
            t = np.clip((funscript_positions[i] - v0) / (v1 - v0), 0.0, 1.0)
            beta_values[i] = 0.5 + beta_dir * np.sin(t * np.pi)
            # alpha_values[i] already set to funscript_positions[i]

    # Smooth out any derivative kinks at segment boundaries.
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