"""
Curve-based Quantization

Snap each y-value of a funscript to one of N levels derived from points
sampled around a parametric curve. Several curve families are supported,
plus a sandboxed custom-expression mode.

Curve families:
    hypo         hypotrochoid             params: R, r, d
    epi          epitrochoid              params: R, r, d
    rose         rose curve r=a*cos(k*t)  params: a, k
    lissajous    Lissajous figure         params: A, B, a, b, delta
    butterfly    Fay's butterfly curve    params: scale
    superformula Gielis superformula      params: a, b, m, n1, n2, n3
    custom       user-entered x(t), y(t)  params: x_expr, y_expr

Hypotrochoid — rolling circle rolls INSIDE the fixed circle:
    x(t) = (R - r) cos(t) + d cos(((R - r) / r) t)
    y(t) = (R - r) sin(t) - d sin(((R - r) / r) t)

Epitrochoid — rolling circle rolls OUTSIDE the fixed circle:
    x(t) = (R + r) cos(t) - d cos(((R + r) / r) t)
    y(t) = (R + r) sin(t) - d sin(((R + r) / r) t)

We sample N points evenly in t over the family's natural period, project
to a single scalar (radius / x / y), normalize the resulting values to
[0, 1], and use those as quantization levels. Every point in the input
signal is then snapped to the nearest level.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, Any

import numpy as np

sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


VALID_PROJECTIONS = ('radius', 'y', 'x')
VALID_CURVE_TYPES = ('hypo', 'epi')  # legacy alias for trochoid_xy
CURVE_FAMILIES = (
    'hypo', 'epi', 'rose', 'lissajous',
    'butterfly', 'superformula', 'custom',
)


# -----------------------------------------------------------------------------
# Family default parameter sets and natural sampling ranges.
# theta_max is in units of pi (so 2 means [0, 2*pi)). Some families need a
# longer parameter range than 2*pi to trace the full curve once (butterfly).
# -----------------------------------------------------------------------------

FAMILY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'hypo': {
        'description': 'Hypotrochoid — rolling circle inside a fixed circle.',
        'params': {'R': 5.0, 'r': 3.0, 'd': 2.0},
        'theta_max_pi': 2.0,
    },
    'epi': {
        'description': 'Epitrochoid — rolling circle outside a fixed circle.',
        'params': {'R': 5.0, 'r': 3.0, 'd': 2.0},
        'theta_max_pi': 2.0,
    },
    'rose': {
        'description': 'Rose curve r = a*cos(k*theta). Petals = k if odd, 2k if even.',
        'params': {'a': 1.0, 'k': 5.0},
        'theta_max_pi': 2.0,
    },
    'lissajous': {
        'description': 'Lissajous figure x=A sin(a*t+delta), y=B sin(b*t).',
        'params': {'A': 1.0, 'B': 1.0, 'a': 3.0, 'b': 2.0, 'delta': 1.5708},
        'theta_max_pi': 2.0,
    },
    'butterfly': {
        'description': "Temple Fay's butterfly curve.",
        'params': {'scale': 1.0},
        'theta_max_pi': 12.0,  # full butterfly traced over [0, 12*pi)
    },
    'superformula': {
        'description': 'Gielis superformula — flexible organic shapes.',
        'params': {'a': 1.0, 'b': 1.0, 'm': 6.0,
                   'n1': 1.0, 'n2': 7.0, 'n3': 8.0},
        'theta_max_pi': 2.0,
    },
    'custom': {
        'description': 'User-entered x(t) and y(t). t ranges over [0, 2*pi).',
        'params': {'x_expr': 'sin(3*t)', 'y_expr': 'cos(2*t)'},
        'theta_max_pi': 2.0,
    },
}


def list_curve_families() -> Dict[str, Dict[str, Any]]:
    """Return a copy of FAMILY_DEFAULTS for UI consumption."""
    out = {}
    for name, spec in FAMILY_DEFAULTS.items():
        out[name] = {
            'description': spec['description'],
            'params': dict(spec['params']),
            'theta_max_pi': spec['theta_max_pi'],
        }
    return out


# -----------------------------------------------------------------------------
# Sandboxed evaluator for custom x(t)/y(t) expressions.
#
# We build a restricted namespace containing only numpy math primitives and
# the parameter `t`. Compiled bytecode is evaluated with empty __builtins__
# so user expressions cannot import modules, open files, or access object
# internals. We additionally reject source containing the dunder token
# "__" to block obvious attribute-traversal attacks at the source level.
# -----------------------------------------------------------------------------

_SAFE_NS_BASE: Dict[str, Any] = {
    'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
    'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
    'atan2': np.arctan2,
    'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
    'exp': np.exp, 'log': np.log, 'log2': np.log2, 'log10': np.log10,
    'sqrt': np.sqrt, 'cbrt': np.cbrt,
    'abs': np.abs, 'sign': np.sign,
    'floor': np.floor, 'ceil': np.ceil, 'round': np.round,
    'minimum': np.minimum, 'maximum': np.maximum,
    'pi': float(np.pi), 'e': float(np.e), 'tau': 2.0 * float(np.pi),
    'pow': np.power,
}


def evaluate_custom_expression(expr: str, t: np.ndarray) -> np.ndarray:
    """Evaluate a custom expression in a restricted numpy namespace."""
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("expression must be a non-empty string")
    if '__' in expr:
        raise ValueError("expression contains forbidden token '__'")
    code = compile(expr, '<custom_curve>', 'eval')
    ns = dict(_SAFE_NS_BASE)
    ns['t'] = t
    result = eval(code, {'__builtins__': {}}, ns)  # noqa: S307
    arr = np.asarray(result, dtype=float)
    if arr.shape == ():
        arr = np.broadcast_to(arr, t.shape).copy()
    return arr


# -----------------------------------------------------------------------------
# Family evaluators. Each returns (x, y) numpy arrays for the given theta.
# -----------------------------------------------------------------------------

def _eval_hypo(theta, R, r, d):
    if r == 0:
        raise ValueError("r must be non-zero")
    a = R - r
    k = a / r
    x = a * np.cos(theta) + d * np.cos(k * theta)
    y = a * np.sin(theta) - d * np.sin(k * theta)
    return x, y


def _eval_epi(theta, R, r, d):
    if r == 0:
        raise ValueError("r must be non-zero")
    a = R + r
    k = a / r
    x = a * np.cos(theta) - d * np.cos(k * theta)
    y = a * np.sin(theta) - d * np.sin(k * theta)
    return x, y


def _eval_rose(theta, a, k):
    r_t = a * np.cos(k * theta)
    x = r_t * np.cos(theta)
    y = r_t * np.sin(theta)
    return x, y


def _eval_lissajous(theta, A, B, a, b, delta):
    x = A * np.sin(a * theta + delta)
    y = B * np.sin(b * theta)
    return x, y


def _eval_butterfly(theta, scale):
    # Fay (1989): r = e^cos(t) - 2*cos(4t) + sin^5(t/12)
    r_t = np.exp(np.cos(theta)) - 2.0 * np.cos(4.0 * theta) + np.sin(theta / 12.0) ** 5
    x = scale * r_t * np.sin(theta)
    y = scale * r_t * np.cos(theta)
    return x, y


def _eval_superformula(theta, a, b, m, n1, n2, n3):
    if a == 0 or b == 0 or n1 == 0:
        raise ValueError("superformula requires non-zero a, b, n1")
    p1 = np.abs(np.cos(m * theta / 4.0) / a) ** n2
    p2 = np.abs(np.sin(m * theta / 4.0) / b) ** n3
    r_t = (p1 + p2) ** (-1.0 / n1)
    x = r_t * np.cos(theta)
    y = r_t * np.sin(theta)
    return x, y


def _eval_custom(theta, x_expr, y_expr):
    x = evaluate_custom_expression(x_expr, theta)
    y = evaluate_custom_expression(y_expr, theta)
    return x, y


_FAMILY_EVALUATORS = {
    'hypo': _eval_hypo,
    'epi': _eval_epi,
    'rose': _eval_rose,
    'lissajous': _eval_lissajous,
    'butterfly': _eval_butterfly,
    'superformula': _eval_superformula,
    'custom': _eval_custom,
}


def _coerce_params(family: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce params from config (which may store strings) to call-ready types."""
    spec = FAMILY_DEFAULTS.get(family)
    if not spec:
        raise ValueError(f"unknown curve family: {family!r}")
    out = {}
    for k, default_v in spec['params'].items():
        v = params.get(k, default_v) if params else default_v
        if isinstance(default_v, str):
            out[k] = str(v)
        else:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = float(default_v)
    return out


def curve_xy(
    theta: np.ndarray,
    family: str,
    params: Dict[str, Any],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Evaluate a parametric curve from the requested family.

    Args:
        theta: parameter values in radians.
        family: one of CURVE_FAMILIES.
        params: family-specific parameter dict.

    Returns:
        (x, y) numpy arrays.
    """
    if family not in _FAMILY_EVALUATORS:
        raise ValueError(
            f"family must be one of {CURVE_FAMILIES}, got {family!r}")
    p = _coerce_params(family, params or {})
    return _FAMILY_EVALUATORS[family](theta, **p)


def get_family_theta_max(family: str) -> float:
    """Return the natural theta upper bound (in radians) for a family."""
    spec = FAMILY_DEFAULTS.get(family)
    if not spec:
        raise ValueError(f"unknown curve family: {family!r}")
    return float(spec['theta_max_pi']) * float(np.pi)


def generate_curve_levels(
    n_points: int,
    family: str,
    params: Dict[str, Any],
    projection: str = 'radius',
) -> np.ndarray:
    """
    Sample N points around a curve and project to N normalized levels.

    Args:
        n_points: Number of quantization levels (>= 2). Typical: 15, 17, 23.
        family: one of CURVE_FAMILIES.
        params: family-specific parameter dict.
        projection: 'radius' (sqrt(x^2+y^2)), 'y' (y-coord), or 'x' (x-coord).

    Returns:
        Sorted ascending numpy array of values in [0, 1] (length <= n_points
        after de-duplication).
    """
    if n_points < 2:
        raise ValueError("n_points must be >= 2")
    if projection not in VALID_PROJECTIONS:
        raise ValueError(
            f"projection must be one of {VALID_PROJECTIONS}, got {projection!r}")

    theta_max = get_family_theta_max(family)
    theta = np.linspace(0.0, theta_max, n_points, endpoint=False)
    x, y = curve_xy(theta, family, params)

    if projection == 'radius':
        vals = np.sqrt(x * x + y * y)
    elif projection == 'y':
        vals = y
    else:
        vals = x

    # Drop NaN / inf samples from degenerate evaluations.
    finite = np.isfinite(vals)
    if not np.all(finite):
        vals = vals[finite]
    if vals.size < 2:
        return np.linspace(0.0, 1.0, n_points)

    vmin = float(vals.min())
    vmax = float(vals.max())
    if vmax - vmin < 1e-12:
        return np.linspace(0.0, 1.0, n_points)

    levels = (vals - vmin) / (vmax - vmin)
    levels = np.unique(levels)
    return levels


def quantize_to_curve(
    funscript: Funscript,
    n_points: int,
    family: str,
    params: Dict[str, Any],
    projection: str = 'radius',
) -> Funscript:
    """
    Snap each position value to the nearest curve-derived level.
    """
    levels = generate_curve_levels(n_points, family, params, projection)
    y = np.asarray(funscript.y, dtype=float)
    idx = np.searchsorted(levels, y)
    idx = np.clip(idx, 1, len(levels) - 1)
    left = levels[idx - 1]
    right = levels[idx]
    snapped = np.where(np.abs(y - left) <= np.abs(y - right), left, right)
    return Funscript(funscript.x.copy(), snapped,
                     metadata=dict(funscript.metadata))


def deduplicate_holds(funscript: Funscript, atol: float = 1e-9) -> Funscript:
    """
    Drop redundant interior samples in runs of identical positions.

    For each run of consecutive samples with the same value, keep only the
    first and the last sample of the run. The first preserves the start of
    the hold; the last preserves the duration of the hold so the device's
    linear interpolation does not slope across the held window.

    A signal whose values are all distinct is returned unchanged.
    """
    t = np.asarray(funscript.x, dtype=float)
    y = np.asarray(funscript.y, dtype=float)
    n = len(y)
    if n <= 2:
        return Funscript(t.copy(), y.copy(),
                         metadata=dict(funscript.metadata))
    diffs = np.abs(np.diff(y)) > atol
    keep = np.zeros(n, dtype=bool)
    keep[0] = True
    keep[-1] = True
    keep[:-1] |= diffs   # last sample before a value change
    keep[1:] |= diffs    # first sample after a value change
    return Funscript(t[keep], y[keep], metadata=dict(funscript.metadata))


# -----------------------------------------------------------------------------
# Backward-compatible API for the original trochoid-only callers.
# -----------------------------------------------------------------------------

def trochoid_xy(theta, R, r, d, curve_type='hypo'):
    """Legacy entry-point: hypo/epi only."""
    return curve_xy(theta, curve_type, {'R': R, 'r': r, 'd': d})


def generate_trochoid_levels(n_points, R, r, d,
                              projection='radius', curve_type='hypo'):
    """Legacy entry-point: hypo/epi only."""
    return generate_curve_levels(
        n_points, curve_type, {'R': R, 'r': r, 'd': d}, projection)


def quantize_to_trochoid(funscript, n_points, R, r, d,
                          projection='radius', curve_type='hypo'):
    """Legacy entry-point: hypo/epi only."""
    return quantize_to_curve(
        funscript, n_points, curve_type, {'R': R, 'r': r, 'd': d}, projection)
