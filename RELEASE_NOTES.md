## What's New in v2.4.2

### Bug Fixes

1. **Tear-shaped prostate algorithm — hysteresis thresholds** — eliminated the "tear shape restarts every oscillation" artifact:
   - *Root cause*: every monotone segment, no matter how small, traced a full tear-shaped arc (looping through top arc on upstroke, narrow bottom arc on downstroke). Small oscillations around a midpoint (e.g. 40↔60) produced a tiny repeating tear loop that visually restarted from scratch on each cycle.
   - *Fix*: a stroke must span the full range from ≤ 30% up to ≥ 70% (or vice versa) to qualify as a full tear arc. Strokes that stay within a narrower band are rendered as proportional linear motion — beta stays at 0.5 and alpha tracks position — so partial oscillations glide smoothly without the restart artifact.

---
