## What's New in v2.4.7

### New Features

1. **MCB extract / Relentless mode events** — custom event definitions replicating SC Extract pole-switching:
   - `mcb_extract` and `mcb_extract_additive` (3P alpha/beta)
   - `mcb_extract_4p` and `mcb_extract_4p_additive` (4P e4→e1 upward pull, configurable `step_ratio`)
   - `corrupt_4p` (4P inharmonic sawtooth drift)

2. **Chapter export** — custom events can be written as OFS chapters in the base `.funscript` `metadata.chapters`:
   - Toggle in Custom Event Builder options bar ("Chapters: Funscript", default on)
   - Preserves existing chapters and appends new ones from the event timeline
   - Uses the same display names as the UI (General / Clutch / MCB prefixes)

3. **External volume blend (combine 2)** — optional second volume combine after ramp+speed:
   - Blend tool-generated volume with a browsed external `.funscript` (e.g. released volume files)
   - Volume tab: enable checkbox, file browse, **Generated | External** ratio (same UX as Ramp | Speed)
   - Optional output range min/max to compress full 0–100 envelopes for restim
   - Normalization runs after both combines when enabled

4. **CLI** — `python cli.py preview volume-blend [--ratio N] [--json]` describes combine 2 settings

### Improvements

1. **Modulation waveform accuracy** — `_ensure_dense_timestamps()` inserts interpolated points before applying modulation so triangle/sawtooth events render faithfully on sparse axes.
2. **Custom Event Builder** — Funscript snap mode (default), proportional event blocks at any zoom, stable lane layout, waveform downsampling, debounced zoom/pan redraw, VLC seek-bar fixes when switching videos.
3. **Dark mode** — blue info labels use a lighter accent color for readability.
4. **Windows build** — PyInstaller onefile spec; release package assembles a versioned folder with exe and documentation.
5. **RDP simplification** — `simplify_funscript()` preserves funscript metadata through simplification.

### Documentation

- USER_GUIDE and CLI_REFERENCE updated for two-stage volume processing

---

## What's New in v2.4.6

### Bug Fixes

1. **Fixed crash when loading or applying placeholder events** ΓÇö events with an empty `steps:` key (no step items in YAML) caused a `"NoneType is not iterable"` crash both in the parameter preview panel and when processing/applying events. Both code paths now treat an absent or empty steps list as an empty list.

### Performance ΓÇö Custom Events Builder with 150+ events

2. **No more UI freezes or blocked mouse input** ΓÇö canvas redraws are now debounced via a 16 ms `after()` timer, collapsing rapid successive redraw requests into one. The mouse event queue is never starved.

3. **Lane assignment and conflict detection skipped on pan/zoom/playhead** ΓÇö these O(n log n) and O(n┬▓) operations are now gated on a layout-dirty flag and only run when events are actually added, moved, resized, or removed.

4. **Funscript waveform rendering up to 15├ù faster** ΓÇö the visible point range is found in O(log n) using a precomputed timestamp index and `bisect`, replacing an O(n) full-scan over all 30 000+ points. Visible points are then subsampled to Γëñ 2 per canvas pixel, so a 30-minute funscript at fit-view zoom passes Γëê 2 000 points to Tcl instead of Γëê 14 000.

5. **Event list treeview update Γëê 50├ù faster for move/resize** ΓÇö rows are updated in-place with `item()` calls when the event count is unchanged. A full delete-and-reinsert (150 ms for 150 rows) only happens when events are added or removed.

6. **Eliminated `<<TreeviewSelect>>` redraw feedback loop** ΓÇö programmatic `selection_set()` calls in the event list are now bracketed by unbind/rebind of the `<<TreeviewSelect>>` handler, preventing the handler from scheduling a redundant canvas redraw.

7. **`_init_sash` retry loop capped** ΓÇö retries are limited to 10 attempts (Γëê 1 second); `update_idletasks()` is called only on the first attempt, preventing cascading `<Configure>` events that caused continuous full redraws on some systems.

8. **Video tick fast path** ΓÇö during video playback, each tick only redraws the playhead canvas item rather than the full canvas; a full redraw is triggered only when the view needs to auto-scroll.

---
## What's New in v2.4.5

### New Features

1. **RDP simplification for generated funscripts** — Ramer-Douglas-Peucker point reduction via `pybind11-rdp`:
   - New `options.rdp_epsilon` config option (default 0.002); set to 0 to disable
   - All generated funscripts pass through simplification when epsilon > 0

---

## What's New in v2.4.4

### Bug Fixes

1. **Tear-shaped prostate algorithm ΓÇö complete rewrite** ΓÇö replaced the segment-based polar arc algorithm with a simpler, provably correct formula:
   - **Alpha** tracks the funscript position directly (0ΓåÆ1 maps to leftΓåÆright).
   - **Beta** traces a sine arc above or below 0.5 for each stroke:
     - Upstrokes arc **above** ╬▓=0.5 (wide side of the tear).
     - Downstrokes arc **below** ╬▓=0.5 using `min_distance_from_center` as the narrow/wide ratio.
     - Arc height scales with stroke range: `bulge = stroke_range / 2`, capped at 0.5.
   - Because `sin(0) = sin(╧Ç) = 0`, beta is **exactly 0.5 at every stroke extremum** ΓÇö consecutive strokes connect with zero discontinuity and the tear shape never resets mid-oscillation.
   - Strokes shorter than 25% of the full range produce no arc (beta stays at 0.5), so small oscillations glide smoothly along the alpha axis without generating tiny restart loops.

---
