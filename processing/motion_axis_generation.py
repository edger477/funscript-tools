"""
Motion Axis Generation module for creating E1-E4 axis files.

Generates motion axis files using linear mapping with configurable response curves
as an alternative to traditional alpha/beta generation.
"""

import math
from typing import Dict, Any, List, Tuple
from pathlib import Path
import numpy as np
from funscript import Funscript
from .linear_mapping import (
    apply_response_curve_to_funscript,
    get_default_response_curves,
    validate_control_points
)


# Default per-axis phase offsets in degrees so axes wobble out of sync.
# This is what makes per-axis modulation interesting: e1/e2 are 180° apart
# (counter-phased) and e3/e4 are quadrature against them.
DEFAULT_MODULATION_PHASE_DEG = {
    'e1': 0.0,
    'e2': 180.0,
    'e3': 90.0,
    'e4': 270.0,
}

# When modulation is enabled we resample the axis at this rate so the LFO
# has enough samples to actually exist. 60 Hz is plenty for the slow
# wobbles we expose (≤3 Hz).
MODULATION_RESAMPLE_HZ = 60.0


# Linear electrode layout: index-along-the-line for each axis.
# With e1→e4 sweep (default), e1 fires first and e4 fires last.
# With e4→e1 sweep, indices are reversed.
_AXIS_LINE_INDEX = {'e1': 0, 'e2': 1, 'e3': 2, 'e4': 3}


def _find_source_strokes(
    source_fs: Funscript,
    min_stroke_duration_s: float = 0.1,
) -> List[Tuple[float, float, str]]:
    """
    Split a source funscript into monotonic stroke segments.

    Each returned segment is (start_time, end_time, direction), where
    direction is 'up' (values rising) or 'down' (values falling).
    Segments shorter than min_stroke_duration_s are merged into the
    next segment to prevent micro-wobbles from triggering rapid
    flip-flops of the cascade direction.

    Args:
        source_fs: Source signal.
        min_stroke_duration_s: Shortest stroke that counts. Shorter
            segments get absorbed into the next one.

    Returns:
        List of (start_t, end_t, 'up'|'down') spanning the signal.
    """
    x = np.asarray(source_fs.x, dtype=float)
    y = np.asarray(source_fs.y, dtype=float)
    if len(x) < 2:
        return []

    diffs = np.diff(y)
    # Treat flat runs as continuing the previous direction.
    if len(diffs) == 0:
        return []

    # Determine initial direction (first non-zero diff)
    initial_sign = 0
    for d in diffs:
        if d > 0:
            initial_sign = 1
            break
        if d < 0:
            initial_sign = -1
            break
    if initial_sign == 0:
        return []  # Flat signal, no strokes

    raw_segments: List[Tuple[float, float, str]] = []
    seg_start_idx = 0
    cur_sign = initial_sign
    for i, d in enumerate(diffs):
        if d == 0:
            continue
        new_sign = 1 if d > 0 else -1
        if new_sign != cur_sign:
            # Extreme at index i (end of previous segment)
            raw_segments.append((
                float(x[seg_start_idx]),
                float(x[i]),
                'up' if cur_sign > 0 else 'down',
            ))
            seg_start_idx = i
            cur_sign = new_sign
    # Tail segment
    raw_segments.append((
        float(x[seg_start_idx]),
        float(x[-1]),
        'up' if cur_sign > 0 else 'down',
    ))

    # Merge segments shorter than min_stroke_duration_s into their neighbor.
    merged: List[Tuple[float, float, str]] = []
    for seg in raw_segments:
        seg_start, seg_end, direction = seg
        if seg_end - seg_start < min_stroke_duration_s and merged:
            # Extend the previous segment to cover this one (absorb the wobble)
            prev_start, _, prev_dir = merged[-1]
            merged[-1] = (prev_start, seg_end, prev_dir)
        else:
            merged.append(seg)

    return merged


def apply_direction_aware_cascade(
    fs: Funscript,
    source_fs: Funscript,
    line_index: int,
    step_s: float,
    source_duration_s: float,
    min_stroke_duration_s: float = 0.1,
) -> Funscript:
    """
    Cascade shift whose direction follows source stroke direction.

    On up-strokes in the source, axes are delayed by index*step (so
    e1 leads, e4 trails — an e1→e4 sweep). On down-strokes, axes are
    delayed by (3-index)*step (so e4 leads, e1 trails — an e4→e1 sweep).

    At each source stroke boundary, the per-axis delay may change,
    which creates overlap for some axes (the new stroke's lead time is
    shorter than the old stroke's tail) and gaps for others (the new
    stroke's lead time is longer). Resolution:

      - Overlap: newer stroke wins. Tail samples from the previous
        segment whose shifted time is >= the new segment's first
        shifted time get dropped.
      - Gap: hold the last value. A single sample is planted just
        before the new segment's start to keep the axis at its
        previous position until the new stroke reaches it.

    Args:
        fs: The axis funscript (after curve/modulation, before shift).
        source_fs: The original source signal — stroke detection runs
            here, not on the axis signal itself, so all four axes
            agree on the same stroke segmentation.
        line_index: 0, 1, 2, 3 for e1, e2, e3, e4.
        step_s: Seconds of delay per electrode step.
        source_duration_s: Truncate output past this time.
        min_stroke_duration_s: Micro-strokes shorter than this are
            absorbed into their neighbors.

    Returns:
        New Funscript with per-stroke direction-aware cascade applied.
    """
    if step_s <= 0.0 or len(fs.x) == 0:
        return Funscript(fs.x.copy(), fs.y.copy(), metadata=dict(fs.metadata))

    strokes = _find_source_strokes(source_fs, min_stroke_duration_s)
    if not strokes:
        # No strokes detected — fall back to fixed e1→e4 cascade
        return apply_cascade_shift(fs, line_index * step_s, source_duration_s)

    up_shift = line_index * step_s
    down_shift = (3 - line_index) * step_s

    x = np.asarray(fs.x, dtype=float)
    y = np.asarray(fs.y, dtype=float)
    start_value = float(y[0])

    out_x: List[float] = [0.0]
    out_y: List[float] = [start_value]

    for seg_start, seg_end, direction in strokes:
        shift = up_shift if direction == 'up' else down_shift

        # Axis samples whose original timestamps fall in this stroke's
        # source range. Use inclusive-start/inclusive-end so a sample
        # exactly on a boundary goes to the earlier segment.
        mask = (x >= seg_start) & (x <= seg_end)
        if not np.any(mask):
            continue

        seg_x_shifted = x[mask] + shift
        seg_y = y[mask]

        first_new = float(seg_x_shifted[0])

        # Drop overlap: pop outputs whose shifted time >= this segment's
        # first shifted time. Keep the initial head-pad at t=0.
        while len(out_x) > 1 and out_x[-1] >= first_new:
            out_x.pop()
            out_y.pop()

        # Gap padding: if there's a noticeable gap, plant one hold sample
        # just before the new segment starts so the axis idles at its
        # previous value instead of interpolating across the gap.
        if first_new - out_x[-1] > 0.005:
            out_x.append(max(0.0, first_new - 0.001))
            out_y.append(out_y[-1])

        for xi, yi in zip(seg_x_shifted, seg_y):
            out_x.append(float(xi))
            out_y.append(float(yi))

    # Truncate to source_duration_s
    if source_duration_s > 0:
        final_x: List[float] = []
        final_y: List[float] = []
        for xi, yi in zip(out_x, out_y):
            if xi > source_duration_s:
                break
            final_x.append(xi)
            final_y.append(yi)
        out_x, out_y = final_x, final_y

    if not out_x:
        out_x = [0.0]
        out_y = [start_value]

    return Funscript(np.array(out_x), np.array(out_y), metadata=dict(fs.metadata))


def apply_cascade_shift(
    fs: Funscript,
    shift_s: float,
    source_duration_s: float,
) -> Funscript:
    """
    Delay a funscript by shift_s seconds, padding the head with the
    starting value and truncating the tail so the result still fits
    within [0, source_duration_s].

    This is the per-axis time offset used to create apparent motion
    across a linear electrode array. Each axis is independently shifted
    by a different amount (0, Δt, 2Δt, 3Δt) so the stimulus sweeps
    across the electrodes.

    Args:
        fs: Source axis funscript. x is in seconds.
        shift_s: Delay in seconds. 0 is a no-op; positive values push
            the signal later in time.
        source_duration_s: Total duration (seconds) to which the output
            is truncated. Typically the duration of the main signal.

    Returns:
        New Funscript with padded head and truncated tail.
    """
    if shift_s <= 0.0 or len(fs.x) == 0:
        return Funscript(fs.x.copy(), fs.y.copy(), metadata=dict(fs.metadata))

    x = np.asarray(fs.x, dtype=float)
    y = np.asarray(fs.y, dtype=float)

    start_value = float(y[0])

    # Shift every original timestamp forward by shift_s.
    shifted_x = x + shift_s
    shifted_y = y

    # Prepend a head-pad sample at t=0 holding the starting value so
    # playback devices idle at the axis's starting position instead of
    # jumping from undefined to the first sample.
    new_x = np.concatenate(([0.0], shifted_x))
    new_y = np.concatenate(([start_value], shifted_y))

    # Truncate anything past source_duration_s so all axes remain the
    # same length as the source signal.
    if source_duration_s > 0:
        mask = new_x <= source_duration_s
        if not np.any(mask):
            # Whole thing was shifted past the end — keep only the pad.
            new_x = np.array([0.0])
            new_y = np.array([start_value])
        else:
            new_x = new_x[mask]
            new_y = new_y[mask]

    return Funscript(new_x, new_y, metadata=dict(fs.metadata))


def apply_modulation(
    fs: Funscript,
    frequency_hz: float,
    depth: float,
    phase_deg: float = 0.0,
) -> Funscript:
    """
    Apply a sine LFO modulation to a funscript without clamping artifacts.

    The signal is first resampled to MODULATION_RESAMPLE_HZ so the wobble
    is densely represented even on sparse source scripts. Then the source
    is shrunk from [0, 1] into [depth, 1 - depth] so we have headroom for
    the LFO without ever pushing outside [0, 1]:

        shrunk = depth + y * (1 - 2*depth)
        wobble = depth * sin(2π * f * t + phase)
        out    = shrunk + wobble

    This way the wobble has full amplitude everywhere — including the
    middle of the stroke and the extremes — and no hard clamping is needed.
    The trade-off is that peak excursions are slightly reduced (a y=1 input
    only reaches 1 at the LFO crest).

    Args:
        fs: Source funscript (x in seconds, y in 0..1).
        frequency_hz: LFO frequency in Hz.
        depth: Wobble amount, 0..0.5. 0 disables, ~0.15 is a gentle texture.
        phase_deg: Phase offset in degrees (lets multiple axes counter-phase).

    Returns:
        New Funscript with modulation applied.
    """
    if depth <= 0.0 or frequency_hz <= 0.0 or len(fs.x) < 2:
        return Funscript(fs.x.copy(), fs.y.copy(), metadata=dict(fs.metadata))

    # Cap depth so the [depth, 1-depth] window doesn't collapse / invert.
    depth = min(depth, 0.5)

    x = np.asarray(fs.x, dtype=float)
    y = np.asarray(fs.y, dtype=float)

    # Resample uniformly at MODULATION_RESAMPLE_HZ between the original
    # start and end times so the LFO has room to breathe.
    t_start = float(x[0])
    t_end = float(x[-1])
    duration = t_end - t_start
    if duration <= 0.0:
        return Funscript(fs.x.copy(), fs.y.copy(), metadata=dict(fs.metadata))

    n_samples = max(2, int(math.ceil(duration * MODULATION_RESAMPLE_HZ)) + 1)
    new_x = np.linspace(t_start, t_end, n_samples)

    # Linear interpolation of the original positions onto the dense grid.
    new_y = np.interp(new_x, x, y)

    # Shrink into [depth, 1-depth] to make headroom for the LFO.
    shrunk = depth + new_y * (1.0 - 2.0 * depth)

    # Sine LFO keyed off absolute time so output is deterministic
    # regardless of where the segment starts.
    phase_rad = math.radians(phase_deg)
    wobble = depth * np.sin(2.0 * math.pi * frequency_hz * new_x + phase_rad)

    modulated = shrunk + wobble

    # Safety clamp (numerical headroom only — should already be in range).
    modulated = np.clip(modulated, 0.0, 1.0)

    return Funscript(new_x, modulated, metadata=dict(fs.metadata))


def generate_motion_axes(
    main_funscript: Funscript,
    config: Dict[str, Any],
    output_directory: Path,
    filename_base: str = None
) -> Dict[str, Path]:
    """
    Generate all enabled motion axis files (E1-E4) from main funscript.

    Args:
        main_funscript: Source funscript for generation
        config: Motion axis configuration
        output_directory: Directory to save generated files
        filename_base: Base filename (without extension) for output files

    Returns:
        Dictionary mapping axis names to generated file paths
    """
    generated_files = {}
    default_curves = get_default_response_curves()

    # Physical-model cascade: linear e1-e2-e3-e4 electrode array. When
    # enabled, each axis is delayed by axis_index * (spacing / speed) so
    # the stimulus sweeps across electrodes, producing apparent motion.
    phys_model = config.get('physical_model', {}) if isinstance(config, dict) else {}
    phys_enabled = bool(phys_model.get('enabled', False))
    phys_spacing = float(phys_model.get('electrode_spacing_mm', 20.0))
    phys_speed = float(phys_model.get('propagation_speed_mm_s', 300.0))
    phys_direction = str(phys_model.get('sweep_direction', 'e1_to_e4'))
    if phys_enabled and phys_spacing > 0 and phys_speed > 0:
        step_s = (phys_spacing / phys_speed)
    else:
        step_s = 0.0
    # Duration of the source signal — used to truncate shifted axes so
    # they don't run past the original video length.
    if len(main_funscript.x) >= 1:
        source_duration_s = float(main_funscript.x[-1])
    else:
        source_duration_s = 0.0

    for axis_name in ['e1', 'e2', 'e3', 'e4']:
        axis_config = config.get(axis_name, {})

        if not axis_config.get('enabled', False):
            continue

        # Get curve configuration
        curve_config = axis_config.get('curve', default_curves[axis_name])
        control_points = curve_config.get('control_points', default_curves[axis_name]['control_points'])

        # Validate control points
        print(f"[generate] {axis_name}: {len(control_points)} points, cp={control_points}")
        if not validate_control_points(control_points):
            print(f"Warning: Invalid control points for {axis_name}, using default")
            control_points = default_curves[axis_name]['control_points']

        # Apply signal rotation before curve if angle is set
        signal_angle = axis_config.get('signal_angle', 0)
        if signal_angle:
            import math
            cos_a = math.cos(math.radians(signal_angle))
            rotated_positions = [max(0.0, min(1.0, 0.5 + (p - 0.5) * cos_a))
                                 for p in main_funscript.y]
            rotated_fs = Funscript(main_funscript.x.copy(), rotated_positions)
            print(f"  {axis_name}: signal rotated by {signal_angle}\u00b0 "
                  f"(input {min(main_funscript.y):.3f}-{max(main_funscript.y):.3f} "
                  f"→ rotated {min(rotated_positions):.3f}-{max(rotated_positions):.3f})")
        else:
            rotated_fs = main_funscript

        # Generate axis funscript by applying curve to (rotated) signal
        axis_funscript = apply_response_curve_to_funscript(
            rotated_fs,
            control_points
        )

        # Apply per-axis modulation (sine LFO) if enabled. Applied here,
        # before phase shift, so the phase-shifted axis carries the wobble.
        modulation_cfg = axis_config.get('modulation', {})
        mod_enabled = modulation_cfg.get('enabled', False)
        mod_freq = float(modulation_cfg.get('frequency_hz', 0.5))
        mod_depth = float(modulation_cfg.get('depth', 0.15))
        # phase_enabled lets the user park a phase value but disable its
        # effect (treats phase as 0 without losing the configured number).
        phase_enabled = modulation_cfg.get('phase_enabled', True)
        mod_phase = float(modulation_cfg.get(
            'phase_deg', DEFAULT_MODULATION_PHASE_DEG.get(axis_name, 0.0)))
        if not phase_enabled:
            mod_phase = 0.0
        if mod_enabled and mod_depth > 0.0 and mod_freq > 0.0:
            print(f"  {axis_name}: modulation freq={mod_freq}Hz "
                  f"depth={mod_depth} phase={mod_phase}\u00b0")
            axis_funscript = apply_modulation(
                axis_funscript, mod_freq, mod_depth, mod_phase)

        # Physical-model cascade shift. Each axis's index along the line
        # determines its delay.
        #  - 'e1_to_e4'       : fixed, e1 leads
        #  - 'e4_to_e1'       : fixed, e4 leads
        #  - 'signal_direction': e1 leads on up-strokes, e4 leads on down-strokes
        cascade_shift_s = 0.0
        if step_s > 0:
            line_index = _AXIS_LINE_INDEX[axis_name]
            if phys_direction == 'signal_direction':
                # Per-stroke direction-aware cascade — the shift value
                # varies across the signal, so there's no single number
                # to report. Metadata will still record the "nominal"
                # e1→e4 shift for reference.
                cascade_shift_s = line_index * step_s
                print(f"  {axis_name}: direction-aware cascade "
                      f"(step={step_s*1000:.1f}ms, spacing={phys_spacing}mm, "
                      f"speed={phys_speed}mm/s)")
                axis_funscript = apply_direction_aware_cascade(
                    axis_funscript, main_funscript, line_index, step_s,
                    source_duration_s)
            else:
                if phys_direction == 'e4_to_e1':
                    line_index = 3 - line_index
                cascade_shift_s = line_index * step_s
                if cascade_shift_s > 0:
                    print(f"  {axis_name}: cascade shift {cascade_shift_s*1000:.1f}ms "
                          f"(spacing={phys_spacing}mm, speed={phys_speed}mm/s, "
                          f"dir={phys_direction})")
                    axis_funscript = apply_cascade_shift(
                        axis_funscript, cascade_shift_s, source_duration_s)

        # Add metadata
        from version import __version__, __app_name__, __url__
        axis_funscript.metadata = {
            "creator": __app_name__,
            "description": f"Generated by {__app_name__} v{__version__} - Motion axis {axis_name.upper()}",
            "url": __url__,
            "title": f"Motion Axis {axis_name.upper()}",
            "metadata": {
                "generator": __app_name__,
                "generator_version": __version__,
                "file_type": f"motion_axis_{axis_name}",
                "response_curve_control_points": control_points,
                "modulation": {
                    "enabled": mod_enabled,
                    "frequency_hz": mod_freq,
                    "depth": mod_depth,
                    "phase_deg": mod_phase,
                    "phase_enabled": phase_enabled,
                },
                "physical_model": {
                    "enabled": phys_enabled,
                    "electrode_spacing_mm": phys_spacing,
                    "propagation_speed_mm_s": phys_speed,
                    "sweep_direction": phys_direction,
                    "cascade_shift_ms": cascade_shift_s * 1000.0,
                }
            }
        }

        # Save to file
        if filename_base is None:
            filename_base = output_directory.stem
        output_path = output_directory / f"{filename_base}.{axis_name}.funscript"
        axis_funscript.save_to_path(output_path)
        generated_files[axis_name] = output_path

        print(f"Generated {axis_name} axis: {output_path}")

    return generated_files


def get_motion_axis_config_template() -> Dict[str, Any]:
    """
    Get template configuration for motion axis generation.

    Returns:
        Template configuration dictionary
    """
    default_curves = get_default_response_curves()

    return {
        "enabled": True,
        "mode": "motion_axis",  # or "legacy" for alpha/beta
        "e1": {
            "enabled": True,
            "curve": default_curves["e1"]
        },
        "e2": {
            "enabled": True,
            "curve": default_curves["e2"]
        },
        "e3": {
            "enabled": False,  # Disabled by default
            "curve": default_curves["e3"]
        },
        "e4": {
            "enabled": False,  # Disabled by default
            "curve": default_curves["e4"]
        }
    }


def validate_motion_axis_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate motion axis configuration.

    Args:
        config: Motion axis configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not isinstance(config, dict):
        errors.append("Configuration must be a dictionary")
        return errors

    # Check mode
    mode = config.get('mode', 'motion_axis')
    if mode not in ['motion_axis', 'legacy']:
        errors.append(f"Invalid mode: {mode}. Must be 'motion_axis' or 'legacy'")

    # Check axis configurations
    for axis_name in ['e1', 'e2', 'e3', 'e4']:
        axis_config = config.get(axis_name, {})

        if not isinstance(axis_config, dict):
            errors.append(f"{axis_name} configuration must be a dictionary")
            continue

        # Check curve configuration if axis is enabled
        if axis_config.get('enabled', False):
            curve_config = axis_config.get('curve', {})

            if not isinstance(curve_config, dict):
                errors.append(f"{axis_name} curve configuration must be a dictionary")
                continue

            control_points = curve_config.get('control_points', [])
            if not validate_control_points(control_points):
                errors.append(f"{axis_name} has invalid control points")


    return errors


def create_custom_curve(
    name: str,
    description: str,
    control_points: List[Tuple[float, float]]
) -> Dict[str, Any]:
    """
    Create a custom response curve configuration.

    Args:
        name: Human-readable curve name
        description: Curve description
        control_points: List of (input, output) control points

    Returns:
        Curve configuration dictionary
    """
    if not validate_control_points(control_points):
        raise ValueError("Invalid control points provided")

    return {
        "name": name,
        "description": description,
        "control_points": control_points
    }


def get_curve_presets() -> Dict[str, Dict[str, Any]]:
    """
    Get all available curve presets including defaults and common variations.

    Returns:
        Dictionary of preset curve configurations
    """
    presets = get_default_response_curves()

    # Add additional preset variations
    presets.update({
        "inverted": {
            "name": "Inverted",
            "description": "Inverted linear mapping",
            "control_points": [(0.0, 1.0), (1.0, 0.0)]
        },
        "s_curve": {
            "name": "S-Curve",
            "description": "Smooth acceleration and deceleration",
            "control_points": [(0.0, 0.0), (0.2, 0.1), (0.5, 0.5), (0.8, 0.9), (1.0, 1.0)]
        },
        "sharp_peak": {
            "name": "Sharp Peak",
            "description": "Sharp emphasis on middle range",
            "control_points": [(0.0, 0.0), (0.4, 0.1), (0.5, 1.0), (0.6, 0.1), (1.0, 0.0)]
        },
        "gentle_wave": {
            "name": "Gentle Wave",
            "description": "Gentle wave-like response",
            "control_points": [(0.0, 0.2), (0.25, 0.7), (0.5, 0.3), (0.75, 0.8), (1.0, 0.4)]
        }
    })

    return presets


def copy_existing_axis_files(
    input_directory: Path,
    output_directory: Path,
    filename_base: str,
    enabled_axes: List[str]
) -> Dict[str, Path]:
    """
    Copy existing motion axis files if they exist.

    Args:
        input_directory: Directory containing existing files
        output_directory: Directory to copy files to
        filename_base: Base filename without extension
        enabled_axes: List of axis names to look for

    Returns:
        Dictionary mapping axis names to copied file paths
    """
    copied_files = {}

    for axis_name in enabled_axes:
        source_path = input_directory / f"{filename_base}.{axis_name}.funscript"

        if source_path.exists():
            dest_path = output_directory / f"{filename_base}.{axis_name}.funscript"

            # Copy file (could use shutil.copy2 for metadata preservation)
            with open(source_path, 'r') as src, open(dest_path, 'w') as dst:
                dst.write(src.read())

            copied_files[axis_name] = dest_path
            print(f"Copied existing {axis_name} file: {dest_path}")

    return copied_files