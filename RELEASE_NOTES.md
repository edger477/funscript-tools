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
