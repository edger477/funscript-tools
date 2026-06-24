## What's New in v2.4.6

### Bug Fixes

1. **Fixed crash when loading or applying placeholder events** — events with an empty `steps:` key (no step items in YAML) caused a `"NoneType is not iterable"` crash both in the parameter preview panel and when processing/applying events. Both code paths now treat an absent or empty steps list as an empty list.

### Performance — Custom Events Builder with 150+ events

2. **No more UI freezes or blocked mouse input** — canvas redraws are now debounced via a 16 ms `after()` timer, collapsing rapid successive redraw requests into one. The mouse event queue is never starved.

3. **Lane assignment and conflict detection skipped on pan/zoom/playhead** — these O(n log n) and O(n²) operations are now gated on a layout-dirty flag and only run when events are actually added, moved, resized, or removed.

4. **Funscript waveform rendering up to 15× faster** — the visible point range is found in O(log n) using a precomputed timestamp index and `bisect`, replacing an O(n) full-scan over all 30 000+ points. Visible points are then subsampled to ≤ 2 per canvas pixel, so a 30-minute funscript at fit-view zoom passes ≈ 2 000 points to Tcl instead of ≈ 14 000.

5. **Event list treeview update ≈ 50× faster for move/resize** — rows are updated in-place with `item()` calls when the event count is unchanged. A full delete-and-reinsert (150 ms for 150 rows) only happens when events are added or removed.

6. **Eliminated `<<TreeviewSelect>>` redraw feedback loop** — programmatic `selection_set()` calls in the event list are now bracketed by unbind/rebind of the `<<TreeviewSelect>>` handler, preventing the handler from scheduling a redundant canvas redraw.

7. **`_init_sash` retry loop capped** — retries are limited to 10 attempts (≈ 1 second); `update_idletasks()` is called only on the first attempt, preventing cascading `<Configure>` events that caused continuous full redraws on some systems.

8. **Video tick fast path** — during video playback, each tick only redraws the playhead canvas item rather than the full canvas; a full redraw is triggered only when the view needs to auto-scroll.

---
