"""
Trochoid Spatial Mapping.

Drives N electrodes (default 4 at 0/90/180/270°) from a 1D input signal
by:

    1. Parameterizing a 2D curve (hypotrochoid, rose, butterfly, ...)
       by the input position.
    2. For each (x, y) on the curve, computing per-electrode intensity
       via a directional / distance / amplitude rule.

Result: each electrode gets its own intensity track over time, and
together they paint a "rotating sensation" pattern around the
electrode array as the input sweeps.

This is an alternative to the response-curve-based motion-axis
generation in motion_axis_generation.py — it produces the same kind of
output (e1/e2/e3/e4 intensity funscripts) by a fundamentally different
mechanism (spatial projection vs. per-axis curve mapping).
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np

sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from .trochoid_quantization import (
    curve_xy, get_family_theta_max, FAMILY_DEFAULTS,
)


VALID_MAPPINGS = ('directional', 'distance', 'amplitude')

# Default electrode angles in degrees (compass-like layout):
DEFAULT_ELECTRODE_ANGLES_DEG = (0.0, 90.0, 180.0, 270.0)


def compute_spatial_intensities(
    input_y: np.ndarray,
    family: str,
    params: Dict[str, Any],
    electrode_angles_deg: Tuple[float, ...] = DEFAULT_ELECTRODE_ANGLES_DEG,
    mapping: str = 'directional',
    sharpness: float = 1.0,
    cycles_per_unit: float = 1.0,
) -> Dict[str, np.ndarray]:
    """
    Compute per-electrode intensity arrays from a 1D input signal.

    Args:
        input_y: 1D array of input positions in [0, 1].
        family: Curve family ('hypo', 'epi', 'rose', etc.).
        params: Family-specific curve parameters.
        electrode_angles_deg: Compass angles for the electrodes (one per
            output channel). Default: (0, 90, 180, 270).
        mapping: 'directional' | 'distance' | 'amplitude'.
        sharpness: Exponent applied to the cosine in directional/amplitude
            modes. Higher = more selective (electrode lights only when
            path points nearly straight at it). 1.0 = soft, 4.0 = sharp.
        cycles_per_unit: How many full curve cycles per 0→1 input change.
            Higher = faster electrode flicker per stroke.

    Returns:
        Dict {'e1': array, 'e2': array, ...} matching the order of
        electrode_angles_deg. Each array is the same length as input_y
        and lies in [0, 1].
    """
    if mapping not in VALID_MAPPINGS:
        raise ValueError(
            f"mapping must be one of {VALID_MAPPINGS}, got {mapping!r}")

    input_y = np.asarray(input_y, dtype=float)
    input_y = np.clip(input_y, 0.0, 1.0)

    # Drive the curve parameter from the input. theta_max keeps the sweep
    # extent consistent across families (butterfly traces over 12π naturally,
    # most others over 2π).
    theta_max = get_family_theta_max(family)
    theta = theta_max * float(cycles_per_unit) * input_y
    x, y = curve_xy(theta, family, params)

    # Normalize the curve into a unit-radius reference so the angular /
    # distance math is comparable across very different families.
    finite = np.isfinite(x) & np.isfinite(y)
    if not finite.all():
        x = np.where(finite, x, 0.0)
        y = np.where(finite, y, 0.0)
    radii = np.sqrt(x * x + y * y)
    rmax = float(np.max(radii)) if len(radii) else 1.0
    if rmax < 1e-12:
        rmax = 1.0
    xn = x / rmax
    yn = y / rmax
    rn = radii / rmax  # in [0, 1]

    out: Dict[str, np.ndarray] = {}
    sharpness = max(0.01, float(sharpness))

    if mapping == 'directional':
        path_angle = np.arctan2(yn, xn)
        for i, angle_deg in enumerate(electrode_angles_deg):
            ang = np.radians(angle_deg)
            cos_val = np.cos(path_angle - ang)
            cos_val = np.clip(cos_val, 0.0, 1.0)
            out[f'e{i + 1}'] = cos_val ** sharpness

    elif mapping == 'distance':
        # Place the electrodes on the unit circle.
        for i, angle_deg in enumerate(electrode_angles_deg):
            ang = np.radians(angle_deg)
            ex, ey = np.cos(ang), np.sin(ang)
            # Distance from each curve point to this electrode.
            dx = xn - ex
            dy = yn - ey
            d = np.sqrt(dx * dx + dy * dy)
            # Map distance [0, 2] (electrode-to-antipode) to intensity [1, 0].
            intensity = np.clip(1.0 - d / 2.0, 0.0, 1.0)
            out[f'e{i + 1}'] = intensity ** sharpness

    else:  # 'amplitude'
        # Combine radius (reach) with direction (cosine).
        path_angle = np.arctan2(yn, xn)
        for i, angle_deg in enumerate(electrode_angles_deg):
            ang = np.radians(angle_deg)
            cos_val = np.cos(path_angle - ang)
            cos_val = np.clip(cos_val, 0.0, 1.0)
            out[f'e{i + 1}'] = rn * (cos_val ** sharpness)

    # Final sanitation
    for key, arr in out.items():
        out[key] = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
        np.clip(out[key], 0.0, 1.0, out=out[key])

    return out


def generate_spatial_funscripts(
    main_funscript: Funscript,
    family: str,
    params: Dict[str, Any],
    electrode_angles_deg: Tuple[float, ...] = DEFAULT_ELECTRODE_ANGLES_DEG,
    mapping: str = 'directional',
    sharpness: float = 1.0,
    cycles_per_unit: float = 1.0,
    densify_hz: float = 60.0,
) -> Dict[str, Funscript]:
    """
    Build per-electrode Funscript outputs from the main signal.

    When `densify_hz > 0`, the input y is linearly resampled to that
    rate before the curve mapping is evaluated. This matters when
    `cycles_per_unit` is high or the family has many lobes: between
    two sparse input samples the curve can traverse a significant
    arc, producing intensity variation that would otherwise be
    aliased away. Setting densify_hz = 0 preserves the old behavior
    (output shares the input's timestamps exactly).
    """
    t_in = np.asarray(main_funscript.x, dtype=float)
    y_in = np.asarray(main_funscript.y, dtype=float)
    if len(t_in) >= 2 and float(densify_hz) > 0.0:
        duration = float(t_in[-1] - t_in[0])
        if duration > 0.0:
            n = max(2, int(np.ceil(duration * float(densify_hz))) + 1)
            t_out = np.linspace(float(t_in[0]), float(t_in[-1]), n)
            y_for_mapping = np.clip(
                np.interp(t_out, t_in, y_in), 0.0, 1.0)
        else:
            t_out = t_in.copy()
            y_for_mapping = y_in
    else:
        t_out = t_in.copy()
        y_for_mapping = y_in

    intensities = compute_spatial_intensities(
        y_for_mapping, family, params, electrode_angles_deg,
        mapping, sharpness, cycles_per_unit,
    )
    out = {}
    for key, arr in intensities.items():
        out[key] = Funscript(t_out.copy(), arr,
                             metadata=dict(main_funscript.metadata))
    return out


def get_default_config() -> Dict[str, Any]:
    """Default config block for trochoid_spatial."""
    return {
        'enabled': False,
        'family': 'hypo',
        'mapping': 'directional',
        'sharpness': 1.0,
        'cycles_per_unit': 1.0,
        'electrode_angles_deg': list(DEFAULT_ELECTRODE_ANGLES_DEG),
        'params_by_family': {
            fam: dict(spec['params'])
            for fam, spec in FAMILY_DEFAULTS.items()
        },
    }
