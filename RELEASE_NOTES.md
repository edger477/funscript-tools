## What's New in v2.3.6

### Bug Fixes

1. **E1-E4 motion axes now interpolated at the configured interval** — previously, generated axis files only contained points where the original script had a keyframe. They now interpolate at the interval configured in the Speed tab (`interpolation_interval`), producing a smooth dense point grid identical to what the rest of the pipeline uses.

2. **Fixed crash on funscripts with out-of-order entries** — some funscript files contain stray entries with incorrect timestamps (e.g. `{"at": 0, "pos": 0}` appended at the end). These caused an array index out-of-bounds exception in the processor. Actions are now sorted by timestamp on load, so any stray entry is placed correctly and processing continues normally.

---

## What's New in v2.3.5

### Video Player Overhaul

1. **Replaced ffpyplayer with python-vlc** — VLC renders directly into the canvas window via HWND embedding. No frame copying or transfer queue needed; seeking is near-instant and play/pause responds immediately. MKV and other formats that crashed ffpyplayer now work reliably.

2. **Frozen exe is self-contained** — `libvlc.dll`, `libvlccore.dll` and the VLC `plugins/` folder are bundled via the PyInstaller spec. No separate VLC installation required on Windows.

### Timeline UX Improvements

3. **Seek bar click jumps directly to position** — clicking anywhere on the seek bar now seeks to that exact position (previously stepped page-by-page).

4. **Time label toggles elapsed / remaining** — click the time label in the video window to switch between `elapsed / total` and `-remaining / total` display.

5. **Timeline auto-scrolls during playback** — the timeline pages forward automatically when the playhead reaches the right edge.

---

## What's New in v2.3.4

### Video Playback Performance

1. **Eliminated audio blip on seek** — audio is muted during the short decode window after a seek while paused, removing the audible blip that occurred with ffpyplayer.

2. **Canvas image item reused each frame** — the canvas item is updated in-place (`itemconfig`) instead of being deleted and recreated each frame, reducing per-frame overhead.

3. **Cached canvas dimensions and metadata** — canvas size is cached via a `<Configure>` binding; video duration and FPS are read once and cached after the first successful read.

4. **Time label and seek bar throttled to ~5 fps** — UI updates during playback are batched to reduce CPU load; seek and pause still update immediately.

5. **Timeline redraws throttled to ~15 fps** — canvas redraws during video playback are limited to every other video tick to reduce overhead.

---

## What's New in v2.3.3

### Bug Fixes

1. **Fixed crash when reopening Custom Event Builder** — an access violation in `SDL2_mixer.dll` occurred when opening the Custom Event Builder a second time after processing files. ffpyplayer's internal C thread was still accessing SDL audio resources when the new dialog tried to re-initialize SDL. Fixed by cancelling all pending Tkinter callbacks on player close, forcing garbage collection of the C-level player wrapper, and delaying window destruction by 300 ms to let the thread wind down cleanly.

2. **Fixed error loading event files with empty events section** — a `NoneType is not iterable` error appeared when loading a default events file whose `events:` key had no entries (only comments). `yaml.safe_load` returns `None` for a key with a comment-only block; `dict.get('events', [])` does not substitute the default when the key is present but `None`. Fixed by using `or []` instead.

3. **Fixed fallback dark theme when sv_ttk is not installed** — the app now falls back gracefully when `sv_ttk` is not available.

### Experimental

- **macOS build** — an experimental GitHub Actions workflow (`build-mac.yml`) has been added for manual-trigger macOS builds. The video player is Windows-only; all other features work on macOS. Trigger via Actions → Build macOS (manual).

### Bug Fixes

1. **Fixed crash when reopening Custom Event Builder** — an access violation in `SDL2_mixer.dll` occurred when opening the Custom Event Builder a second time after processing files. ffpyplayer's internal C thread was still accessing SDL audio resources when the new dialog tried to re-initialize SDL. Fixed by cancelling all pending Tkinter callbacks on player close, forcing garbage collection of the C-level player wrapper, and delaying window destruction by 300 ms to let the thread wind down cleanly.

2. **Fixed error loading event files with empty events section** — a `NoneType is not iterable` error appeared when loading a default events file whose `events:` key had no entries (only comments). `yaml.safe_load` returns `None` for a key with a comment-only block; `dict.get('events', [])` does not substitute the default when the key is present but `None`. Fixed by using `or []` instead.

3. **Fixed fallback dark theme when sv_ttk is not installed** — the app now falls back gracefully when `sv_ttk` is not available.

---

## What's New in v2.3.2

### New Features (merged from contributor PR #10 + follow-up fixes)

**Canvas Timeline (Custom Event Builder)**
1. Replaced the basic event list with a fully interactive canvas timeline — drag blocks to reposition, drag right edge to resize event duration
2. Zoom with Ctrl+scroll, pan with scroll or drag background
3. Snap-to-grid (Off / 0.5s / 1s / 5s / 10s / 30s / 1m)
4. Undo / Redo support
5. Funscript waveform overlay — auto-loads matching `.funscript` when opening an events file
6. Playhead indicator
7. Conflict detection — overlapping events warn before save/apply
8. Category-coloured event blocks (mcb / clutch / test / general)

**Video Playback & Timeline**
9. Synchronized video playback window (ffpyplayer) with timeline scrubbing
10. Arrow key frame stepping and spacebar play/pause on timeline; keys work when video window is focused
11. Seek bar in video window syncs timeline playhead
12. "Show waveform" checkbox in Options bar to hide/show funscript track
13. Timeline ruler minor tick subdivisions and two-level grid
14. Timeline zoom extended to support long videos (>15 min)
15. Auto-load matching video file when opening events for same source

**Dark Mode**
16. Dark/light mode toggle button in main toolbar (sv_ttk theme)
17. Dark mode preference is now persisted in config and restored on next launch

### Dependencies added
- `python-vlc>=3.0.0` (Windows only; replaces ffpyplayer + Pillow)
- `sv-ttk>=2.6.0`
