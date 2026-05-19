## What's New in v2.4.1

### Bug Fixes

1. **Tear-shaped prostate algorithm — segment-based direction assignment** — eliminated sudden large jumps in alpha/beta when the source funscript crosses value 0.5:
   - *Root cause*: direction was determined per-point using a 3-sample lookahead. Near value 0.5 or at noisy peaks, the trend could flip, mapping the same `pos_in_range = 0.5` to both the upper arc (β = 0.5 + r) and the lower arc (β = 0.5 − r) in successive frames.
   - *Fix*: the algorithm now identifies monotone segments between consecutive local extrema and assigns a single fixed direction to all points in each segment. Direction never changes mid-segment, so the arc is traced smoothly from boundary to boundary. A light Gaussian smoothing pass (σ ≈ 2 samples, ~80 ms at 25 pps) bridges the discontinuities where adjacent segments have different stroke ranges.

---
