## What's New in v2.2.3

### Fix: Alpha/Beta Grid Alignment with Speed Funscript

1. **Fixed isolated low-value artifacts in `pulse_frequency`** — caused by segment-relative `np.linspace` timestamps in alpha/beta generation drifting off the speed funscript's uniform 20 ms `np.arange` grid. When the two grids were merged via `union1d` in `combine_funscripts`, the alpha funscript's true arc-minimum appeared as an extra outlier point at an off-grid time, producing a single noticeably low value (visible as ~20% dip) surrounded by correctly-interpolated neighbours.
2. **Alpha/beta generation now uses the speed funscript's own timestamps** as the output time grid (when `speed_funscript` is provided). `union1d` therefore adds zero new points — the combined grid is identical to the speed grid.
3. **Points Per Second in the 3P tab is now read-only**, automatically derived as `round(1 / interpolation_interval)`. This keeps the fallback arange path consistent with the speed grid and prevents the user from accidentally re-introducing misalignment.

---

## What's New in v2.2.2

### Hotfix
1. Fixed typo `§stroke_offset` → `$stroke_offset` in the `slow` event definition — caused a numpy DType error ("The DType `StrDType` could not be promoted by `PyFloatDType`") when applying effects in the Custom Event Builder

---

## v2.2.1 — Central folder bugfixes and zip output feature

### Bugfixes
1. Fixed **Process Motion Files** ignoring the central folder setting — files were written to the source funscript folder instead of the configured central folder
2. Fixed the same central folder bug in the 3P conversion path (_perform_2d_conversion)
3. Fixed **Custom Event Builder**: fractional frequencies (e.g. `buzz_freq: 1.5`) now use a float spinbox instead of an integer spinbox

### New Feature: Zip Output in Central Mode
4. Added **Zip output files** option in the General tab (only active when Central mode is selected)
5. When enabled, all generated `.funscript` files are packed into a single `<name>.zip` in the central folder instead of individual files
6. On re-process without backups, the previous `.zip` is deleted before regenerating

### Tuned Event Defaults
7. `cum`: `buzz_intensity` 0.07→0.1, `volume_boost` 0.1→0.2
8. `stay`: `buzz_intensity` 0.03→0.05, `volume_boost` 0.05→0.1
9. `edge`: `buzz_intensity` 0.1→0.07, `volume_boost` 0.1→0.15
10. `slow`: separated alpha linear offset from modulation (was incorrectly using `max_level_offset` for the DC bias)
11. `medium`, `fast`: `stroke_offset` default 0.1→0 (center-aligned strokes)

---

## v2.2.0 — Tuned event defaults and config

1. Tuned `cum`: `buzz_intensity` 0.05→0.07, `volume_boost` 0.05→0.10
2. Tuned `stay`: `buzz_freq` 10→15, `buzz_intensity` 0.02→0.03, `volume_boost` 0.01→0.05
3. Tuned `medium`: `buzz_freq` 30→10, `volume_boost` 0.05→0.10, `ramp_up_ms` 250→500
4. Tuned `clutch_tantalize`: `volume_boost` 0.05→0.03; fixed `clutch_tranquil` volume axis and start/end values
5. Updated config default `interpolation_interval` 0.05→0.02 for higher resolution processing

---

## v2.1.1 — Custom events bugfixes and new event definitions

1. Fixed normalization bug: negative values on axes with `max > 1.0` (e.g. `pulse_frequency`) now correctly divided by max instead of passed through as-is
2. Added step validation in event processor: clear errors for missing `operation`, `axis`, or `start_value` fields (including hint to use `apply_modulation`)
3. Improved error reporting in Custom Event Builder: full traceback shown for unexpected errors
4. Added new event definitions: `cum`, `stay`, `medium`, `fast`, `edge` (General group)
5. Updated config defaults: algorithm, interpolation interval, `pulse_freq_min`, overwrite behavior
