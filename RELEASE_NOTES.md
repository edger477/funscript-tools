## What's New in v2.1.0

### Motion Axis tab split into 3P and 4P
1. "Motion Axis" tab replaced by two independent tabs: **Motion Axis (3P)** (legacy alpha/beta) and **Motion Axis (4P)** (E1-E4)
2. Each tab has its own **Generate motion scripts** checkbox and **Generate phase-shifted versions** checkbox on the same row
3. 3P and 4P script generation can now be enabled/disabled independently
4. Each tab has independent phase-shift delay percentage settings

### Bugfixes
5. Fixed matplotlib not being installed during Windows build (added to requirements.txt and PyInstaller hidden imports)
6. Fixed E1-E4 files not being copied to output after generation (missing filename parameter in generate_motion_axes call)
