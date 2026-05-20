## What's New in v2.4.4

### Bug Fixes

1. **Tear-shaped prostate algorithm — complete rewrite** — replaced the segment-based polar arc algorithm with a simpler, provably correct formula:
   - **Alpha** tracks the funscript position directly (0→1 maps to left→right).
   - **Beta** traces a sine arc above or below 0.5 for each stroke:
     - Upstrokes arc **above** β=0.5 (wide side of the tear).
     - Downstrokes arc **below** β=0.5 using `min_distance_from_center` as the narrow/wide ratio.
     - Arc height scales with stroke range: `bulge = stroke_range / 2`, capped at 0.5.
   - Because `sin(0) = sin(π) = 0`, beta is **exactly 0.5 at every stroke extremum** — consecutive strokes connect with zero discontinuity and the tear shape never resets mid-oscillation.
   - Strokes shorter than 25% of the full range produce no arc (beta stays at 0.5), so small oscillations glide smoothly along the alpha axis without generating tiny restart loops.

---
