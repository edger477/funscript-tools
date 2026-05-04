"""
Signal analysis engine for funscript files.

Examines a funscript's characteristics (stroke rate, amplitude, speed
distribution, rest periods, etc.) and produces concrete setting
recommendations for the processing pipeline.
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from funscript import Funscript
from processing.speed_processing import add_interpolated_points, convert_to_speed


def _interpolate(fs: Funscript, interval: float = 0.02) -> Funscript:
    """Resample to a uniform grid without mutating the original."""
    copy = Funscript(np.array(fs.x, dtype=float), np.array(fs.y, dtype=float))
    return add_interpolated_points(copy, interval)


# ── Stroke Detection ─────────────────────────────────────────────────

def _find_strokes(y: np.ndarray, min_samples: int = 5) -> List[Dict]:
    """
    Find monotonic stroke segments (peak-to-valley or valley-to-peak).

    Returns list of dicts with keys:
        start_idx, end_idx, direction ('up'/'down'), amplitude
    """
    if len(y) < 3:
        return []

    diffs = np.diff(y)
    strokes = []
    seg_start = 0
    cur_sign = 1 if diffs[0] >= 0 else -1

    for i in range(1, len(diffs)):
        new_sign = 1 if diffs[i] >= 0 else -1
        if new_sign != cur_sign and new_sign != 0:
            seg_len = i - seg_start
            if seg_len >= min_samples:
                amp = abs(float(y[i]) - float(y[seg_start]))
                strokes.append({
                    'start_idx': seg_start,
                    'end_idx': i,
                    'direction': 'up' if cur_sign > 0 else 'down',
                    'amplitude': amp,
                })
            seg_start = i
            cur_sign = new_sign

    # Tail segment
    seg_len = len(y) - 1 - seg_start
    if seg_len >= min_samples:
        amp = abs(float(y[-1]) - float(y[seg_start]))
        strokes.append({
            'start_idx': seg_start,
            'end_idx': len(y) - 1,
            'direction': 'up' if cur_sign > 0 else 'down',
            'amplitude': amp,
        })

    return strokes


# ── Metric Computation ───────────────────────────────────────────────

def _compute_stroke_metrics(t: np.ndarray, y: np.ndarray) -> Dict:
    """Stroke rate, amplitude, and variability metrics."""
    strokes = _find_strokes(y)
    if not strokes:
        return {
            'stroke_count': 0,
            'median_stroke_rate_hz': 0.0,
            'stroke_rate_variability': 0.0,
            'mean_amplitude': 0.0,
            'median_amplitude': 0.0,
            'amplitude_p25': 0.0,
            'amplitude_p75': 0.0,
            'amplitudes': [],
            'strokes_per_minute': 0.0,
        }

    duration = float(t[-1] - t[0])
    stroke_count = len(strokes)
    amplitudes = np.array([s['amplitude'] for s in strokes])

    # Stroke durations → local rates
    durations = np.array([float(t[s['end_idx']] - t[s['start_idx']])
                          for s in strokes])
    durations = durations[durations > 0]
    local_rates = 1.0 / durations if len(durations) > 0 else np.array([0.0])

    median_rate = float(np.median(local_rates))
    if median_rate > 0:
        iqr = float(np.percentile(local_rates, 75) - np.percentile(local_rates, 25))
        variability = iqr / median_rate
    else:
        variability = 0.0

    return {
        'stroke_count': stroke_count,
        'median_stroke_rate_hz': median_rate,
        'stroke_rate_variability': min(variability, 3.0),
        'mean_amplitude': float(np.mean(amplitudes)),
        'median_amplitude': float(np.median(amplitudes)),
        'amplitude_p25': float(np.percentile(amplitudes, 25)),
        'amplitude_p75': float(np.percentile(amplitudes, 75)),
        'amplitudes': amplitudes.tolist(),
        'strokes_per_minute': stroke_count / max(duration / 60.0, 1e-6),
    }


def _compute_temporal_metrics(t: np.ndarray, y: np.ndarray) -> Dict:
    """Duration, rest periods, active segments."""
    duration = float(t[-1] - t[0])

    # Instantaneous speed
    dt = np.diff(t)
    dy = np.abs(np.diff(y))
    inst_speed = np.where(dt > 0, dy / dt, 0.0)
    max_speed = float(inst_speed.max()) if len(inst_speed) > 0 else 1.0

    # Rest = speed < 5% of max for > 2 seconds
    threshold = max_speed * 0.05
    is_rest = inst_speed < threshold

    # Find contiguous rest periods
    rest_periods = []
    in_rest = False
    rest_start = 0
    for i in range(len(is_rest)):
        if is_rest[i] and not in_rest:
            rest_start = i
            in_rest = True
        elif not is_rest[i] and in_rest:
            rest_dur = float(t[i] - t[rest_start])
            if rest_dur >= 2.0:
                rest_periods.append((float(t[rest_start]), float(t[i])))
            in_rest = False
    if in_rest:
        rest_dur = float(t[-1] - t[rest_start])
        if rest_dur >= 2.0:
            rest_periods.append((float(t[rest_start]), float(t[-1])))

    total_rest = sum(end - start for start, end in rest_periods)
    rest_fraction = total_rest / max(duration, 1e-6)
    active_duration = duration - total_rest

    # Active segment durations
    if rest_periods:
        active_segs = []
        prev_end = float(t[0])
        for rs, re in rest_periods:
            if rs > prev_end:
                active_segs.append(rs - prev_end)
            prev_end = re
        if float(t[-1]) > prev_end:
            active_segs.append(float(t[-1]) - prev_end)
        mean_active_seg = float(np.mean(active_segs)) if active_segs else active_duration
    else:
        mean_active_seg = active_duration

    return {
        'total_duration_s': duration,
        'active_duration_s': active_duration,
        'rest_fraction': rest_fraction,
        'rest_periods': rest_periods,
        'rest_count': len(rest_periods),
        'mean_active_segment_s': mean_active_seg,
    }


def _compute_speed_metrics(t: np.ndarray, y: np.ndarray) -> Dict:
    """Speed distribution metrics."""
    dt = np.diff(t)
    dy = np.abs(np.diff(y))
    inst_speed = np.where(dt > 0, dy / dt, 0.0)

    if len(inst_speed) == 0:
        return {
            'speed_mean': 0.0, 'speed_median': 0.0,
            'speed_p25': 0.0, 'speed_p75': 0.0, 'speed_p95': 0.0,
            'speed_max': 0.0,
        }

    return {
        'speed_mean': float(np.mean(inst_speed)),
        'speed_median': float(np.median(inst_speed)),
        'speed_p25': float(np.percentile(inst_speed, 25)),
        'speed_p75': float(np.percentile(inst_speed, 75)),
        'speed_p95': float(np.percentile(inst_speed, 95)),
        'speed_max': float(np.max(inst_speed)),
    }


def _compute_position_metrics(y: np.ndarray) -> Dict:
    """Position distribution."""
    hist, bin_edges = np.histogram(y, bins=20, range=(0.0, 1.0))
    hist_norm = hist / max(hist.sum(), 1)

    return {
        'position_mean': float(np.mean(y)),
        'position_std': float(np.std(y)),
        'position_p5': float(np.percentile(y, 5)),
        'position_p95': float(np.percentile(y, 95)),
        'position_range': float(np.percentile(y, 95) - np.percentile(y, 5)),
        'position_histogram': hist_norm.tolist(),
        'position_bin_edges': bin_edges.tolist(),
    }


def _compute_frequency_metrics(y: np.ndarray, dt: float) -> Dict:
    """FFT-based frequency content."""
    n = len(y)
    if n < 64:
        return {'high_freq_energy_ratio': 0.0, 'dominant_freq_hz': 0.0}

    # Remove mean, apply window
    windowed = (y - np.mean(y)) * np.hanning(n)
    fft_vals = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=dt)

    total_energy = float(np.sum(fft_vals ** 2))
    if total_energy < 1e-12:
        return {'high_freq_energy_ratio': 0.0, 'dominant_freq_hz': 0.0}

    # High-frequency = above 1 Hz
    high_mask = freqs > 1.0
    high_energy = float(np.sum(fft_vals[high_mask] ** 2))

    # Dominant frequency (excluding DC)
    fft_no_dc = fft_vals.copy()
    fft_no_dc[0] = 0
    dominant_idx = np.argmax(fft_no_dc)
    dominant_freq = float(freqs[dominant_idx])

    return {
        'high_freq_energy_ratio': high_energy / total_energy,
        'dominant_freq_hz': dominant_freq,
    }


# ── Classification ───────────────────────────────────────────────────

def _classify(metrics: Dict) -> Dict:
    """Produce a human-readable classification of the script."""
    spm = metrics['stroke']['strokes_per_minute']
    var = metrics['stroke']['stroke_rate_variability']
    rest = metrics['temporal']['rest_fraction']
    amp = metrics['stroke']['mean_amplitude']

    # Pace
    if spm < 30:
        pace = 'slow'
    elif spm < 80:
        pace = 'moderate'
    elif spm < 150:
        pace = 'fast'
    else:
        pace = 'very fast'

    # Variability
    if var < 0.3:
        var_label = 'steady'
    elif var < 0.8:
        var_label = 'moderate variability'
    else:
        var_label = 'highly variable'

    # Intensity
    if amp < 0.2:
        intensity = 'subtle'
    elif amp < 0.5:
        intensity = 'moderate'
    else:
        intensity = 'intense'

    parts = [pace, var_label, intensity]
    if rest > 0.2:
        parts.append(f'{rest*100:.0f}% rest')

    tag = f"{pace.upper()}, {var_label.upper()}"

    description = (
        f"{spm:.0f} strokes/min, {var_label} pacing, "
        f"{intensity} amplitude (mean {amp:.2f}). "
    )
    if rest > 0.1:
        description += f"{rest*100:.0f}% rest time. "
    description += f"Duration: {metrics['temporal']['total_duration_s']/60:.1f} min."

    return {
        'tag': tag,
        'description': description,
        'pace': pace,
        'variability': var_label,
        'intensity': intensity,
    }


# ── Recommendations ──────────────────────────────────────────────────

def _recommend(metrics: Dict) -> List[Dict]:
    """Generate setting recommendations from metrics."""
    recs = []
    stroke = metrics['stroke']
    temporal = metrics['temporal']
    speed = metrics['speed']
    freq = metrics['frequency']

    spm = stroke['strokes_per_minute']
    var = stroke['stroke_rate_variability']
    rate_hz = stroke['median_stroke_rate_hz']
    amp = stroke['mean_amplitude']
    rest_frac = temporal['rest_fraction']
    hf_ratio = freq['high_freq_energy_ratio']
    speed_p95 = speed['speed_p95']
    mean_active = temporal['mean_active_segment_s']

    # 1. Speed method
    if var > 0.8:
        method = 'savgol'
        reason = f'High stroke variability ({var:.2f}) — savgol preserves peaks'
    elif var < 0.3:
        method = 'rolling_average'
        reason = f'Steady pacing ({var:.2f}) — rolling average works well'
    else:
        method = 'ema'
        reason = f'Moderate variability ({var:.2f}) — EMA gives smooth response'
    recs.append({'setting': 'speed.method', 'value': method, 'reason': reason})

    # 2. Speed window (valid range: 1-30)
    if rate_hz > 0:
        win = 2.0 / rate_hz
    else:
        win = 3.0
    win = max(1.0, min(win, 30.0))
    if mean_active < 3.0:
        win = min(win, max(1.0, mean_active * 0.8))
    win = round(max(1.0, win), 1)
    recs.append({
        'setting': 'general.speed_window_size', 'value': win,
        'reason': f'~2 stroke cycles at {rate_hz:.2f} Hz median rate'
    })

    # 3. Accel window (valid range: 1-10)
    accel_win = round(max(1.0, min(win * 0.6, 10.0)), 1)
    recs.append({
        'setting': 'general.accel_window_size', 'value': accel_win,
        'reason': f'60% of speed window ({win}s)'
    })

    # 4. Interpolation interval
    if speed_p95 > 3.0:
        interp = 0.01
        reason = f'Fast signal (p95 speed {speed_p95:.1f}) needs dense sampling'
    elif speed_p95 < 0.5:
        interp = 0.05
        reason = f'Slow signal (p95 speed {speed_p95:.1f}) — coarser sampling OK'
    else:
        interp = 0.02
        reason = f'Moderate speed (p95 {speed_p95:.1f}) — standard density'
    recs.append({
        'setting': 'speed.interpolation_interval', 'value': interp,
        'reason': reason
    })

    # 5. Savgol options
    if method == 'savgol':
        poly = 4 if hf_ratio > 0.4 else 3
        recs.append({
            'setting': 'speed.savgol_options.poly_order', 'value': poly,
            'reason': f'HF energy ratio {hf_ratio:.2f} — '
                      + ('higher order for fast content' if poly > 3
                         else 'cubic is sufficient')
        })
        fit_factor = round(max(0.05, min(0.05 + 0.2 * (1 - var), 0.5)), 2)
        recs.append({
            'setting': 'speed.savgol_options.fit_window_factor',
            'value': fit_factor,
            'reason': f'Variability {var:.2f} — '
                      + ('tight fit for variable signal' if fit_factor < 0.15
                         else 'standard fit width')
        })
        smooth = round(max(0.0, min(0.1 + 0.3 * var, 1.0)), 2)
        recs.append({
            'setting': 'speed.savgol_options.post_smooth_factor',
            'value': smooth,
            'reason': f'Balance detail vs smoothness for variability {var:.2f}'
        })

    # 6. Rest level
    if rest_frac > 0.3:
        rest_lvl = 0.3
        reason = f'Lots of rest ({rest_frac*100:.0f}%) — low rest level for contrast'
    elif rest_frac < 0.05:
        rest_lvl = 0.5
        reason = f'Almost no rest ({rest_frac*100:.0f}%) — higher baseline'
    else:
        rest_lvl = 0.4
        reason = f'Moderate rest ({rest_frac*100:.0f}%)'
    recs.append({
        'setting': 'general.rest_level', 'value': rest_lvl,
        'reason': reason
    })

    # 7. Modulation frequency
    if rate_hz > 0:
        mod_freq = round(max(0.1, min(rate_hz * 0.3, 3.0)), 2)
    else:
        mod_freq = 0.5
    recs.append({
        'setting': 'modulation.frequency_hz', 'value': mod_freq,
        'reason': f'Sub-harmonic of {rate_hz:.2f} Hz stroke rate'
    })

    # 8. Modulation depth
    if amp < 0.3:
        mod_depth = 0.25
        reason = f'Small strokes (amp {amp:.2f}) — more modulation texture'
    elif amp > 0.7:
        mod_depth = 0.08
        reason = f'Big strokes (amp {amp:.2f}) — less modulation needed'
    else:
        mod_depth = 0.15
        reason = f'Moderate strokes (amp {amp:.2f}) — standard depth'
    recs.append({
        'setting': 'modulation.depth', 'value': mod_depth,
        'reason': reason
    })

    # 9. Physical model speed
    phys_speed = round(max(100, min(200 + 200 * rate_hz, 1000)))
    recs.append({
        'setting': 'physical_model.propagation_speed_mm_s',
        'value': phys_speed,
        'reason': f'Scaled to {rate_hz:.2f} Hz stroke rate — '
                  f'sweep completes within one stroke'
    })

    # 10. Sweep direction
    if var > 0.5:
        sweep = 'signal_direction'
        reason = f'Variable pacing ({var:.2f}) — direction-following adds expressiveness'
    else:
        sweep = 'e1_to_e4'
        reason = f'Steady pacing ({var:.2f}) — fixed sweep is cleaner'
    recs.append({
        'setting': 'physical_model.sweep_direction',
        'value': sweep,
        'reason': reason
    })

    return recs


# ── Public API ───────────────────────────────────────────────────────

def analyze_funscript(fs: Funscript) -> Dict[str, Any]:
    """
    Analyze a funscript and return metrics, classification, and
    setting recommendations.

    Args:
        fs: Source funscript.

    Returns:
        Dict with keys 'metrics', 'classification', 'recommendations'.
    """
    # Interpolate to uniform grid
    interp_fs = _interpolate(fs, 0.02)
    t = np.asarray(interp_fs.x, dtype=float)
    y = np.asarray(interp_fs.y, dtype=float)
    dt = 0.02

    metrics = {
        'stroke': _compute_stroke_metrics(t, y),
        'temporal': _compute_temporal_metrics(t, y),
        'speed': _compute_speed_metrics(t, y),
        'position': _compute_position_metrics(y),
        'frequency': _compute_frequency_metrics(y, dt),
    }

    classification = _classify(metrics)
    recommendations = _recommend(metrics)

    return {
        'metrics': metrics,
        'classification': classification,
        'recommendations': recommendations,
    }
