import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def add_interpolated_points(funscript_data, interval=0.1):
    """
    Interpolate funscript so that there's one value every interval seconds.
    """
    if len(funscript_data.x) < 2:
        raise ValueError("Need at least two points to interpolate.")

    x = np.array(funscript_data.x)
    y = np.array(funscript_data.y)

    start = int(x[0])
    end = int(x[-1])

    # Generate timestamps every interval seconds
    target_x = np.arange(start, end + 1, interval)

    # Interpolate positions at those timestamps
    interp_y = np.interp(target_x, x, y)

    # Update the funscript data
    funscript_data.x = target_x.tolist()
    funscript_data.y = interp_y.tolist()

    return funscript_data


# ── Method 1: Rolling Average (original) ────────────────────────────

def calculate_speed_windowed(funscript, window_seconds=5):
    """Calculate the rolling average speed of change over the last n seconds."""
    x = []
    y = []
    max_speed = 0
    time_window = window_seconds
    shift = int(time_window * 5)  # 5 points per second after interpolation

    # Start with zero speed
    x.append(funscript.x[0])
    y.append(0)

    for i in range(1 + shift, len(funscript.x)):
        current_time = funscript.x[i]

        # Initialize variables for rolling sum
        total_speed = 0
        count = 0

        # Look back at all points within the last n seconds
        for j in range(i, -1, -1):
            if current_time - funscript.x[j] > time_window:
                break  # Stop if we're outside the n-second window

            if j == 0:
                break

            time_diff = funscript.x[j] - funscript.x[j-1]  # Time difference in seconds
            pos_diff = abs(funscript.y[j] - funscript.y[j-1])  # Absolute position change

            # Avoid division by zero if time_diff is zero
            if time_diff != 0:
                speed = pos_diff / time_diff  # Speed (change per second)
                total_speed += speed
                count += 1

        # Calculate the average speed over the rolling window
        avg_speed = (total_speed / count) if count > 0 else 0

        if avg_speed > max_speed:
            max_speed = avg_speed

        # Append with shift compensation
        x.append(funscript.x[i-shift])
        y.append(avg_speed)

    # Add final point with zero speed
    x.append(funscript.x[len(funscript.x)-1])
    y.append(0)

    # Normalize to 0-1 range
    if max_speed > 0:
        factor = 1 / max_speed
        for i in range(len(y)):
            y[i] = y[i] * factor

    return Funscript(x, y)


# ── Method 2: Exponential Moving Average (EMA) ──────────────────────

def calculate_speed_ema(funscript, half_life_seconds=2.0):
    """
    EMA-smoothed absolute speed.

    Instead of a hard rectangular window, recent samples are weighted
    exponentially more than old ones.  The half_life_seconds parameter
    controls the decay: after half_life seconds, a past speed sample's
    influence has dropped to 50%.

    Compared to the rolling-average method this is:
      - O(n) instead of O(n²)
      - Smoother (no "box-car" artifacts when old data drops out)
      - Zero-lag at the trailing edge (soft decay, no hard cutoff)
    """
    x = np.asarray(funscript.x, dtype=float)
    y = np.asarray(funscript.y, dtype=float)

    if len(x) < 2:
        return Funscript(np.array([x[0]]), np.array([0.0]))

    # Per-sample instantaneous absolute speed
    dt = np.diff(x)
    dy = np.abs(np.diff(y))
    inst_speed = np.where(dt > 0, dy / dt, 0.0)

    # Time constant τ = half_life / ln(2)
    tau = max(half_life_seconds, 1e-6) / np.log(2.0)

    # Single-pass EMA with variable-step alpha
    ema = np.empty_like(inst_speed)
    ema[0] = inst_speed[0]
    for i in range(1, len(inst_speed)):
        alpha = 1.0 - np.exp(-dt[i] / tau)
        ema[i] = alpha * inst_speed[i] + (1.0 - alpha) * ema[i - 1]

    # Normalize to [0, 1]
    max_val = ema.max()
    if max_val > 0:
        ema /= max_val

    # Output timestamps aligned to the later sample of each pair
    out_x = x[1:]
    return Funscript(out_x, ema)


# ── Method 3: Savitzky-Golay derivative ─────────────────────────────

def calculate_speed_savgol(funscript, window_seconds=2.0,
                           poly_order=3,
                           fit_window_factor=0.15,
                           post_smooth_factor=0.25):
    """
    Speed via Savitzky-Golay polynomial-fit 1st derivative.

    Fits a local polynomial to the position data and takes its
    analytical derivative.  This gives a smooth speed estimate that
    preserves peaks better than averaging — the polynomial tracks the
    shape of the stroke rather than flattening it.

    Falls back to the EMA method if scipy is not installed.

    The user-facing window_seconds is mapped to a savgol fit window
    that produces comparable smoothing to the rolling-average method
    at the same setting.  The rolling average sums speeds across the
    full window, preserving amplitude even for oscillations inside it.
    A savgol polynomial, by contrast, would flatten those oscillations
    entirely if given the same raw width.  So we use a shorter fit
    window (≈ window_seconds × fit_window_factor, minimum 5 samples)
    and then smooth the raw derivative with EMA at the full window
    scale.  This two-stage approach gives savgol's peak-preserving
    precision with the same temporal "feel" as the other methods.

    Args:
        funscript: Interpolated Funscript.
        window_seconds: Overall smoothing scale (seconds).
        poly_order: Polynomial order for the savgol fit (2-5).
            Lower = smoother but rounds peaks. Higher = sharper but
            amplifies noise.  3 (cubic) is the standard default.
        fit_window_factor: Fraction of window_seconds used for the
            polynomial fit (0.05-0.5).  Smaller = more reactive,
            tracks faster oscillations.  Larger = broader fit, more
            smoothing.
        post_smooth_factor: EMA post-smoothing strength as a fraction
            of window_seconds (0.0-1.0).  0 = no post-smoothing
            (raw savgol derivative).  Larger = more smoothing on
            top of the derivative.
    """
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        print("Warning: scipy not installed, falling back to EMA for speed calculation")
        return calculate_speed_ema(funscript, half_life_seconds=window_seconds)

    x = np.asarray(funscript.x, dtype=float)
    y = np.asarray(funscript.y, dtype=float)

    if len(x) < 5:
        return Funscript(x.copy(), np.zeros_like(y))

    dt = float(np.median(np.diff(x)))
    if dt <= 0:
        dt = 1e-3

    # Clamp parameters to sane ranges
    poly_order = max(2, min(int(poly_order), 5))
    fit_window_factor = max(0.05, min(float(fit_window_factor), 0.5))
    post_smooth_factor = max(0.0, min(float(post_smooth_factor), 1.0))

    # Short fit window: captures local stroke shape without smearing
    # multiple full oscillation cycles.
    fit_seconds = max(window_seconds * fit_window_factor, 5 * dt)
    window_samples = int(round(fit_seconds / dt))
    window_samples = max(window_samples, 5)
    if window_samples % 2 == 0:
        window_samples += 1
    if window_samples > len(x):
        window_samples = len(x) if len(x) % 2 == 1 else len(x) - 1
    if window_samples < 5:
        window_samples = 5

    # Ensure poly_order < window_samples
    effective_order = min(poly_order, window_samples - 1)

    # 1st derivative → absolute velocity
    raw_speed = np.abs(savgol_filter(y, window_samples, effective_order, deriv=1, delta=dt))

    # Post-smoothing with EMA. When post_smooth_factor is 0, skip entirely.
    if post_smooth_factor > 0.001:
        tau = max(window_seconds * post_smooth_factor, 1e-6) / np.log(2.0)
        smoothed = np.empty_like(raw_speed)
        smoothed[0] = raw_speed[0]
        for i in range(1, len(raw_speed)):
            alpha = 1.0 - np.exp(-dt / tau)
            smoothed[i] = alpha * raw_speed[i] + (1.0 - alpha) * smoothed[i - 1]
    else:
        smoothed = raw_speed

    # Normalize to [0, 1]
    max_val = smoothed.max()
    if max_val > 0:
        smoothed /= max_val

    return Funscript(x.copy(), smoothed)


# ── Public entry point ───────────────────────────────────────────────

def convert_to_speed(funscript, window_seconds=5, interpolation_interval=0.1,
                     method='rolling_average', savgol_options=None):
    """
    Convert a funscript to speed representation.

    Args:
        funscript: Source Funscript (position vs time).
        window_seconds: For rolling_average: backward-looking window in sec.
            For ema: half-life in sec.  For savgol: polynomial fit window in sec.
        interpolation_interval: Resampling density (seconds between points).
        method: 'rolling_average' (original), 'ema', or 'savgol'.
        savgol_options: Optional dict with savgol-specific params:
            poly_order (int 2-5, default 3),
            fit_window_factor (float 0.05-0.5, default 0.15),
            post_smooth_factor (float 0.0-1.0, default 0.25).

    Returns:
        Funscript with speed values normalized to [0, 1].
    """
    # Make a copy to avoid modifying the original
    fs_copy = funscript.copy()

    # Resample to uniform grid
    fs_copy = add_interpolated_points(fs_copy, interpolation_interval)

    if method == 'ema':
        return calculate_speed_ema(fs_copy, half_life_seconds=window_seconds)
    elif method == 'savgol':
        opts = savgol_options if isinstance(savgol_options, dict) else {}
        return calculate_speed_savgol(
            fs_copy,
            window_seconds=window_seconds,
            poly_order=opts.get('poly_order', 3),
            fit_window_factor=opts.get('fit_window_factor', 0.15),
            post_smooth_factor=opts.get('post_smooth_factor', 0.25),
        )
    else:
        # Default: original rolling average
        return calculate_speed_windowed(fs_copy, window_seconds)
