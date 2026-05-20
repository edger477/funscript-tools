## What's New in v2.4.3

### Performance Improvements

1. **Vectorized speed calculation** (`calculate_speed_windowed`) — replaced the O(n²) double loop with a cumulative-sum rolling window; O(n) time regardless of window size or funscript length.

2. **Vectorized ramp-up transitions** (`combine_funscripts`) — replaced the O(n × M) per-point nearest-transition search with a sorted `searchsorted` pass; O(n log M) where M is the number of rest→active transitions.

3. **Vectorized response curve application** (`apply_response_curve_to_funscript`) — replaced a Python `for` loop with `np.interp` + `np.clip` over the whole array in one call.

### Config Default Tuning

4. **Pulse width range widened** — `pulse_width_min` 0.10 → 0.05, `pulse_width_max` 0.55 → 0.65 for a broader pulse shape range.

5. **Volume ramp combine ratio adjusted** — `volume_ramp_combine_ratio` 25.2 → 20.0.

---
