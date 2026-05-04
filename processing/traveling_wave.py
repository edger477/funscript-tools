"""
Traveling-Wave Electrode Driver.

Generates per-electrode intensity tracks by running a "wave crest"
along the shaft at a configurable speed. Each electrode fires when the
crest is near its configured shaft position.

Unlike the position-driven mappings (response curves, trochoid-spatial,
axial-trochoid), the wave advances on its OWN clock — time-driven
rather than position-driven. The input signal modulates the wave's
envelope (and optionally its speed), so strokes still matter, but the
moving-sensation comes from the wave itself.

The wave crest is a triangular kernel of width `wave_width` along the
shaft. For each electrode at position p_i ∈ [0, 1]:

    intensity_i(t) = envelope(t) · max(0, 1 − |crest_pos(t) − p_i| / wave_width)

Direction options for crest_pos(t):

    one_way_up       crest moves base→tip at constant wave_speed Hz
                     (0→1, wrap at 1)
    one_way_down     same but tip→base (1→0)
    bounce           crest runs back and forth between base and tip
    signal_direction crest moves base→tip during up-strokes, tip→base
                     during down-strokes (direction flips with the
                     sign of the input's derivative)
    signal_position  crest IS the signal — crest_pos(t) = y(t). The
                     pen rides directly on the input funscript. No
                     self-clocking; wave_speed_hz and speed_mod are
                     ignored. Tightest funscript sync available.

Envelope modes:

    constant     amplitude always 1 (pure wave regardless of input)
    input        amplitude = input position (y ∈ [0, 1])
    input_speed  amplitude = |dy/dt| normalized to its 95th percentile
    abs_center   amplitude = 2 · |y − 0.5| (0 at mid, 1 at extremes)

Speed modulation (optional):
    effective_speed(t) = wave_speed · (1 + speed_mod · (y(t) − 0.5))
    so a speed_mod of 1.0 makes the wave go half-speed at input=0 and
    1.5x-speed at input=1. speed_mod=0 disables modulation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


VALID_DIRECTIONS = ('one_way_up', 'one_way_down',
                    'bounce', 'signal_direction',
                    'signal_position')
VALID_ENVELOPES = ('constant', 'input', 'input_speed', 'abs_center')


def _central_diff(t: np.ndarray, y: np.ndarray, window_s: float) -> np.ndarray:
    """Symmetric central-difference derivative."""
    n = len(y)
    if n < 3:
        return np.zeros(n)
    dt_med = float(np.median(np.diff(t)))
    if dt_med <= 0:
        dt_med = 1e-3
    half = max(1, int(round((window_s / 2.0) / dt_med)))
    idx = np.arange(n)
    lo = np.clip(idx - half, 0, n - 1)
    hi = np.clip(idx + half, 0, n - 1)
    dy = y[hi] - y[lo]
    dt = t[hi] - t[lo]
    dt = np.where(dt <= 0, dt_med, dt)
    return dy / dt


def _crest_positions(
    t: np.ndarray,
    y: np.ndarray,
    wave_speed_hz: float,
    direction: str,
    speed_mod: float,
) -> np.ndarray:
    """Compute the wave-crest position at each time sample (in [0, 1])."""
    n = len(t)
    if n == 0:
        return np.zeros(0)

    # Signal-position mode: the crest IS the input signal. No
    # self-clocking, no wrapping — the pen sits exactly at y(t), so
    # wave_speed_hz and speed_mod are ignored here. This is the tightest
    # funscript sync available and matches the Trochoid Viewer shadow
    # behavior.
    if direction == 'signal_position':
        return np.clip(np.asarray(y, dtype=float), 0.0, 1.0)

    # Per-sample instantaneous speed after modulation. Input y ∈ [0, 1].
    if speed_mod != 0.0:
        spd = wave_speed_hz * (1.0 + float(speed_mod) * (y - 0.5))
        spd = np.maximum(spd, 0.0)  # never negative; direction handled below
    else:
        spd = np.full(n, float(wave_speed_hz), dtype=float)

    # Direction sign per sample.
    if direction == 'one_way_up':
        sgn = np.ones(n)
    elif direction == 'one_way_down':
        sgn = -np.ones(n)
    elif direction == 'bounce':
        # For bounce the phase accumulates forward, then we fold it with
        # a triangle wave — direction is implicit in the fold.
        sgn = np.ones(n)
    elif direction == 'signal_direction':
        # Smooth derivative → sign per sample. Flat runs carry previous.
        dy = _central_diff(t, y, 0.08)
        raw = np.sign(dy)
        # Carry zeros forward
        last = 1.0
        for i in range(n):
            if raw[i] == 0:
                raw[i] = last
            else:
                last = raw[i]
        sgn = raw
    else:
        sgn = np.ones(n)

    # Integrate signed speed over time to get accumulated phase (shaft-lengths).
    if n >= 2:
        dt = np.diff(t, prepend=t[0])
    else:
        dt = np.zeros(n)
    phase = np.cumsum(sgn * spd * dt)

    if direction == 'bounce':
        # Fold phase ∈ ℝ into a triangle on [0, 1]:
        folded = np.mod(phase, 2.0)
        return 1.0 - np.abs(folded - 1.0)
    else:
        # For one_way_* and signal_direction: wrap into [0, 1].
        return np.mod(phase, 1.0)


def _envelope(
    t: np.ndarray,
    y: np.ndarray,
    mode: str,
    velocity_window_s: float = 0.10,
) -> np.ndarray:
    """Return a 0..1 amplitude envelope per sample."""
    n = len(y)
    if n == 0:
        return np.zeros(0)
    if mode == 'constant':
        return np.ones(n)
    if mode == 'input':
        return np.clip(y, 0.0, 1.0)
    if mode == 'abs_center':
        return np.clip(2.0 * np.abs(y - 0.5), 0.0, 1.0)
    if mode == 'input_speed':
        v = np.abs(_central_diff(t, y, velocity_window_s))
        p95 = float(np.percentile(v, 95)) if np.any(v) else 1.0
        p95 = max(p95, 1e-6)
        return np.clip(v / p95, 0.0, 1.0)
    # Unknown → constant
    return np.ones(n)


def compute_wave_intensities(
    funscript: Funscript,
    electrode_positions: Tuple[float, float, float, float] = (
        0.85, 0.65, 0.45, 0.25),
    wave_speed_hz: float = 1.0,
    wave_width: float = 0.18,
    direction: str = 'bounce',
    envelope_mode: str = 'input',
    speed_mod: float = 0.0,
    sharpness: float = 1.0,
    velocity_window_s: float = 0.10,
    noise_gate: float = 0.0,
    exclusive: bool = False,
) -> Dict[str, np.ndarray]:
    """
    Compute per-electrode intensity arrays from a traveling wave.

    Args:
        funscript: Main signal providing time and input y.
        electrode_positions: Four positions along the shaft in [0, 1].
        wave_speed_hz: Full-shaft traversals per second (crest speed).
        wave_width: Half-width of the triangular kernel in shaft units.
            Smaller = sharper peak; larger = broader overlap.
        direction: One of VALID_DIRECTIONS.
        envelope_mode: One of VALID_ENVELOPES.
        speed_mod: How much the input modulates wave speed. 0 = no mod.
        sharpness: Exponent applied to the triangular kernel. 1 = linear.
        velocity_window_s: Window for speed-based envelope/direction.
        noise_gate: Threshold in [0, 0.5]. Any intensity <= gate is
            zeroed; values above are rescaled so the output still
            reaches 1.0 at full kernel. 0.0 disables the gate; 0.10
            is a good "kill the fuzz" default; ~0.25 gives crisp
            on/off behavior. This is the lowest-effort way to drop
            the noise floor without re-tuning width/sharpness.
        exclusive: When True, only the electrode with the highest
            intensity at each sample is kept; the rest are zeroed.
            Winner-take-all. Useful for crisp "one electrode at a
            time" feel, especially with signal_position direction.

    Returns:
        Dict {'e1': array, 'e2': array, 'e3': array, 'e4': array}.
    """
    t = np.asarray(funscript.x, dtype=float)
    y = np.clip(np.asarray(funscript.y, dtype=float), 0.0, 1.0)
    n = len(t)
    if n == 0:
        return {k: np.zeros(0) for k in ('e1', 'e2', 'e3', 'e4')}
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be one of {VALID_DIRECTIONS}, got {direction!r}")
    if envelope_mode not in VALID_ENVELOPES:
        raise ValueError(
            f"envelope_mode must be one of {VALID_ENVELOPES}, got "
            f"{envelope_mode!r}")

    crest = _crest_positions(t, y, wave_speed_hz, direction, speed_mod)
    env = _envelope(t, y, envelope_mode, velocity_window_s)

    width = max(1e-3, float(wave_width))
    sharp = max(0.01, float(sharpness))
    gate = max(0.0, min(0.95, float(noise_gate)))

    out: Dict[str, np.ndarray] = {}
    for i, axis in enumerate(('e1', 'e2', 'e3', 'e4')):
        pos = float(electrode_positions[i])
        # Triangular kernel, then envelope, then optional sharpness.
        d = np.abs(crest - pos)
        kernel = np.clip(1.0 - d / width, 0.0, 1.0) ** sharp
        out[axis] = np.clip(env * kernel, 0.0, 1.0)

    # Winner-take-all: for each sample, keep only the strongest axis.
    if exclusive and n > 0:
        stack = np.stack([out['e1'], out['e2'], out['e3'], out['e4']],
                         axis=0)  # shape (4, n)
        winner = np.argmax(stack, axis=0)
        for i, axis in enumerate(('e1', 'e2', 'e3', 'e4')):
            out[axis] = np.where(winner == i, out[axis], 0.0)

    # Noise gate: soft-threshold each axis. Values <= gate map to 0;
    # the remaining [gate, 1] range is rescaled to [0, 1] so peaks
    # still hit full amplitude and the on/off edges remain crisp.
    if gate > 0.0:
        denom = max(1e-6, 1.0 - gate)
        for axis in ('e1', 'e2', 'e3', 'e4'):
            v = out[axis]
            out[axis] = np.clip((v - gate) / denom, 0.0, 1.0)
    return out


def generate_wave_funscripts(
    funscript: Funscript,
    electrode_positions: Tuple[float, float, float, float] = (
        0.85, 0.65, 0.45, 0.25),
    densify_hz: float = 60.0,
    **kwargs,
) -> Dict[str, Funscript]:
    """Build per-electrode Funscript outputs from a traveling wave.

    When `densify_hz > 0`, the input is linearly resampled to that rate
    before the wave dynamics are computed so high-frequency crest
    motion is actually captured in the saved output files. A typical
    funscript has 15-30 points/sec, which would otherwise alias away
    most of a 1 Hz+ crest traveling at 0.18 shaft-width. Setting
    densify_hz = 0 disables the resample and falls back to the input's
    native timestamps.
    """
    t_in = np.asarray(funscript.x, dtype=float)
    y_in = np.asarray(funscript.y, dtype=float)
    if len(t_in) >= 2 and float(densify_hz) > 0.0:
        duration = float(t_in[-1] - t_in[0])
        if duration > 0.0:
            n = max(2, int(np.ceil(duration * float(densify_hz))) + 1)
            t_dense = np.linspace(float(t_in[0]), float(t_in[-1]), n)
            y_dense = np.clip(np.interp(t_dense, t_in, y_in), 0.0, 1.0)
            source_fs = Funscript(
                t_dense, y_dense, metadata=dict(funscript.metadata))
        else:
            source_fs = funscript
    else:
        source_fs = funscript
    intensities = compute_wave_intensities(
        source_fs, electrode_positions=electrode_positions, **kwargs)
    out = {}
    for key, arr in intensities.items():
        out[key] = Funscript(
            source_fs.x.copy(), arr,
            metadata=dict(source_fs.metadata))
    return out


def get_default_config() -> Dict:
    """Default config block for traveling_wave."""
    return {
        'enabled': False,
        'wave_speed_hz': 1.0,
        'wave_width': 0.18,
        'direction': 'bounce',
        'envelope_mode': 'input',
        'speed_mod': 0.0,
        'sharpness': 1.0,
    }
