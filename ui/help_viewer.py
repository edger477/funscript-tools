"""
Built-in help viewer. Displays scrollable help text in a popup window,
launched from the Help menu on the main window's menu bar.
"""

import tkinter as tk
from tkinter import ttk

# ── Help content ─────────────────────────────────────────────────────
# Stored as a plain string so it renders in a Text widget without any
# external dependencies.  Sections use ALL-CAPS headers, subsections
# use Title Case with dashes.

HELP_TEXT = r"""
================================================================================
                     RESTIM FUNSCRIPT PROCESSOR — HELP
================================================================================

TABLE OF CONTENTS
  1.  Overview
  2.  General Tab
  3.  Speed Tab
  4.  Frequency / Volume / Pulse Tabs
  5.  Motion Axis (3P) Tab
  6.  Understanding E1-E4 Axes — How Electrodes Interpret Signals
  7.  Motion Axis (4P) Tab — E1-E4 Generation
  8.  Curve Editor
  9.  Modulation (per-axis LFO)
  10. Physical Model (cascade delay)
  11. Animation Viewer
  12. Signal Analyzer
  13. Curve Quantization (Trochoid Tab)
  14. Trochoid Spatial Tab — Curve-driven E1-E4
  15. Traveling Wave Tab — Linear/Axial E1-E4
  16. Comparison Viewer (Compare Funscripts)
  17. Shaft Viewer — Horizontal Cylinder + Synced Video
  18. Trochoid Viewer — 2D Curve + Shaft Shadow / Lobes
  19. Variants (A/B/C/D Whole-Config Snapshots)
  20. UI Conventions (Two-Row Tabs, Scroll Anywhere)
  21. Tips & Suggestions

================================================================================
1. OVERVIEW
================================================================================

This tool converts a .funscript file (position vs time) into a set of
e-stim control signals for use with restim. One funscript in, multiple
output files out — each controlling a different dimension of sensation.

OUTPUT FILES:
  *.alpha / *.beta           Electrode X/Y position (where you feel it)
  *.e1 / *.e2 / *.e3 / *.e4 Motion axis electrode intensities (4P mode)
  *.frequency                Pulse rate envelope
  *.pulse_frequency          Action-speed-mapped pulse rate
  *.volume                   Amplitude envelope (how strong)
  *.pulse_width              Pulse duration (fullness vs sharpness)
  *.pulse_rise_time          Pulse attack (hard vs soft onset)
  *.speed / *.accel          Speed and acceleration signals

WORKFLOW:
  1. Load a .funscript file (drag-and-drop or Browse)
  2. Adjust settings across the tabs
  3. Click "Process All Files" or "Process Motion Files"
  4. Output files appear next to the input file

================================================================================
2. GENERAL TAB
================================================================================

Rest Level (0.0-1.0)
  Signal level when volume ramp or speed is zero. Higher = more baseline
  sensation during quiet moments. 0.4 is a good starting point.

Ramp Up Duration After Rest (0-10 sec)
  How long to fade from rest level back to full output after a pause.
  0 = instant snap back, 5 = gentle ramp. Prevents jarring transitions.

Speed Window (0.5-30 sec)
  Rolling window for speed calculation. This is the single most impactful
  setting for how responsive the output feels.
    Smaller (0.5-1):  Tracks fast strokes, noisier signal.
    Default (2):      Good balance.
    Larger (3-5):     Smooth, averaged, sluggish response.
  Also affects alpha/beta radius scaling (faster = bigger radius).

Accel Window (0.5-10 sec)
  Same concept applied to the speed signal to derive acceleration.
  Measures how fast the speed itself is changing.
    Smaller (1):    Catches sudden speed changes.
    Default (3):    Balanced.
    Larger (4-6):   Smoother acceleration curve.

Processing Options:
  Normalize Volume       Scale volume to use the full 0-1 range.
  Delete Intermediary    Remove temp files after processing.
  Overwrite Existing     Replace output files if they already exist.

================================================================================
3. SPEED TAB
================================================================================

Calculation Method
  Three algorithms for deriving speed from position data. Each uses the
  Speed Window and Accel Window from the General tab, but interprets them
  slightly differently.

  ROLLING AVERAGE (original, default)
    Backward-looking rectangular window. Averages the absolute velocity of
    every consecutive sample pair within the window. O(n^2).
    + Biggest dynamic range (fast sections pop, slow sections drop near zero)
    + Most familiar behavior
    - Sluggish on fast transients, box-car artifacts at window edges

  EXPONENTIAL MOVING AVERAGE (EMA)
    Single-pass exponential decay. Recent samples weighted more, old ones
    fade smoothly. O(n) — much faster on long scripts.
    + Smoothest output, no box-car artifacts
    + Zero-lag at the trailing edge
    - Slower to respond to sudden changes (retains "memory")
    - Window parameter is half-life, not hard cutoff

  SAVITZKY-GOLAY DERIVATIVE
    Fits a local polynomial to the position data and takes its analytical
    derivative. Best at preserving the shape of individual stroke peaks.
    Falls back to EMA if scipy is not installed.
    + Best peak preservation — tracks stroke shape, not just average
    + Clean acceleration signal (polynomial 2nd derivative)
    - Requires scipy

  Savitzky-Golay Options (visible when Savitzky-Golay is selected):

    Polynomial Order (2-5, default 3)
      Degree of the polynomial fitted to each window of samples.
        2 (quadratic):  Very smooth, rounds off peaks. Good for noisy scripts.
        3 (cubic):      Standard — good balance of shape and smoothness.
        4-5:            Tracks sharper features but amplifies noise.

    Fit Window Factor (0.05-0.5, default 0.15)
      Fraction of Speed Window used for the polynomial fit.
        0.05:   Very short fit, tracks every wiggle.
        0.15:   Good balance.
        0.3-0.5: Broader fit, smooths over short strokes.

    Post-Smoothing (0.0-1.0, default 0.25)
      EMA smoothing applied on top of the savgol derivative.
        0.0:   Raw derivative, maximum detail, may be spiky.
        0.25:  Gentle smoothing (default).
        0.5-1.0: Heavy smoothing, approaches pure EMA behavior.

  PRACTICAL COMBOS:
    Clean, deliberate strokes:  Order 3, Fit 0.15, Smooth 0.25
    Fast/percussive:            Order 4, Fit 0.08, Smooth 0.15
    Noisy/jittery:              Order 2, Fit 0.3,  Smooth 0.4
    Raw analysis:               Order 3, Fit 0.1,  Smooth 0.0

Interpolation Interval (0.01-1.0 sec)
  Resampling density before speed/accel calculation.
    0.02 (default):  50 pts/sec, good balance.
    0.01:            100 pts/sec, captures faster transients, slower.
    0.05-0.1:        Faster processing, loses high-freq detail.
  Also sets the alpha/beta output grid density.

Normalization Method
  max:  Normalize so the fastest moment = 1.0.
  rms:  Normalize by RMS (root mean square) energy.

Speed / Acceleration Preview
  Click "Refresh Preview" to see how your settings transform the signal.
  Check "Compare all methods" to overlay all three methods (Rolling Average
  in blue, EMA in green, Savitzky-Golay in orange) on the same data.
  If a .funscript is loaded, the preview uses your actual file; otherwise
  it generates a synthetic fast/slow/fast test signal.

================================================================================
4. FREQUENCY / VOLUME / PULSE TABS
================================================================================

These tabs control how the remaining output dimensions are derived from
the speed and acceleration signals. Refer to the inline labels and
tooltips in each tab for parameter-specific guidance.

================================================================================
5. MOTION AXIS (3P) TAB
================================================================================

Controls alpha/beta generation (the 2D spatial position of the stimulus).
The algorithm setting is the most important choice here:

  Circular          Semicircular path (180 degrees). Smooth, natural.
  Top-Left-Right    Three-quarter circle sweep (270 degrees).
  Top-Right-Left    Quarter circle sweep (90 degrees).
  Restim Original   Full circle per segment, random direction changes.

Key parameters:
  Min Distance from Center   How close to center the pattern can collapse.
  Speed Threshold %          What speed percentile maps to full radius.
  Direction Change Prob      (Restim Original only) Chance of flipping direction.

Phase Shift creates delayed *-2.funscript variants for devices that play
two alternating scripts per axis for a richer stim feel.

================================================================================
6. UNDERSTANDING E1-E4 AXES — HOW ELECTRODES INTERPRET SIGNALS
================================================================================

The E1-E4 system is a four-electrode linear array. Unlike the alpha/beta
system (which positions a single stimulus in 2D space), the E1-E4 system
drives four independent electrodes arranged in a line. Each electrode
has its own intensity signal.

PHYSICAL LAYOUT:
  The electrodes are arranged in a straight line with equal spacing:

    E1 -------- E2 -------- E3 -------- E4
    |<- spacing ->|<- spacing ->|<- spacing ->|

  Typical spacing is 10-30 mm depending on your device. You enter
  your actual spacing in the Physical Model section.

WHAT EACH AXIS DOES:
  Each axis file (e1.funscript, e2.funscript, etc.) contains a value
  from 0 to 1 at each moment in time:

    0.0 = electrode is OFF (no stimulation)
    1.0 = electrode is at FULL intensity
    0.5 = electrode is at half intensity

  The restim software reads all four files simultaneously and drives
  each electrode independently. What you feel is the combined effect
  of all four electrodes firing at their respective intensities.

HOW A SINGLE SOURCE BECOMES FOUR DIFFERENT SIGNALS:
  Your source funscript is a single 1D signal — position over time.
  The E1-E4 system transforms this one signal into four by applying
  a different response curve to each axis:

    Source position (0-1) ---> [Response Curve E1] ---> E1 intensity
                          ---> [Response Curve E2] ---> E2 intensity
                          ---> [Response Curve E3] ---> E3 intensity
                          ---> [Response Curve E4] ---> E4 intensity

  Each response curve is a remapping function. For example:
    Linear:     input 0.5 -> output 0.5 (passthrough)
    Ease In:    input 0.5 -> output 0.2 (quiet at low positions, strong at high)
    Inverted:   input 0.5 -> output 0.5 (high input -> low output)
    Sharp Peak: input 0.5 -> output 1.0 (spikes in the middle)

  By giving each electrode a different curve, the same source motion
  creates a spatially varied sensation — different electrodes respond
  to different parts of the stroke.

EXAMPLE — HOW A STROKE PLAYS ACROSS FOUR ELECTRODES:
  Suppose the source goes from 0 (bottom) to 1 (top) over 1 second.
  With these curves:
    E1: Ease In      (quiet at bottom, strong at top)
    E2: Sharp Peak   (spikes in the middle)
    E3: Inverted     (strong at bottom, quiet at top)
    E4: Bell Curve   (strongest at mid-range, quiet at extremes)

  As the stroke rises from 0 to 1:
    t=0.0s (pos=0.0): E1=low  E2=low   E3=HIGH E4=low   <- E3 dominates
    t=0.3s (pos=0.3): E1=low  E2=med   E3=med  E4=HIGH  <- E4 peaks
    t=0.5s (pos=0.5): E1=med  E2=HIGH  E3=med  E4=HIGH  <- E2+E4 peak
    t=0.7s (pos=0.7): E1=med  E2=med   E3=low  E4=med   <- spreading out
    t=1.0s (pos=1.0): E1=HIGH E2=low   E3=low  E4=low   <- E1 dominates

  The sensation "travels" from E3 -> E4 -> E2 -> E1 as the stroke rises.
  On the way back down, the pattern reverses.

SIGNAL ROTATION (ANGLE MANIPULATION):
  Before the response curve is applied, the input signal can be rotated
  around its center (0.5) by an angle. This effectively compresses or
  inverts the input range that each axis sees:

    0 degrees:   Normal input (unchanged).
    90 degrees:  Signal compressed to a flat line at 0.5 (cos(90)=0).
    180 degrees: Signal inverted (0 becomes 1, 1 becomes 0).

  By giving each axis a different rotation angle, you can make them
  respond to different "views" of the same source signal — similar to
  how rotating a microphone changes what it picks up.

THE FULL PROCESSING CHAIN (in order):
  1. Source funscript (position 0-1 over time)
  2. Signal rotation (angle manipulation, if set)
  3. Response curve (remaps input to output)
  4. Modulation (sine LFO wobble, if enabled)
  5. Cascade delay (physical model time shift, if enabled)
  6. Phase shift (dual *-2 variant, if enabled)
  7. Save to *.e1.funscript, *.e2.funscript, etc.

  Steps 2-3 shape WHAT each electrode does.
  Step 4 adds TEXTURE (wobble/shimmer).
  Step 5 adds SPATIAL MOTION (traveling sweep).
  Step 6 creates dual-variant files for alternating playback.

COMPARISON: ALPHA/BETA (3P) VS E1-E4 (4P):

  ALPHA/BETA (3P):
    - Two signals: X and Y position.
    - Controls WHERE a single stimulus point moves in 2D space.
    - All the stimulation is at one point; the point moves.
    - Good for: circular/sweeping patterns, focused sensation.

  E1-E4 (4P):
    - Four signals: one intensity per electrode.
    - Controls HOW MUCH each electrode fires independently.
    - Multiple electrodes can fire simultaneously at different levels.
    - Good for: spatial texture, traveling waves, complex patterns.

  You can generate both simultaneously (enable both in the tabs) and
  let restim layer them together, or use one mode exclusively.

PRACTICAL GUIDE — CHOOSING RESPONSE CURVES:
  Start simple and add complexity:

  STEP 1 — All Linear:
    All four axes pass through the source unchanged. Every electrode
    does the same thing. Boring, but it confirms your setup works.

  STEP 2 — One curve different:
    Set E1 to Ease In, keep others Linear. Now E1 responds more to
    the top of each stroke. You'll feel spatial asymmetry.

  STEP 3 — Complementary pairs:
    E1 = Ease In (strong at top), E3 = Inverted (strong at bottom).
    Now up-strokes light up E1, down-strokes light up E3. The sensation
    has directionality.

  STEP 4 — Full differentiation:
    Give each axis a unique curve. Use the Waveform Preview to see how
    the four outputs look before processing. Add modulation for texture,
    cascade delay for spatial sweep.

================================================================================
7. MOTION AXIS (4P) TAB — E1-E4 GENERATION
================================================================================

Generates four electrode-intensity files (E1-E4) using configurable
response curves. Each axis has:

  Enabled checkbox      Turn the axis on/off.
  Edit Curve button     Open the curve editor to shape the response.
  Curve visualization   Shows the current response curve graphically.

The response curve maps input position (0-1) to output intensity (0-1).
A linear curve passes the signal through unchanged. Shaped curves
(ease-in, sharp-peak, inverted, etc.) give each electrode a different
character.

Angle Manipulation
  Rotates the input signal before applying the curve. Useful for giving
  each axis a different "view" of the same source signal. Enter degrees
  for each axis and click Apply.

Config Presets
  Save, load, clone, rename, delete, export, and import complete axis
  configurations. Useful for A/B testing different curve setups.

Waveform Preview
  Shows the input signal and all four axis outputs stacked. Click
  "Refresh Preview" after changing settings. Zoom and scroll to inspect
  details.

================================================================================
8. CURVE EDITOR
================================================================================

Click "Edit Curve" on any E1-E4 axis to open the curve editor. The editor
has three resizable panels that you can drag to resize:

LEFT PANEL — Curve Presets + Library
  Built-in presets (Linear, Ease In, Ease Out, Bell Curve, Inverted,
  S-Curve, Sharp Peak, Gentle Wave) are always available.

  Below the built-in presets, your saved curves appear with a star:
    Linear
    Ease In
    ...
    --- Saved Curves ---
    * My Custom Curve
    * Percussion Spike

  Buttons:
    Load               Apply the selected preset/curve to the editor.
    Save to Library    Save the current curve by name. Built-in names
                       are reserved — you'll be prompted with "My <name>"
                       if you try to use one.
    Delete from Lib    Remove a saved curve (built-in presets can't be deleted).
    Rename             Rename a saved curve.

  The curve library is stored in curve_library.json and persists across
  sessions and config resets. Any curve saved from any axis can be loaded
  onto any other axis.

CENTER PANEL — Interactive Canvas
  Click to add control points. Drag points to move them. Right-click to
  delete. The curve updates in real time as you edit.

  The title above the plot shows the curve name. If you modify a built-in
  preset's control points, the name automatically changes to
  "Custom (<original name>)" to prevent accidentally overwriting the
  built-in definition.

RIGHT PANEL — Control Points
  A table showing all X,Y coordinates. Click a row to select it and
  fill the X/Y entry fields below.

  Coordinate Entry:
    X: [___]  Y: [___]
    [Add Point]  [Update Point]  [Remove Point]
    [Bulk Entry...]

    Add Point      Adds a new point at the entered X,Y.
    Update Point   Overwrites the selected point's coordinates.
    Remove Point   Deletes the selected point.
    Enter key      Smart: updates the selected point if one is selected,
                   adds a new point if none is selected.

  Bulk Entry:
    Opens a text dialog where you can type or paste multiple X,Y pairs:
      0.000, 0.000
      0.250, 0.100
      0.500, 0.800
      1.000, 1.000

    Flexible formats: "0.5, 0.8" or "0.5 0.8" or "(0.5, 0.8)" all work.
    Lines starting with # are ignored. Choose "Replace all" to start fresh
    or "Append" to add to existing points. Duplicate X values merge
    automatically (last one wins).

BOTTOM BUTTONS:
  Restore Default   Reset to the code-defined factory default for this
                    axis (E1=Linear, E2=Ease In, E3=Ease Out, E4=Bell Curve).
  Reset             Revert to the curve as it was when the editor opened.
  Cancel            Close without saving.
  Save Curve        Save the current curve to the axis config.

BUILT-IN PRESET PROTECTION:
  If you load "Ease In", drag some points, and click Save — the curve is
  automatically renamed to "Custom (Ease In)". This prevents the built-in
  preset's name from being associated with wrong control points. The real
  Ease In is always available in the presets list.

  Protected names: Linear, Ease In, Ease Out, Bell Curve, Inverted,
  S-Curve, Sharp Peak, Gentle Wave.

================================================================================
9. MODULATION (PER-AXIS LFO)
================================================================================

Each E1-E4 axis has a modulation row below the Enabled/Curve controls:

  [x] Modulation   Freq (Hz): [0.5]   Depth: [0.15]   [x] Phase [180] deg

WHAT IT DOES:
  Adds a gentle sine-wave wobble on top of whatever the axis is already
  doing. Think of it as texture or shimmer — the axis signal slowly
  oscillates around its base value.

HOW IT WORKS:
  The signal is shrunk from [0,1] into [depth, 1-depth] to make headroom,
  then a sine LFO is added. This ensures the wobble has full amplitude
  everywhere (even at the center and extremes) without clamping.

  When modulation is enabled, the axis is automatically resampled to
  60 Hz so the wobble has enough sample density to exist, even on
  sparse source scripts.

PARAMETERS:
  Frequency (Hz)    How fast the wobble cycles. 0.5 Hz = one wobble every
                    2 seconds. Typical slow-texture range is 0.1-3 Hz,
                    but higher values are allowed (e.g., 8 Hz on E2 and
                    16 Hz on E4 to layer per-electrode fast LFOs). At
                    high frequencies, the funscript timestamp resolution
                    (resampled to 60 Hz internally) caps the effective
                    fidelity — treat ~20-25 Hz as a practical ceiling.

  Depth (0-0.5)     How big the wobble is. 0.15 = the value swings +/-15%
                    of full range. Higher = more intense wobble.

  Phase checkbox    Toggles whether the phase offset is applied.
                    When off, phase is treated as 0 degrees.

  Phase (degrees)   Where in the wobble's cycle this axis starts.
                    Only matters when multiple axes modulate at the same
                    frequency — it determines their relationship:
                      0 vs 180 = counter-phased (one up, other down)
                      0 vs 90  = quadrature (circular feel)
                      0 vs 0   = in unison (no point)

  DEFAULT PHASE OFFSETS:
    E1 = 0 deg, E2 = 180 deg, E3 = 90 deg, E4 = 270 deg
    This gives you counter-phased pairs (E1/E2) and quadrature (E3/E4)
    automatically.

APPLIES TO:
  - Response-curve E1-E4 (Motion Axis 4P tab, section 7).
  - Traveling Wave E1-E4 (section 15). Each axis's modulation block is
    applied as a post-processing step on the wave's output envelope.
  - NOT Trochoid Spatial (the radial projection writes its own
    intensity directly without going through the per-axis modulation
    post-step).

================================================================================
10. PHYSICAL MODEL (CASCADE DELAY)
================================================================================

Located in the Motion Axis (4P) tab, below the phase-shift controls.
This creates apparent motion — the sensation of the stimulus physically
traveling across your electrode array.

HOW IT WORKS:
  For a linear e1-e2-e3-e4 electrode arrangement, each axis is delayed
  by a different amount so the stimulus sweeps across electrodes:

    E1: 0 ms delay (fires first)
    E2: 1 x step delay
    E3: 2 x step delay
    E4: 3 x step delay (fires last)

  Where step = (electrode spacing / propagation speed) x 1000 ms.

  This is NOT based on literal nerve conduction velocity (which would give
  sub-millisecond delays too small to matter). Instead it's based on
  cutaneous apparent motion — the psychophysical illusion where spatially
  separated stimulations fired in quick succession feel like continuous
  traveling motion. The optimal timing for this illusion is 20-200 ms,
  which is right where these delays land.

PARAMETERS:
  Enabled           Master toggle. Processing ignores this section when off.

  Spacing (mm)      Physical distance between adjacent electrodes.
                    Measure your device once and type it in. Default 20 mm.

  Speed (mm/s)      Apparent-motion propagation speed.
                      100 mm/s (Slow sweep):   Deliberate, stretched-out.
                      300 mm/s (Natural touch): Perceptual sweet spot.
                      1000 mm/s (Fast sweep):   Quick but still perceptible.

  Preset dropdown   Quick-select for common speed values plus "Custom".

  Sweep direction   Three modes:
    e1 -> e4          Fixed: always sweeps toward E4.
    e4 -> e1          Fixed: always sweeps toward E1.
    follow signal     Flips direction based on the source signal:
                      Up-strokes sweep e1->e4, down-strokes sweep e4->e1.
                      Feels like the stim is tracking the motion.

  The "follow signal" mode detects strokes in the source and applies
  direction-matched cascade shifts per stroke. A minimum stroke duration
  filter (100 ms) prevents micro-wobbles from triggering rapid flip-flops.

  TRANSITION HANDLING (follow signal mode):
    At direction changes, some axes experience overlap (new stroke starts
    before old finishes) and others experience gaps (new stroke hasn't
    arrived yet). Resolution:
      Overlap: newer stroke wins (older tail truncated).
      Gap: axis holds its last value until the new stroke reaches it.
    These artifacts are small on deliberate strokes and invisible to
    the nervous system at typical timing values.

LIVE PREVIEW:
  The label next to the controls shows:
    step 66.7 ms   sweep 200.0 ms (follows signal)
  "step" is the delay per electrode hop. "sweep" is the total time from
  first electrode to last (step x 3).

================================================================================
11. ANIMATION VIEWER
================================================================================

Click the "Animation Viewer" button in the bottom bar to open a popup
window showing an animated visualization of your output.

The viewer has three panels, each independently togglable:

TRAJECTORY PANEL (top left)
  Shows the alpha/beta position as an animated dot tracing a path.
    Gray path:   Full trajectory (static, faint).
    Blue trail:  Last 40 points, showing recent direction.
    Red dot:     Current position.
    Dashed circle: Electrode boundary. Cross: center (rest).

  2D MODE (default):
    Flat XY view of the alpha/beta path.

  3D MODE (check "3D"):
    X = Alpha, Y = Beta, Z = Time. The trajectory becomes a color-coded
    ribbon (blue=early, red=late). Click and drag to rotate. Top-down
    recovers the 2D perspective; side view shows temporal structure.

BARS PANEL (top right)
  Four colored bars (E1-E4) showing each electrode's intensity at the
  current moment. Animates in sync with the trajectory dot.
  E1 = blue, E2 = orange, E3 = green, E4 = red.

DIMMER STRIP / WATERFALL (bottom, full width)
  Shows E1-E4 intensity over the full timeline. E1 is at the top.

  HEATMAP MODE (default):
    Four horizontal rows. Color = intensity using the inferno colormap:
    black = off, dark red = dim, orange = medium, yellow/white = full.
    A white vertical playhead sweeps across during playback.

  WATERFALL MODE (check "Waterfall"):
    2D ridge plot — each electrode gets its own horizontal band with a
    filled waveform showing intensity. Colored by electrode. Useful for
    seeing individual electrode waveform shapes and comparing them.

  FOLLOW MODE (enabled by default):
    The dimmer strip auto-scrolls to keep a window centered on the
    playhead during playback. Adjust the "Window" size (in seconds)
    to control how much context is visible. Set to 5s for detail,
    20s for overview. The waveform scrolls past like an oscilloscope.

    When Follow is off, use the manual Zoom and scroll controls.

PANEL TOGGLES:
  The "Show" panel in the controls row lets you turn each panel on/off
  AND switch between processing modes for the displayed data:
    [x] Trajectory   [x] Bars   [x] Dimmer   |   [x] 3D   [x] Waterfall
                                              |   [x] Trochoid   [x] Snap-honest   [x] Spatial

  Render-only toggles (don't recompute data):
    Trajectory / Bars / Dimmer  Show or hide that panel.
    3D                          2D (default) or 3D trajectory view.
    Waterfall                   Heatmap (default) or stacked waterfall
                                for the dimmer.

  Data-changing toggles (re-prepare the trajectory and electrode signals):
    Trochoid       Apply trochoid quantization (snap input to N curve-
                   derived levels) before deriving alpha/beta and E1-E4.
                   Defaults to whatever the global config has when you
                   opened the viewer; can be flipped here for A/B
                   comparison without touching the Trochoid tab.
    Snap-honest    Only meaningful when Trochoid is on. Off (default) =
                   linear interpolation between funscript samples
                   (matches what the playback device actually does).
                   On = zero-order hold (bars/dimmer jump between snapped
                   levels so the quantization is visually obvious).
    Spatial        Use trochoid-spatial mapping for E1-E4 instead of the
                   per-axis response curves. Defaults to the global
                   trochoid_spatial.enabled config flag. When on, the
                   four electrodes are driven by the curve geometry
                   (see section 14).

  Disabling panels you don't need improves animation performance:
    All panels:      ~55-60 FPS
    Dimmer only:     ~100 FPS
    Trajectory only: ~80 FPS

  At least one panel must be enabled.

DIMMER ANTI-ALIASING:
  Long files combined with quantization can produce a "forest of vertical
  lines" in the dimmer because the heatmap downsamples a dense matrix
  into a smaller pixel grid. The dimmer now auto-pools the matrix
  columns down to ≤2400 (max-pool, so peaks survive). When this happens
  you'll see a console line like:
    [dimmer] downsampled 30000 -> 2308 cols (chunk=13) for display anti-aliasing
  This makes the rendering readable; the actual signal data on disk is
  unaffected.

NaN GUARD:
  Any non-finite values in the E1-E4 channels are replaced with 0.0
  before rendering (and the count is logged), so stray "magenta" pixels
  from the inferno colormap's bad-value rendering can't appear.

ZOOM (dimmer strip):
  Zoom: [400] %   up to 8000%
  At 100%: full timeline. At 8000%: sample-level detail.
  A scrollbar appears when zoomed in for manual panning.
  During playback with Follow on, the view auto-centers on the playhead.

PLAYBACK CONTROLS:
  Play / Pause       Start/stop animation. Loops at the end.
  Timeline scrubber  Drag to jump to any point.
  Time entry         Type a number (seconds) and press Enter to jump
                     directly to that time.
  Speed              Playback speed: 0.25x, 0.5x, 1x, 2x, 4x.

DATA SOURCE:
  If a .funscript is loaded, the viewer uses it with your current settings
  (algorithm, response curves, modulation, cascade, etc.).
  If no file is loaded, it generates a synthetic 10-second demo.
  Settings are read from the UI at the moment you open the viewer.

================================================================================
12. SIGNAL ANALYZER
================================================================================

Click the "Signal Analyzer" button in the bottom bar. It examines your
loaded funscript and recommends optimal settings based on signal
characteristics.

TROCHOID TOGGLE:
  At the top of the analyzer window, next to the source label, there's
  a checkbox: "Apply trochoid quantization to source". When on, the
  loaded funscript is quantized BEFORE metrics are computed — so the
  summary, classification, charts, and recommendations all reflect
  the quantized signal that the processor will actually produce.
  Defaults to whatever the global config has when the analyzer opens;
  toggling it re-runs the full analysis. The source label gains a
  "[trochoid: hypo, N=23]" suffix when the override is active.

WHAT IT MEASURES:

  Stroke Metrics:
    - Stroke count and strokes per minute (SPM)
    - Median stroke rate (Hz) and rate variability
    - Stroke amplitude distribution (mean, P25, P75)

  Temporal Metrics:
    - Total and active duration
    - Rest fraction (time where speed < 5% of max for > 2 seconds)
    - Rest period count and locations
    - Mean active segment length

  Speed Metrics:
    - Speed percentiles (P25, P50, P75, P95, max)

  Frequency Metrics:
    - Dominant frequency (FFT-based)
    - High-frequency energy ratio

  Position Metrics:
    - Position distribution histogram
    - Effective position range (P5 to P95)

CLASSIFICATION:
  Based on the metrics, the script is classified:
    Pace:        slow (<30 SPM), moderate (30-80), fast (80-150), very fast
    Variability: steady, moderate, highly variable
    Intensity:   subtle, moderate, intense
  Example: "FAST, MODERATE VARIABILITY — 120 SPM, moderate pacing..."

RECOMMENDATIONS:
  The analyzer produces 9-12 specific setting recommendations:

  Speed Method:
    High variability -> savgol (preserves peaks)
    Low variability  -> rolling_average (steady signal)
    Moderate         -> ema (smooth response)

  Speed Window:
    Approximately 2 stroke cycles at the median rate.
    Clamped to [1, 30] seconds and to 80% of mean active segment length.

  Accel Window:
    60% of the recommended speed window, clamped to [1, 10].

  Interpolation Interval:
    Fast signal (p95 speed > 3) -> 0.01 (dense sampling)
    Slow signal (p95 speed < 0.5) -> 0.05 (coarser OK)
    Moderate -> 0.02

  Savgol Options (when savgol is recommended):
    Polynomial order: 4 if high-frequency content, else 3.
    Fit window factor: scales inversely with variability.
    Post-smoothing: scales with variability.

  Rest Level:
    High rest (>30%) -> 0.3 (low for contrast)
    Low rest (<5%)   -> 0.5 (higher baseline)
    Moderate         -> 0.4

  Modulation:
    Frequency = sub-harmonic of stroke rate (rate x 0.3).
    Depth: small strokes -> 0.25, big strokes -> 0.08, moderate -> 0.15.

  Physical Model:
    Speed = 200 + 200 x stroke_rate_hz, clamped to [100, 1000].
    Direction: variable pacing -> "follow signal", steady -> fixed.

VISUALIZATIONS (4 charts):
  1. Position Distribution  — where the signal spends time
  2. Stroke Amplitude       — histogram of per-stroke amplitudes
  3. Instantaneous Speed    — speed over time, rest periods shaded
  4. Stroke Rate            — local SPM over time with average line

APPLYING RECOMMENDATIONS:
  The table shows: Setting | Current | Recommended | Reason
  Settings that differ from current are highlighted in red.

  Apply All:       Writes all recommendations to the config.
  Apply Selected:  Only applies rows you've selected in the table.
  Close:           Closes without applying.

  After applying, the table refreshes — matched settings are no longer red.

  IMPORTANT: Recommendations are a starting point, not final values.
  Always reprocess and test in restim after applying. Tune by feel.

================================================================================
13. CURVE QUANTIZATION (TROCHOID TAB)
================================================================================

Snap every position value in your input funscript to one of N discrete
levels derived from a parametric curve. Useful for creating rhythmic,
mechanical-feeling stim patterns where the position only ever lands on
specific "rungs", and for crafting unusual non-uniform stairstep responses
based on geometric curve math (hypotrochoid, rose, butterfly, etc.).

When enabled, quantization is the FIRST processing step — applied to the
main funscript before speed, alpha/beta, E1-E4, frequency, volume, and
pulse derivations. Every downstream output therefore inherits the snap.

WHERE IT FITS IN THE PIPELINE:

    Input .funscript
        |
        v
    [Curve Quantization]   <-- pre-pipeline, applied here
        |
        v
    Speed / Alpha / Beta / E1-E4 / Frequency / Volume / Pulse
        |
        v
    Output files

THE CONTROLS

  Enable curve quantization
    Master toggle. Off = pipeline runs unchanged.

  Curve family
    Picks which parametric curve generates the level set. Each family has
    its own parameter pane below the family selector. Switching family
    keeps the parameters you typed for the previous one (per-family Vars
    are persistent within a session and saved to config).

  Number of points (N)   2-256, default 23
    The curve is sampled at N evenly spaced theta values. Each sample
    becomes one quantization level. After projection some levels may
    coincide; the actual count is shown in the preview as
    "N unique" — e.g. "23 unique" or "21 unique" if there were duplicates.

  Projection             radius | y | x
    A 2D curve must reduce to 1D to give level values. The N curve points
    are projected to a single scalar:
      radius:  sqrt(x^2 + y^2)  — symmetric, always positive (default).
      y:       y-coordinate     — emphasizes vertical structure.
      x:       x-coordinate     — emphasizes horizontal structure.
    The N projected scalars are then normalized to [0, 1] and used as
    quantization levels. Different projections of the same curve produce
    very different level distributions.

  Deduplicate consecutive identical samples
    After snapping, neighboring samples often land on the same level.
    By default these are kept (faithful to the original time grid).
    Enable this option to drop redundant interior samples in each
    "plateau", keeping only the first and last sample of each value-run.
    Why keep both: playback devices linearly interpolate between
    consecutive funscript samples. Keeping the LAST sample of a plateau
    ensures the device holds the position until the next change instead
    of sloping across the plateau. The first/last pair acts as the
    bookends of the held value.
    Effect: typically cuts sample count by 50-80% with no audible change
    in playback. Useful for keeping device buffers responsive on long
    scripts.

THE CURVE FAMILIES

  hypo — Hypotrochoid (rolling inside)
    x(t) = (R - r) cos(t) + d cos(((R - r)/r) t)
    y(t) = (R - r) sin(t) - d sin(((R - r)/r) t)

    The hypotrochoid is the path traced by a pen attached to a small
    circle of radius r as it rolls without slipping INSIDE a larger
    fixed circle of radius R. The pen sits at distance d from the
    rolling circle's center.

    Params:
      R (outer radius, > 0)
        Sets the bounding container size. Larger R = wider overall
        pattern. The R/r ratio is what really shapes the curve:
          - Integer ratios produce closed curves (the pen returns to
            its start). Example: R=5, r=3 closes after 3 turns of the
            outer circle.
          - Irrational ratios trace forever without ever closing.
          - The number of distinct lobes/petals is approximately
            R / gcd(R, r) for integer ratios.

      r (rolling radius, > 0, ≠ R)
        Smaller r relative to R = more lobes/petals.
          - r ≈ R/3 to R/5: classic Spirograph-style multi-petal patterns.
          - r ≈ R/2: simple bipolar patterns.
          - r close to R: soft, almost-circular single-loop shapes.

      d (pen offset)
        Three distinct regimes:
          1. d = r:  TRUE HYPOCYCLOID — sharp pointed cusps where the
                     pen touches the outer circle (e.g. astroid for R=4,
                     r=1).
          2. d < r:  CURTATE TROCHOID — pen is inside the rolling
                     circle. Rounded loops, no cusps. The smaller d/r,
                     the more circular the result.
          3. d > r:  PROLATE TROCHOID — pen is outside the rolling
                     circle. Self-intersecting loops/knots.

    Classic Spirograph patterns. The N quantization points trace evenly
    around this curve, so the radius (sqrt(x^2+y^2)) projection gives
    levels clustered around the petal radii — strong "rest" levels with
    a few accent peaks.

    Try: R=5, r=3, d=2 (default — gentle rounded multi-loop)
         R=8, r=3, d=5 (pronounced loops, prolate regime)
         R=4, r=1, d=1 (4-cusped astroid — very angular levels)
         R=5, r=2, d=2 (5-pointed quasi-star)

  epi — Epitrochoid (rolling outside, "hypertrochoid")
    x(t) = (R + r) cos(t) - d cos(((R + r)/r) t)
    y(t) = (R + r) sin(t) - d sin(((R + r)/r) t)

    Same idea as hypo, but the rolling circle rolls around the OUTSIDE
    of the fixed circle. R, r, d have the same roles and the same three
    d-regimes (cusps / curtate / prolate) as hypo. Pattern lives outside
    the fixed circle — looks like daisy petals, gear-tooth shapes, or
    flowery rosettes.

    Try: R=5, r=3, d=2 (default — gentle rosette)
         R=4, r=1, d=2 (cardioid-like with one big lobe)
         R=3, r=1, d=1 (nephroid — 2 cusps)
         R=6, r=1, d=1.5 (6-petal flower)

  rose — Rose curve   r = a * cos(k * t)
    Params: a (amplitude), k (petal frequency).
    Petal count: k petals if k is odd, 2k petals if even.
    The level distribution clusters near 0 (when r ~ 0) and 1
    (at petal tips) — produces a "soft floor + accent peaks" feel.
    Try: a=1, k=5 (5 petals) or a=1, k=4 (8 petals).

  lissajous — Lissajous figure
    x(t) = A * sin(a*t + delta),   y(t) = B * sin(b*t)
    Params: A, B (amplitudes), a, b (frequencies), delta (phase rad).
    a:b ratio determines the figure's structure. delta rotates it.
    Try: A=B=1, a=3, b=2, delta=pi/2 (3:2 figure).
    Try: A=B=1, a=5, b=4, delta=0 (5:4 lattice).

  butterfly — Temple Fay's butterfly curve
    r(t) = e^cos(t) - 2*cos(4t) + sin(t/12)^5
    x(t) = scale * r * sin(t),  y(t) = scale * r * cos(t)
    Sampled over [0, 12*pi) — the full butterfly traces over six full
    rotations of t. Params: scale only.
    Highly non-uniform level distribution; perfect for organic "natural"
    feeling quantization with lots of values clustered near a "rest"
    radius and a few extreme reaches.

  superformula — Gielis superformula
    r(t) = ((|cos(m*t/4)/a|)^n2 + (|sin(m*t/4)/b|)^n3)^(-1/n1)
    Params: a, b, m (symmetry order), n1, n2, n3 (shape exponents).
    Extremely flexible — can produce circles, polygons, stars, blobs,
    flowers, pinched shapes, by varying the exponents.
    Try: a=b=1, m=6, n1=1, n2=7, n3=8 (default — soft hexagonal flower).
    Try: a=b=1, m=4, n1=12, n2=15, n3=15 (rounded square / supershape).

  custom — User-entered x(t) and y(t)
    Enter two expressions in numpy syntax. Available functions:
      sin cos tan asin acos atan atan2 sinh cosh tanh
      exp log log2 log10 sqrt cbrt abs sign floor ceil round
      pow minimum maximum
    Available constants: pi, e, tau (= 2*pi).
    The variable t ranges over [0, 2*pi).
    Examples:
      x(t) = sin(3*t) + 0.5*sin(7*t)        y(t) = cos(2*t)
      x(t) = t * cos(t)                     y(t) = t * sin(t)        (spiral)
      x(t) = sin(t) * (1 + 0.3*cos(5*t))    y(t) = cos(t) * (1 + 0.3*cos(5*t))   (flower)

    SECURITY: expressions are evaluated in a sandboxed namespace with
    __builtins__ disabled. Imports, file I/O, and attribute access via
    dunder names ("__") are rejected. Safe for local use; do not paste
    untrusted expressions if you don't trust their author.

LIVE PREVIEW

  Three subplots in the Preview panel:

    Top-left:  The curve geometry in 2D, with the N sampled points
               highlighted as red dots.

    Top-right: A "rug plot" of the N normalized quantization levels
               between 0 and 1. Title shows how many unique levels
               survived projection (some may coincide).

    Bottom:    "Signal before/after" — a fragment (first 10 sec) of the
               loaded input funscript with the raw signal overlaid in
               grey and the quantized signal in black, with horizontal
               red lines marking the level grid.
               Title shows zoom %, render mode, and dedup status.

  Interactive controls for the bottom subplot:

    Signal Zoom   100-8000 %. Combobox with common values, or type your
                  own and press Enter. Scrollbar appears below the figure
                  when zoom > 100 %.

    Reset View    Zoom 100 % + scroll 0.

    Clear Playhead   Removes the green vertical playhead line.

    Show as: Interpolated / Step
      DEFAULT: Interpolated. Plots the snapped signal as a normal line
        with sample points marked as dots. THIS IS WHAT THE DEVICE
        ACTUALLY DOES — funscript playback linearly interpolates between
        consecutive samples, so the on-device behavior is sloped lines
        between successive snapped values, not square steps.
      Step: Plots the snapped signal as a step function (flat held value
        with vertical jumps). Useful for visualizing the snap edges,
        but NOT how the device will reproduce the signal.

    Mouse interactions (signal subplot only):
      Left-click           Set the playhead at that time. Label updates
                           with the raw and snapped values at that moment.
      Left-click + drag    Pan horizontally. Respects the current zoom.
      Scroll wheel         Zoom in/out, anchored on the cursor position.
      Right-click          Clear the playhead.

  All three subplots refresh live when you change family, N, projection,
  any family parameter, or the dedup toggle — and the change also
  propagates to the main 4P Waveform Preview so you can see the
  quantization affecting the E1-E4 outputs in real time.

ABOUT "DIGITAL-LOOKING" OUTPUT

  Quantization makes the position only land on N specific values, so
  consecutive samples that snap to the same value form flat plateaus.
  In the preview's Step mode this looks like a square wave. In reality
  the device interpolates between samples — so the actual playback will
  smoothly ramp from one snapped value to the next over the time gap
  between them, then hold flat across plateaus. The Interpolated render
  mode shows this truthful view.

  If consecutive samples snap to DIFFERENT levels (because they're far
  apart in input value), the device will linearly slide between them
  over the time delta between samples. If your input has dense samples
  (60+ Hz) and the snap changes every sample, those slides happen so
  fast they FEEL near-instantaneous — that's the closest you get to
  true digital character. Lower input density or stronger plateaus
  give a more "stairstep" feel.

  Tuning levers for the digital/analog spectrum:
    More N + low input density   = analog-like (small steps, close samples)
    Few N + high input density   = digital-like (big steps, fast slides)
    Dedup ON                     = honest plateau hold
    Step render mode             = false visual sharpness
    Interpolated render mode     = truthful

USAGE RECIPES

  Recipe 1 — "Mechanical 7-position lock"
    Family:        hypo (or any)
    Points:        7
    Projection:    radius
    Use case:      Force a stroke into 7 discrete positions. Strokes will
                   feel ratcheted onto specific levels. Try N=5, 7, 11
                   for distinctly "digital" feel.

  Recipe 2 — "Subtle texture"
    Family:        hypo
    Points:        64
    Projection:    radius
    Dedup:         off
    Use case:      Many levels means snap differences are tiny. Adds
                   subtle quantization "tooth" without changing the
                   overall stroke shape. Useful for taking the edge off
                   over-smooth signals.

  Recipe 3 — "Flower clustering"
    Family:        rose
    Params:        a=1, k=5
    Points:        40
    Projection:    radius
    Use case:      Rose curves cluster levels near 0 (most petals are
                   short) with a few peaks. Strokes spend most time near
                   low positions with occasional reaches to specific
                   higher levels. Sounds esoteric — try it.

  Recipe 4 — "Asymmetric Lissajous"
    Family:        lissajous
    Params:        A=1, B=1, a=5, b=3, delta=1.0
    Projection:    y
    Points:        32
    Use case:      Y-projection of an asymmetric Lissajous makes a
                   noticeably non-uniform level grid. Combined with
                   dedup, gives uneven "rhythm" to held positions.

  Recipe 5 — "Butterfly with custom levels"
    Family:        butterfly
    Params:        scale=1.0
    Projection:    radius
    Points:        48
    Dedup:         on
    Use case:      Many duplicate levels collapse to a smaller unique
                   set; preview will show e.g. "32 unique". Wide sample
                   reduction after dedup. Organic-feeling steps.

  Recipe 6 — "Custom signature"
    Family:        custom
    x(t):          sin(t) * (1 + 0.4*sin(7*t))
    y(t):          cos(t) * (1 + 0.4*sin(7*t))
    Projection:    radius
    Points:        23
    Use case:      A 7-fold-symmetric flower. Levels cluster at the
                   inner radius with seven distinct peaks. Substitute
                   the 7 with another small odd number for more/fewer
                   accent levels.

CONFIG STORAGE

  Saved under "trochoid_quantization" in config.json:
    enabled               bool
    n_points              int
    projection            "radius" | "y" | "x"
    family                e.g. "hypo", "rose", "butterfly", ...
    deduplicate_holds     bool
    params_by_family      {family_name: {param: value, ...}, ...}

  Per-family params are stored separately so switching family doesn't
  lose values. The legacy flat keys (curve_type, R, r, d) from earlier
  versions are auto-migrated into params_by_family on first load.

NOTE ON DENSIFICATION

  Unlike Trochoid Spatial (section 14) and Traveling Wave (section 15),
  Trochoid Quantization does NOT resample the output to a denser grid.
  It's a snap-to-level transform: each input sample maps to the nearest
  level, preserving the input's timing exactly. Densifying would just
  add redundant hold samples without changing the information — the
  discrete stair-step is the whole point.

================================================================================
14. TROCHOID SPATIAL TAB — CURVE-DRIVEN E1-E4
================================================================================

A second way to use parametric curves with the E1-E4 system. Where the
"Trochoid" tab (section 13) SNAPS the INPUT signal to discrete curve-derived
levels, this tab uses the curve geometry directly to DRIVE the four
electrodes — each electrode represents a compass direction, and the
2D curve point determines how loud each electrode is at any moment.

When enabled, this OVERRIDES the response-curve E1-E4 generation in the
Motion Axis (4P) tab. The .e1/.e2/.e3/.e4 funscripts that the processor
writes will come from this spatial mapping instead of from per-axis
response curves.

CONCEPTUAL MODEL

Imagine four electrodes arranged in a circle around you:

           E2 (90°)
              |
   E3 (180°) -+- E1 (0°)
              |
           E4 (270°)

Now imagine a moving point — the "pen" of a Spirograph. As input position
sweeps from 0 to 1, the pen traces along the chosen 2D curve (hypotrochoid,
rose, butterfly, ...). At each moment, the pen has a position (x, y) in
the plane. We compute "how much" each electrode should fire from the
relationship between the pen's position and that electrode's compass
direction. As the pen orbits, the sensation moves around the four
electrodes — like a virtual stim spot dancing through space.

Different curves produce dramatically different motion patterns. A simple
hypotrochoid traces a closed flower; a rose curve sweeps in/out through
petals; a butterfly traces an organic, asymmetric path. Each yields a
unique spatial sensation pattern.

THE CONTROLS

  Enable trochoid-spatial E1-E4 generation
    Master toggle. When on, the processor uses the spatial mapping for
    .e1/.e2/.e3/.e4 instead of running each axis through its response
    curve. Default OFF.

  Curve family
    Same family list as the Trochoid tab — hypo, epi, rose, lissajous,
    butterfly, superformula, custom. The chosen curve provides the
    pen's path. See section 13 for full equations and parameter meaning.

  Mapping        directional | distance | amplitude
    How the pen position becomes per-electrode intensity. See "Mapping
    modes" below for the math and feel of each.

  Sharpness        ≥ 0.01, default 1.0
    Cosine exponent applied in directional and amplitude modes. Higher
    sharpness = more selective; the electrode lights only when the pen
    points nearly straight at it.
      0.5 — very soft, broad activation; multiple electrodes fire at once
      1.0 — natural cosine; smooth transitions
      2.0 — moderate selectivity
      4.0 — sharp; each electrode fires only in its narrow direction
      8.0 — laser-focused; near-binary on/off

  Cycles per stroke        default 1.0
    How many full curve traversals happen per 0→1 input change. Controls
    how quickly the pen orbits as the input sweeps.
      0.5 — slow; one stroke covers half the curve, sensation drifts
      1.0 — natural; one stroke = one full curve trace
      3.0 — busy; one stroke triggers three full orbits, fast electrode flicker
      10.0 — frantic; near-buzzing rotation per stroke

  Electrode angles (E1, E2, E3, E4) in degrees
    Compass positions of the four electrodes. Default 0/90/180/270 — a
    cardinal layout (E1=East, E2=North, E3=West, E4=South). Edit to
    rotate the whole layout (e.g. 45/135/225/315 for diagonals) or to
    cluster electrodes (e.g. 0/30/60/90 to bias activation toward one
    quadrant).

  Family parameters (R, r, d / a, k / etc.)
    Same per-family curve parameters as the Trochoid tab (section 13),
    with short inline hints and hover tooltips.

MAPPING MODES — THE MATH

For each input sample p ∈ [0, 1]:
  1. Compute t = theta_max × cycles_per_stroke × p
     (theta_max is the family's natural sweep range — 2π for most,
     12π for butterfly)
  2. Evaluate the curve at t to get (x, y)
  3. Normalize the curve into a unit-radius reference so the math is
     comparable across families: x_n = x / r_max, y_n = y / r_max,
     where r_max is the curve's maximum radius.
  4. For each electrode at compass angle θ_k, compute intensity i_k
     using the chosen mapping rule:

  ── DIRECTIONAL (default) ──────────────────────────────────────
    angle = atan2(y_n, x_n)               # angle of pen from origin
    i_k   = max(0, cos(angle - θ_k)) ^ sharpness

    What you feel: as the pen orbits the origin, the sensation rotates
    around the electrode array. Each electrode lights up when the pen
    is "in its direction". With sharpness=1, two adjacent electrodes
    overlap (smooth fade between them). With sharpness=4+, only the
    electrode directly aligned with the pen fires strongly.

    Best for: rose curves, pentagram-like hypotrochoids, anything with
    clear directional reach. The sensation feels like a moving spot
    of focus traversing the array.

  ── DISTANCE ────────────────────────────────────────────────────
    For each electrode, place it at (cos(θ_k), sin(θ_k)) on the unit
    circle.
    d   = ‖(x_n, y_n) − (cos(θ_k), sin(θ_k))‖
    i_k = max(0, 1 − d/2) ^ sharpness

    What you feel: each electrode lights up when the pen physically
    approaches its position on the unit circle. Unlike directional,
    this rewards both correct angle AND proximity (radius matters).
    Pen at origin → all electrodes equally "1 unit away" → similar
    medium intensities. Pen pushed out toward an electrode → that
    one peaks while opposites stay dark.

    Best for: curves that loiter at specific radii. Rose curves with
    distance mapping concentrate energy at the petal tips. Lissajous
    figures highlight the lattice intersections.

  ── AMPLITUDE ──────────────────────────────────────────────────
    angle = atan2(y_n, x_n)
    r_n   = ‖(x_n, y_n)‖              # normalized radius
    i_k   = r_n × max(0, cos(angle - θ_k)) ^ sharpness

    Combination of directional + radius weighting. Even when the pen
    is pointing toward an electrode, intensity is scaled down if the
    pen is near origin.

    What you feel: the rotating sensation of directional, but with
    intensity that "breathes" — strongest at the curve's outer
    extremes, quieter when the curve passes near center. Adds a
    natural emphasis to peaks of motion.

    Best for: emphasizing the dramatic moments of complex curves.
    Butterfly + amplitude shows when the pen reaches the wing tips.

LIVE PREVIEW — THREE PANELS

  Top-left: 2D curve geometry
    The full curve, with the four electrode positions marked as
    colored dots on the unit circle (E1 blue, E2 orange, E3 green,
    E4 red). A dashed grey unit circle is drawn for reference.

  Top-right: Intensity vs input position
    Four lines (one per electrode) showing how each electrode's
    intensity varies as input sweeps 0 → 1. This is the "channel
    response" — exactly what each electrode will do in response to
    a smooth input ramp. Useful for tuning sharpness and cycles:
    you'll see the activation patterns directly.

  Bottom: Time-domain preview
    Using the loaded input file (or a synthetic sine if no file is
    loaded), shows what the input signal looks like (faint grey)
    and what each electrode would do over time (colored lines).
    This is the closest visual approximation of what the device
    will receive.

All three panels refresh live as you change family, mapping, sharpness,
cycles, electrode angles, or family parameters. Changes also propagate
to the Motion Axis (4P) Waveform Preview, so you can see the override
in context with the source signal.

TROCHOID vs TROCHOID SPATIAL — WHEN TO USE WHICH

  Trochoid Quantization (section 13):
    - Snaps the INPUT signal to N discrete curve-derived levels
    - Affects EVERYTHING downstream (alpha/beta, E1-E4, frequency,
      volume, pulse) because all those derive from the snapped main
    - Best for: "mechanical lock" feel; rhythmic, stepped motion;
      forcing position into specific rungs

  Trochoid Spatial (section 14):
    - Replaces the E1-E4 derivation entirely
    - Doesn't change the input signal — alpha/beta and other
      derivations work from the original main funscript
    - Best for: "rotating sensation" feel; spatial choreography
      across the four electrodes; making complex curve geometry
      directly drive the pattern

  Both can be on at the same time:
    - Quantization snaps the input first
    - Spatial then maps the (snapped) input through the curve
      geometry to produce E1-E4
    - Result: discrete-level rotation through the spatial pattern

USAGE RECIPES

  Recipe 1 — "Rotating spotlight" (smooth orbit)
    Family:    rose, a=1, k=5
    Mapping:   directional
    Sharpness: 2.0
    Cycles:    1.0
    Use case:  As input sweeps a stroke, the sensation rotates once
               around the electrode array, visiting each electrode in
               turn. Smooth and clearly perceptible directional motion.

  Recipe 2 — "Petal punch" (focused peaks)
    Family:    rose, a=1, k=5
    Mapping:   distance
    Sharpness: 4.0
    Cycles:    1.0
    Use case:  Each rose petal reaches toward a specific compass
               direction; only the matching electrode lights up at
               the petal tip. Five distinct "punches" per stroke.

  Recipe 3 — "Hypotrochoid orbit" (multi-loop dance)
    Family:    hypo, R=5, r=3, d=2
    Mapping:   directional
    Sharpness: 2.5
    Cycles:    1.0
    Use case:  Complex orbital motion; the pen dances through several
               internal loops per stroke, lighting electrodes in
               non-trivial sequences.

  Recipe 4 — "Butterfly wings" (asymmetric reach)
    Family:    butterfly, scale=1.0
    Mapping:   amplitude
    Sharpness: 3.0
    Cycles:    0.5
    Use case:  The butterfly traces wings reaching out at specific
               angles. Amplitude mode emphasizes the wing-tip moments,
               so the sensation surges when the pen reaches its
               extremes. Half-cycle covers the curve over a stroke.

  Recipe 5 — "Fast cardinal flicker"
    Family:    hypo or any
    Mapping:   directional
    Sharpness: 6.0
    Cycles:    8.0
    Use case:  Each input stroke triggers many full curve traversals,
               and high sharpness ensures only one electrode at a time.
               Result: rapid sequential firing across electrodes —
               feels like a circular buzz.

  Recipe 6 — "Diagonal layout"
    Family:    hypo, default
    Mapping:   directional
    Sharpness: 1.5
    Electrode angles: 45 / 135 / 225 / 315
    Use case:  Same hypotrochoid pattern but rotated 45° — useful when
               your physical electrode mounting is diagonal rather than
               cardinal. The pattern feel rotates with the layout.

  Recipe 7 — "Custom expression"
    Family:    custom
    x(t) = sin(t) * (1 + 0.4*cos(7*t))
    y(t) = cos(t) * (1 + 0.4*cos(7*t))
    Mapping:   amplitude
    Sharpness: 3.0
    Cycles:    1.0
    Use case:  A 7-fold flower with seven distinct directional surges
               per stroke. Substitute the 7 with another small odd
               number for more/fewer accent moments.

CONFIG STORAGE

Saved under "trochoid_spatial" in config.json:
    enabled              bool
    family               e.g. "hypo", "rose", "butterfly", ...
    mapping              "directional" | "distance" | "amplitude"
    sharpness            float ≥ 0.01
    cycles_per_unit      float (cycles per 0→1 input change)
    electrode_angles_deg list of 4 floats (compass angles)
    params_by_family     {family_name: {param: value, ...}, ...}

Per-family params are stored separately so switching family doesn't
lose values.

OUTPUT DENSIFICATION

  `generate_spatial_funscripts` linearly resamples the input to
  60 Hz before evaluating the curve mapping, then writes the dense
  output files. This matters for curves with many lobes or high
  `cycles_per_unit` values: between two sparse input samples (typical
  funscripts run 8-30 Hz) the curve can traverse significant arc,
  producing intensity variation that would otherwise be aliased
  away. Without densification a rose(k=5, cycles=4) mapped through
  an 8 Hz funscript can come out visually identical to the input.
  With 60 Hz densification, the per-lobe detail is preserved in the
  saved .e1-.e4 files. Pass `densify_hz=0` to the API for the old
  behavior.

NOTES

  - When trochoid_spatial.enabled is true, the response-curve motion
    axis generation in the Motion Axis (4P) tab is SKIPPED. You don't
    need to disable axes in that tab — the spatial generation produces
    all four files unconditionally.
  - The spatial mapping does NOT touch alpha/beta, frequency, volume,
    pulse, or the prostate channels. Those are still derived from the
    (possibly trochoid-quantized) main funscript via the standard
    pipeline. Only the four .e1/.e2/.e3/.e4 files come from the
    spatial mapping.
  - The Animation Viewer has a "Spatial" toggle in its Show panel that
    switches the live trajectory/bars/dimmer between the response-curve
    view and the spatial-mapping view. Defaults to whatever the global
    config has when the viewer is opened.

================================================================================
15. TRAVELING WAVE TAB — LINEAR/AXIAL E1-E4
================================================================================

A THIRD E1-E4 generator, alongside the response-curve Motion Axis (4P)
and Trochoid Spatial. Where the others are either per-axis curves
(section 7) or a 2D radial projection onto compass-angle electrodes
(section 14), Traveling Wave treats the four electrodes as LINEAR
POSITIONS ALONG A SHAFT and moves a wave crest along that shaft at
its own clock. Each electrode fires when the crest passes close to
its position.

When Traveling Wave is enabled it takes the HIGHEST PRIORITY in the
processor — both Trochoid Spatial and the Motion Axis response curves
are skipped for E1-E4.

HOW THE WAVE WORKS

  For each electrode at shaft position p_i in [0, 1]:

      intensity_i(t) = envelope(t) · max(0, 1 − |crest_pos(t) − p_i|
                                               / wave_width) ^ sharpness

  The crest advances along the shaft independently of the input
  signal. The input y modulates the envelope (amplitude) and can
  optionally modulate the wave speed.

PARAMETERS

  Enable traveling-wave E1-E4 generation
    Master toggle. When on, writes e1-e4 from this model and skips
    spatial + response-curve paths.

  Direction
    How the crest moves along the shaft.
      one_way_up        Always base → tip, wrapping at the tip.
      one_way_down      Always tip → base, wrapping at the base.
      bounce            Ping-pongs between base and tip.
      signal_direction  Crest moves base → tip on up-strokes of the
                        input signal and tip → base on down-strokes.
                        The direction flips with the sign of the
                        input's smoothed derivative.
      signal_position   Crest IS the input signal — crest_pos(t) =
                        y(t). The "wave" becomes a position-driven
                        spotlight that lights whichever electrode
                        the signal is currently closest to. Tightest
                        funscript sync available; wave_speed_hz and
                        speed_mod are ignored in this mode. Width and
                        sharpness still control the kernel shape.

  Envelope
    How the input y modulates the crest's amplitude.
      constant     Envelope = 1 always. Pure wave regardless of
                   input. Use for continuous pulse patterns.
      input        Envelope = y(t). Amplitude tracks the input.
                   Wave dies at y=0, full at y=1.
      input_speed  Envelope = |dy/dt| normalized to its 95th
                   percentile. Wave fires during motion, silent
                   when held. Great for speed-driven sensations.
      abs_center   Envelope = 2 · |y − 0.5|. Peaks at the extremes
                   (y=0 or y=1), silent at mid-stroke.

  Wave speed (Hz)
    Full-shaft traversals per second. 1.0 Hz = one base-to-tip
    traversal per second. 3 Hz = three per second (fast buzz).

  Wave width
    Half-width of the triangular kernel in shaft units [0-1].
    Smaller = sharper, more localized "zap" as the crest passes.
    Larger = broader overlap, multiple electrodes fire at once.
    Default 0.18.

  Speed modulation
    How much the input modulates the effective wave speed:
        effective_speed = wave_speed · (1 + speed_mod · (y − 0.5))
    0 = constant speed (default). 1.0 = wave runs half-speed at y=0
    and 1.5x speed at y=1. Useful for "faster wave on deep strokes".

  Sharpness
    Exponent applied to the triangular kernel. 1 = linear triangle.
    Higher values narrow the peak and flatten the skirts — each
    electrode fires only when the crest is directly on it.

  Noise gate (0 - 0.5)
    Soft-threshold applied to each electrode's intensity AFTER the
    kernel. Values at or below the gate are zeroed; the remaining
    (gate, 1] range is linearly rescaled to [0, 1] so peaks still
    reach full amplitude. This is the simplest way to drop the
    noise floor — the low-level residual activation from kernel
    skirts and never-quite-zero envelopes — without re-tuning
    width/sharpness.
      0.00  disabled (raw output)
      0.10  default; kills skirt fuzz, keeps soft edges
      0.25  crisp on/off behavior
      0.40+ aggressive; only strong hits fire at all

  Exclusive (winner-take-all)
    Checkbox. When on, at each sample only the electrode with the
    HIGHEST intensity keeps its value; the other three are zeroed.
    Combined with a narrow wave_width and signal_position direction,
    this gives a clean "one electrode at a time" spotlight that
    hops as the signal sweeps past each position.

  Electrode positions (E1-E4)
    Shaft positions in [0, 1]. Default: E1=0.85 (near tip),
    descending to E4=0.25 (near base). Adjustable per device
    layout.

PER-AXIS MODULATION APPLIES

  The per-axis modulation block from the Motion Axis (4P) tab
  (section 9) applies here too. When an axis has modulation
  enabled, its traveling-wave output is passed through the same
  `apply_modulation()` LFO: the intensity envelope shrinks into
  [depth, 1-depth] and a sine at frequency_hz is added. This lets
  you overlay per-electrode textures on top of the wave — e.g.,
  8 Hz wobble on E2, 16 Hz wobble on E4.

RECIPES

  "Gentle continuous sweep"
    direction=bounce, envelope=constant, wave_speed=0.5 Hz,
    width=0.25, speed_mod=0, sharpness=1
    → Slow overlapping rollover across all electrodes, independent
    of input. Use for baseline presence.

  "Signal-following zap"
    direction=signal_direction, envelope=input, speed=3 Hz,
    width=0.08, speed_mod=0, sharpness=2
    → Sharp crest that moves with stroke direction. Feels like
    the sensation follows your motion.

  "Speed-responsive wave"
    direction=bounce, envelope=input_speed, speed=1 Hz, width=0.2,
    speed_mod=1.0, sharpness=1
    → Wave amplitude tracks how fast you're stroking, and the wave
    speeds up on deep strokes.

  "Clean spotlight" (uses signal_position + exclusive)
    direction=signal_position, envelope=constant, width=0.12,
    sharpness=2, noise_gate=0.15, exclusive=true
    → Only one electrode fires at a time, and only the one the
    funscript's y value is currently over. Speed/speed_mod are
    ignored in this direction mode. Crisp, discrete, 1-of-4 feel.

  "Quiet floor" (noise-gate demo on a smooth wave)
    direction=bounce, envelope=input, speed=1 Hz, width=0.22,
    sharpness=1.5, noise_gate=0.25
    → Same smooth traveling wave, but the kernel skirts are killed.
    Electrodes only fire when the crest is genuinely close, giving
    visibly punchier transitions between them.

OUTPUT DENSIFICATION

  `generate_wave_funscripts` linearly resamples the input to 60 Hz
  before running the wave model, then writes the dense intensity
  arrays. Without this, a typical sparse funscript (8-30 pts/sec)
  would alias out most of the wave's motion — a 4 Hz crest sampled
  at 8 Hz can end up as flat zero because every input timestamp
  happens to fall in the wave's trough. At 60 Hz the crest's full
  trajectory is captured in the saved .e1-.e4 files. Pass
  `densify_hz=0` to the API to disable.

CONFIG KEYS

Saved under "traveling_wave" in config.json:
  enabled, direction, envelope_mode, wave_speed_hz, wave_width,
  speed_mod, sharpness, velocity_window_s, noise_gate, exclusive,
  electrode_positions.

OVERRIDE PRIORITY SUMMARY (HIGHEST → LOWEST)

  1. Traveling Wave     — linear/axial crest model
  2. Trochoid Spatial   — radial/angular 2D projection
  3. Motion Axis (4P)   — per-axis response curves

Only the highest-enabled path runs for E1-E4. Everything else
(alpha/beta, frequency, volume, pulse) is unaffected.

================================================================================
16. COMPARISON VIEWER (COMPARE FUNSCRIPTS)
================================================================================

A standalone comparison tool for viewing two funscripts side by side
(or overlaid) with synchronized scrolling, a draggable playhead, and
an optional difference panel. Useful for:
  - Comparing original input vs processed output
  - Comparing two different processing settings (A/B test)
  - Spotting drift, alignment differences, or quantization effects
  - Cross-checking that a saved/loaded file matches expectations

LAUNCH

  In-app:    Click the "Compare Funscripts" button in the bottom button
             row of the main window. The currently-selected input file
             is pre-loaded into slot A; use Browse to add a slot B file.

  Standalone: From the project folder, run
                  python funscript_compare.py
              Or with one or both files pre-loaded:
                  python funscript_compare.py file_a.funscript
                  python funscript_compare.py file_a.funscript file_b.funscript

  In either case the viewer runs in the same Python process — no
  significant startup overhead, no extra interpreter spinup.

LAYOUT

  ┌─────────────────────────────────────┐
  │  A: [Browse]  filename — N samples  │
  │  B: [Browse]  filename — N samples  │
  │  ┌─────────────────────────────┐    │
  │  │   file A timeline           │    │
  │  └─────────────────────────────┘    │
  │  ┌─────────────────────────────┐    │
  │  │   file B timeline           │    │
  │  └─────────────────────────────┘    │
  │  Scrub: ──●─────────────────  12.345 s │
  │  ☐ Overlay  ☐ Difference  [Fit] [Clear] │
  │  View: 0.000 → 120.000 s   Playhead: ─ │
  └─────────────────────────────────────┘

THE TIMELINES

  Each plot shows position 0–100 over time, filled-area styling.
  File A is blue, File B is red. They share the X (time) axis, so
  zooming or panning one moves the other in lockstep.

  Above each plot, the file path and a summary appear:
      file.funscript — 1234 samples | 120.50 s

OVERLAY MODE (checkbox)

  Off (default): two stacked timelines.
  On: both signals collapse into a single subplot, with file A in blue
  and file B in red. Best for inspecting alignment — drift between the
  two signals becomes immediately visible.

DIFFERENCE PANEL (checkbox)

  Off (default): no difference panel.
  On: a third panel appears at the bottom showing (B − A) over time.
  Both signals are resampled to a common dense grid covering only the
  time range where both files exist. The panel title shows:
    Difference — RMS XX.XX | peak XX.XX
  RMS = root-mean-square of the difference (overall drift magnitude).
  peak = maximum absolute difference (biggest single-sample divergence).

  Useful for measuring how much processing changed the signal, or
  detecting that two "identical" files actually differ.

MOUSE INTERACTIONS

  Within any signal subplot:

  Left-click            Set the playhead at that time. The playhead
                        readout shows  "1.234 s   A=68.5   B=72.3"
                        (raw and B values at that moment).
  Left-click + drag     Pan the view horizontally. The other timelines
                        follow because they share the X axis. Light-
                        weight (set_xlim only) so it stays smooth on
                        long files.
  Scroll-wheel up       Zoom in, anchored on the cursor's time position
                        (the time under the cursor stays put).
  Scroll-wheel down     Zoom out, also cursor-anchored.
  Right-click           Clear the playhead.

  Buttons:
    Fit                 Reset the view to span all loaded data.
    Clear playhead      Removes the green vertical playhead line.
    Swap A↔B            Swap the two slots without re-browsing.

THE SCRUBBER (TIMELINE SLIDER)

  A horizontal slider below the canvas covers the entire loaded
  duration. Drag it to move the playhead through the file at any
  speed. The current scrubber position appears next to it as
  "12.345 s".

  Follow scrub (checkbox)
    On (default): if the playhead would scroll outside the visible
    window during a drag, the view re-centers on it so you stay
    focused on the playhead even at high zoom.
    Off: the playhead can scrub off-screen and the view stays put —
    useful when you're inspecting one zoomed region and want to see
    A/B values at faraway timestamps without losing your zoom.

  Clicking on a plot also updates the scrubber automatically — the
  slider always reflects the current playhead position.

VIEW READOUT

  Just above the playhead readout, the current visible time range
  appears as "0.000 → 120.000 s". Updates live as you pan or zoom.

PERFORMANCE NOTES

  - Toplevel popup (when launched from the main app) — no separate
    process, no startup penalty.
  - Pan and zoom use lightweight set_xlim + draw_idle, not full figure
    rebuilds. Stays smooth on multi-hour files.
  - Difference panel resamples to ≤20,000 points (capped) — bounded
    cost regardless of input length.
  - The figure is only rebuilt when overlay/difference toggles change
    or files are loaded.

================================================================================
17. SHAFT VIEWER — HORIZONTAL CYLINDER + SYNCED VIDEO
================================================================================

A physical model of a cylindrical shaft with E1-E4 arranged linearly
along its length. A red dot slides horizontally tracking the current
signal position, each electrode pulses with its current intensity,
and an optional video panel above the shaft plays in sync with the
signal. Launch from the "Shaft Viewer" button in the main app's bottom
button row.

LAYOUT

    ┌──────────────────────────────────────────────┐
    │                                              │
    │            VIDEO  (drag a file in,           │
    │            or click Browse)                  │
    │                                              │
    ├──────────────────────────────────────────────┤
    │    E4▓   E3▓    E2▓     E1▓                  │  ← horizontal shaft
    │     ●────── position dot ──────●             │    (0 = base/left,
    │                                              │     1 = tip/right)
    ├──────────────────────────────────────────────┤
    │ ▶ Play  ════●═══ 12.34 / 45.67s  Speed: 1.0x │
    │ Intensity: [auto ▾]  ☐ Trochoid  ☑ Show video│
    │ [E1 slider] [E2 slider] [E3 slider] [E4 ..]  │
    │ Video: [ file.mp4 ]  Offset [0.00] Sync here │
    └──────────────────────────────────────────────┘

Default orientation: E1 at 0.85 (near the tip/right), descending to
E4 at 0.25 (near the base/left). All four positions are adjustable
with sliders below the canvas.

ELECTRODE POSITIONS

Four sliders + numeric entries, one per electrode, in the range
[0, 1] along the shaft. 0 = base (LEFT in the horizontal view), 1 =
tip (RIGHT). Defaults: E1=0.85, E2=0.65, E3=0.45, E4=0.25 — E1 closest
to the tip, descending to E4 at the base.

Drag any slider and the band, intensity bar, and label positions
update live. Positions can be set to match your device's actual
electrode layout; common configurations:

    Evenly spaced (full length):  E1=0.85 / E2=0.65 / E3=0.45 / E4=0.25
    Tip-clustered:                E1=0.90 / E2=0.80 / E3=0.70 / E4=0.60
    Base-clustered:               E1=0.40 / E2=0.30 / E3=0.20 / E4=0.10

INTENSITY SOURCE

The dropdown "Intensity mode" selects how per-electrode intensity is
computed at each moment. Six options:

    auto        Priority-resolve using the current config:
                  1. Traveling wave (if enabled)
                  2. Trochoid-spatial mapping (if enabled)
                  3. Response curves (if Motion Axis 4P on)
                  4. Saved .e1-.e4 files (if they exist on disk)
                  5. Proximity model
    wave        Force the traveling-wave linear/axial driver. See
                section 15.
    spatial     Force the trochoid-spatial radial projection (curve
                parameterized by input, projected onto electrode
                angles). See section 14.
    curves      Force the per-axis response-curve E1-E4 from the
                Motion Axis (4P) tab.
    files       Force reading from saved .e1/.e2/.e3/.e4 funscripts
                (if they exist next to the source file).
    proximity   Geometric model only: intensity = max(0, 1 − |pos −
                electrode_pos| / reach). Ignores all processing.

"Apply trochoid quantization" checkbox snaps the main signal to N
curve-derived levels BEFORE computing E1-E4 (regardless of the
intensity mode). Defaults to whatever the global config has.

The "Intensity" summary line above the canvas always states what's
active, e.g. "Intensity: Trochoid Spatial (rose, directional) +
trochoid quantization".

REFRESH BUTTON

Re-reads the main window's current_config and recomputes the per-sample
E1-E4 intensity arrays. Click after changing settings in the Trochoid,
Trochoid Spatial, or Traveling Wave tabs to see the update in the
viewer.

SHOW VIDEO TOGGLE

A checkbox in the top control row. When off, the video panel is hidden
(removed from the layout — the shaft canvas grows to fill the freed
space). Loaded video state is preserved: toggling back on resumes
playback from exactly where it was, with the same file/offset. While
hidden, the video frame decoder is skipped every tick for a small CPU
saving.

PROXIMITY REACH

Slider + numeric readout, range 0.02–0.50, only relevant in proximity
mode (or when no spatial/curves config is active). Smaller = each
electrode fires only when the dot is very close to its position;
larger = broad overlapping activation across electrodes.

VIDEO PLAYBACK

Optional synced video. Three ways to load a video:

    1. Drop a video file onto the black panel at the top of the window
       (.mp4 / .mov / .mkv / .m4v / .avi / .webm supported via opencv).
    2. Click the "Browse…" button in the bottom controls.
    3. Automatically — when the viewer opens with a funscript loaded,
       it looks for a video file with a matching base name next to the
       funscript. E.g. `scene.funscript` + `scene.mp4` in the same
       folder loads the video automatically.

Frames are read via opencv-python and displayed with Pillow (ImageTk).
Requires both libraries; if either is missing, the video panel shows
"Video playback unavailable — install opencv-python + Pillow" and the
rest of the viewer works normally.

SYNC CONTROLS

Even with matched filenames, the video and signal sometimes start at
different reference points (a funscript with a 2 s lead-in vs a raw
video starting from frame 0 is common). Three controls handle this:

    Offset (s)    Spinbox with 0.05 s increments (or type any value,
                  press Enter). The video time for any given signal
                  time is computed as:
                      video_t = signal_t + offset
                  Positive offset = video is advanced relative to
                  signal. Negative offset = video is delayed.
    Sync here     Click this after manually aligning signal and video
                  (e.g., scrubbing to a distinctive moment and tweaking
                  the offset until they line up visually). The button
                  reads the actual current video position and sets
                  offset = actual_video_time − signal_time so subsequent
                  playback honors that alignment.
    Clear         Releases the loaded video and returns the black
                  placeholder.

Video frames are primed BEFORE playback starts (clicking ▶ Play forces
an immediate video update, so the first frame is visible before the
dot begins moving). Frame seeking is throttled to avoid re-reading
the same frame — seeks only occur when the time drift exceeds half a
video frame.

Note on seek accuracy: opencv's `CAP_PROP_POS_MSEC` seeks to the
nearest keyframe for most codecs. On heavily-compressed content you
may see ±0.5 s granularity. H.264 MP4s from most sources are keyframe-
dense enough that this is negligible.

PLAYBACK CONTROLS

    ▶ Play / ⏸ Pause   Autonomous playback at 30 FPS.
    Scrubber           Drag to jump; stays synced with playback.
    Time readout       "12.34 / 45.67 s" shows playhead / total.
    Speed              0.25x / 0.5x / 1x / 2x / 4x (combobox).
    Loops              Automatically loops from the end back to start.

The same scrubber drag updates the dot, the electrode intensity bars
AND the video frame in lockstep — useful for frame-accurate
inspection.

================================================================================
18. TROCHOID VIEWER — 2D CURVE + SHAFT SHADOW / LOBES
================================================================================

A focused viewer that pairs the 2D trochoid curve with its
"shadow" on the shaft. Launch from the "Trochoid Viewer" button
in the main app's bottom button row. Unlike the Shaft Viewer
(which shows a dot tracking the raw signal), this viewer shows
how a CHOSEN TROCHOID transforms the signal into a shaft
position — useful for previewing and A/B-ing trochoid curves.

LAYOUT

    ┌────────────────────┬──────────────────────────┐
    │                    │                          │
    │   Trochoid (2D)    │   VIDEO (drop/Browse)    │
    │    ● ← pen         ├──────────────────────────┤
    │    ╱               │  Shaft (shadow)          │
    │   ╱ trail          │   E1▓  E2▓  E3▓  E4▓     │
    │                    │   ●────── shadow dot     │
    │                    │                          │
    ├────────────────────┴──────────────────────────┤
    │ ▶ Play  ═══●═══ 12.3 / 45.0 s  Speed: 1.0x    │
    │ Family:[rose▾] Projection:[y▾] Cycles:[1.0]   │
    │ Shaft:[shadow▾] ☑ Show video                  │
    │ E1 [●════]  E2 [●════]  E3 [●════]  E4 [●════]│
    └───────────────────────────────────────────────┘

LEFT PANEL — 2D TROCHOID

The full curve (from the selected family) is drawn as a faint
reference. A red pen dot traces along it, driven by:

    theta = (y(t) · theta_max · cycles) mod theta_max

As y sweeps 0 → 1, the pen sweeps the whole curve once (more
times if Cycles > 1). A short red trail shows the last 0.6 s
of motion. Unit-circle reference drawn as a dashed grey ring.

RIGHT PANEL — SHAFT (TWO DISPLAY MODES)

Shadow mode (default):
    The pen's (x, y) is projected to a scalar via the Projection
    selector (x, y, or radius), then normalized to [0, 1] using
    the dense curve's min/max. That's the shadow's shaft position.
    A red marker on the shaft tracks the shadow, with a fading
    trail behind it.

Lobes mode:
    Peaks of the selected projection are detected with a ≥ 8%
    prominence threshold. Each peak is a "lobe" and gets an equal
    slice of shaft [0, 1]. Bars are drawn with height = peak's
    projection value and viridis coloring. A red outline highlights
    the currently-active lobe (the one containing the pen's theta).
    Lobe count = visual petal count for most curves — e.g. rose
    k=5 with projection=y gives 5 lobes.

ELECTRODE INTENSITY (VIEWER-LOCAL)

A simple proximity falloff:
    intensity_i = max(0, 1 − |shadow_x − p_i| / reach)
The "Proximity reach" slider controls the falloff width. In lobes
mode the active lobe's center is used as the shadow for this
calculation. Note: this is a SIMPLIFIED VIEWER MODEL — it is NOT
what the processor writes to the .e1-.e4 files. For accurate
per-electrode outputs, enable Trochoid Spatial (section 14) or
Traveling Wave (section 15) and process.

CONTROLS — TOP ROW

    Family        Curve: hypo, epi, rose, lissajous, butterfly,
                  superformula, custom. Rebuilds the curve + shadow
                  lookup + lobe layout.
    Projection    radius / x / y. What scalar is extracted from
                  the pen's (x, y) for the shadow AND what the
                  lobe detector finds peaks of.
    Cycles        How many curve traversals per 0→1 sweep. Higher
                  = pen flicks around the curve faster per stroke;
                  shadow sweeps the shaft more times per input
                  cycle.
    Shaft         shadow / lobes. Switches right-panel rendering
                  between continuous shadow marker and discrete
                  lobe bar-chart.
    Show video    Toggle the video panel visibility (preserves
                  video state).

CONTROLS — BOTTOM

    E1-E4 sliders + entries   Shaft position of each electrode.
    Proximity reach           Falloff half-width for electrode
                              intensity computation.
    Playback                  ▶/⏸, scrubber, time readout,
                              speed combobox (0.25x - 4x).
    Video                     Browse, Clear, Offset, Sync-here
                              (same controls as Shaft Viewer).

CURVE PARAMETERS

The per-family `R`, `r`, `d`, `a`, `k`, etc. come from
`trochoid_spatial.params_by_family` in config.json at viewer-open
time. Edit them via the Trochoid Spatial tab (section 14), then
reopen the viewer to see the reshape. (Live parameter editing in
the viewer is not yet exposed.)

CONFIG SOURCES

  Family + params      trochoid_spatial.family + params_by_family
                       (fallback to trochoid_quantization)
  Cycles default       trochoid_spatial.cycles_per_unit
  Electrode positions  traveling_wave.electrode_positions
                       (fallback to viewer defaults)

The viewer does NOT write back to config — tuning in the viewer
is display-only. To persist changes, edit the respective tabs
in the main UI.

================================================================================
19. VARIANTS (A/B/C/D WHOLE-CONFIG SNAPSHOTS)
================================================================================

A compact top-level bar sits above the parameter tabs:

    Variants:  Active: [●A  ○B  ○C  ○D]    Enabled: [☑A ☐B ☐C ☐D]
               [Save current to active slot]  [Process all enabled variants]

Each slot (A/B/C/D) stores a COMPLETE snapshot of every tab's
settings — general/speed/frequency/volume/pulse/motion-axis/trochoid/
trochoid-spatial/traveling-wave/everything. Picking a different slot
swaps the whole config at once; no per-tab work, no lost edits.

BEHAVIOR

  Switching active slot:
    - The current UI state is auto-saved into the slot you're LEAVING.
    - The new slot's snapshot is loaded into every tab via
      update_display(). If the target slot has never been populated,
      it inherits the current config on first switch.
    - This is the fast iteration loop: set up a config in A, flip to
      B, reshape, flip to C, etc. All four live side-by-side.

  Save current to active slot:
    Explicit snapshot. Use when you want to commit the exact current
    state to the active slot without switching away first.

  Enabled checkboxes:
    Pick which slots get included when you click "Process all enabled".
    The active slot is always included if its box is checked.

  Process all enabled variants:
    Loops over the enabled slots, running the full processor once
    per variant. Each variant's outputs go to their own subfolder:

        <input_dir>/<basename>_variants/A/<basename>.e1.funscript
        <input_dir>/<basename>_variants/A/<basename>.e2.funscript
        <input_dir>/<basename>_variants/A/<basename>.alpha.funscript
        ...
        <input_dir>/<basename>_variants/B/<basename>.e1.funscript
        ...
        <input_dir>/<basename>_variants/C/...

    Restim loads files by matching basename in a folder — point it at
    one subfolder at a time to audition that variant. No filename
    collisions, no renaming.

  Runs sequentially (one variant at a time), same thread model as
  regular processing. Four variants take ~4x a single run's wall time.

WORKFLOW

  1. Configure slot A normally. Process once to confirm it works.
  2. Click B in the Active group. The UI inherits A's config. Tweak
     anything you want to compare (e.g. different trochoid family,
     noise_gate, wave direction, curve choice, etc.).
  3. Repeat for C and D. Tick the Enabled boxes for every slot you
     want to render.
  4. Click "Process all enabled variants".
  5. Point restim at <basename>_variants/A/, test; then /B/, test; etc.
  6. Iterate on the ones you like; re-run.

RESET TO DEFAULTS

  The "Reset to Defaults" button at the bottom of the main window
  is untouched by the variants system. Clicking it resets the CURRENT
  (active) slot's config back to defaults so you can start fresh on
  a new file. Other slots are left intact. Use this when you load a
  new file and want a clean slate while keeping your A/B/C/D work
  for later.

CONFIG STORAGE

  Saved under "variants" in config.json:
    active    "A" | "B" | "C" | "D"
    slots     { "A": {label, enabled, config: {...}},
                "B": {label, enabled, config: {...}},
                ... }

  Each slot's "config" is a FULL snapshot of every other top-level
  config section, minus the "variants" block itself (so it doesn't
  recursively nest). Empty config dict = not yet populated (inherits
  on first switch).

NOTES

  - Variants DO NOT affect the normal single-run "Process All Files"
    or "Process Motion Files" buttons. Those always use the currently
    active slot's settings and write to the normal output location.
  - Saving the config (Save Config / Save Preset) persists the whole
    variants block to disk, so your A/B/C/D survive restarts.
  - The custom_output_directory setting is temporarily overridden
    during a "Process all enabled" run to point at the per-variant
    subfolder; the active slot's persistent setting is not modified.

================================================================================
20. UI CONVENTIONS (TWO-ROW TABS, SCROLL ANYWHERE)
================================================================================

The parameter tabs above the main canvas (General / Speed / Frequency /
Volume / Pulse / Motion Axis 3P / Motion Axis 4P / Advanced / Trochoid /
Trochoid Spatial / Traveling Wave / Signal Gen) are arranged in two rows of up to six
buttons each, so all of them stay visible without a horizontal scroll
or a hidden-overflow chevron. Click any button to switch to that tab —
the currently-selected tab is visually "pressed" (sunken).

The tab bar auto-wraps based on a six-per-row limit. If tabs are added
in the future the bar grows to a third row as needed.

MOUSE-WHEEL SCROLLING

Every parameter tab has its own internal vertical scrollbar for the
content on that page. The mouse wheel scrolls the tab contents
wherever the pointer is — you do NOT need to move the cursor over the
scrollbar itself. The wheel scroll behaves like a web page:

    • Pointer over any control, label, or blank space in the tab
      → wheel scrolls the tab's content.
    • Pointer inside a combobox/dropdown or a control that captures
      the wheel for its own purposes (e.g., a scrollable listbox)
      → the wheel's first natural use wins; the tab does not scroll.
    • Pointer over a different tab's content (when tab is switched)
      → wheel scrolls THAT tab.

Works on macOS trackpad two-finger swipe, Windows/Linux wheel-delta,
and Linux legacy Button-4/Button-5 scroll events alike.

NESTED SCROLLABLES

When multiple scrollable regions are visible at once (e.g. a tab with
a scrollable canvas that contains a Signal Generator's own scrollable
sub-panel), the event routes to whichever scrollable actually contains
the pointer at the moment — the innermost match wins.

HOVER TOOLTIPS

Most numeric entry fields across General / Speed / Frequency / Volume /
Pulse / Motion Axis / Trochoid / Trochoid Spatial / Traveling Wave
show a detailed explanation on hover. Leave the pointer over a field
for a moment and a yellow popup appears with what the setting does,
the practical range, and in many cases a recipe or "when to use it"
hint. The tooltip disappears when the pointer leaves the field. On
macOS the popup is placed to the right of the field to avoid the
bug where mouse-down inside the popup dismisses it; if the right
edge would push it off-screen, it flips to the left automatically.

Tooltips are lazily created on hover and torn down on leave — there
is no idle cost when nothing is hovered.

================================================================================
21. TIPS & SUGGESTIONS
================================================================================

GETTING STARTED:
  1. Load a funscript. Run the Signal Analyzer first to get a baseline.
  2. Apply the analyzer's recommendations as a starting point.
  3. Process the file. Test in restim. Adjust one thing at a time.
  4. Use the Animation Viewer to see the spatial pattern and electrode
     intensities before committing to a full processing run.
  5. Save your curve setups to the library (Edit Curve -> Save to Library)
     so you can reuse them across files.

RECOMMENDED WORKFLOW FOR A NEW FILE:
  1. Load the funscript.
  2. Open Signal Analyzer -> review the classification and charts.
  3. Click "Apply All Recommendations" for a tuned starting point.
  4. Open Animation Viewer -> play through to check the pattern.
  5. Process and test in restim.
  6. Tune by ear: adjust one parameter, reprocess, test, repeat.

SPEED METHOD SELECTION:
  - Start with Rolling Average (it's what you're used to).
  - Try EMA if the output feels "boxy" or has sudden jumps.
  - Try Savitzky-Golay if peaks feel flattened or rounded off.
  - Use "Compare all methods" in the Speed preview to see differences.
  - The Signal Analyzer will recommend a method based on your file's
    stroke variability — trust it as a starting point.

MODULATION:
  - Enable on E1 and E2 first with defaults (0.5 Hz, depth 0.15).
  - The counter-phased defaults (0 vs 180 deg) give immediate texture.
  - Don't go above depth 0.3 until you know what you're doing.
  - Frequency above 2 Hz starts to feel like vibration, not wobble.
  - Try disabling all response curves (set all to flat 0.5) and enabling
    only modulation — this makes the LFO the sole signal, producing a
    pure slow pulsing sensation shaped entirely by the phase offsets.

PHYSICAL MODEL:
  - Measure your actual electrode spacing. The default 20 mm is a guess.
  - Start with "Natural touch" (300 mm/s) and tune by feel.
  - If the sweep feels too fast/twitchy, lower the speed.
  - Try "follow signal" mode on a script with clear up/down strokes.
  - The physical model is independent of the *-2 phase shift — you can
    use both simultaneously.
  - The Signal Analyzer recommends a propagation speed scaled to your
    file's stroke rate.

TROCHOID SPATIAL TAB:
  - Default OFF. When on, OVERRIDES the response-curve E1-E4 generation —
    your per-axis curves in the Motion Axis (4P) tab are bypassed for
    the .e1-.e4 outputs, replaced by the spatial-mapping calculation.
  - Start with the "Rotating spotlight" recipe (rose, k=5, directional,
    sharpness=2). It's the most directly perceptible pattern and easy
    to verify the override is doing what you want.
  - The top-right preview panel (Intensity vs input) is the fastest way
    to tune. Changing sharpness/cycles/family updates it instantly.
    If all four lines look identical, the mapping is too soft — increase
    sharpness. If only one line ever rises, it's too sharp — lower it.
  - Distance mode rewards curves that physically reach toward electrodes
    (rose petals, hypotrochoid lobes). Directional mode rewards curves
    that orbit (most trochoids). Amplitude mode is a hybrid that adds
    natural emphasis at the curve's outer extremes.
  - Cycles per stroke = 1 means one curve trace per stroke. For a busy
    "buzzing rotation" feel, push to 5-10. For a slow drift across
    electrodes, try 0.25-0.5.
  - Open the Animation Viewer with "Spatial" checked to see the
    trajectory dot follow the curve and the bars fire in sequence —
    excellent for previewing the spatial choreography before processing.
  - Trochoid Spatial does NOT touch alpha/beta or other channels. Only
    the four .e1-.e4 files come from the spatial mapping.

CURVE QUANTIZATION (TROCHOID TAB):
  - Default OFF. Only enable when you actually want quantized output —
    every downstream file (alpha/beta, E1-E4, frequency, volume, pulse)
    inherits the snap.
  - Start with N = 23, family = hypo, projection = radius. That's the
    "tutorial preset" — a clearly visible quantization that doesn't
    destroy the source character.
  - Big differences come from family + projection. Try the same N=23
    on hypo/radius vs rose (k=5)/radius vs butterfly/radius — the level
    distributions are wildly different.
  - Use the Step render mode to verify the snap is doing what you expect,
    then switch back to Interpolated to see the actual playback shape.
  - Turn on Deduplicate Holds on long files — it's harmless (the device
    behaves identically) and keeps file sizes small.
  - The custom expression mode is sandboxed but powerful. Reach for it
    when you want a specific N-tooth saw, pseudo-random levels via
    sin(prime*t) combinations, or non-symmetric distributions.
  - The Animation Viewer reflects the quantization too — open it after
    enabling to see the dimmer strip turn into discrete bands.

RESPONSE CURVES:
  - Linear is boring but predictable. Start there for each axis.
  - Ease-In makes the axis respond more at high positions.
  - Sharp Peak makes the axis spike in the middle of the stroke.
  - The curve editor lets you draw arbitrary shapes with control points.
  - Use Bulk Entry to paste exact coordinates from a spreadsheet.
  - Save curves you like to the library — they persist across sessions.
  - Built-in presets can't be overwritten. If you modify a built-in
    curve and save, it auto-renames to "Custom (<name>)".
  - Use the Waveform Preview to see how curves transform the signal.
  - Use the Animation Viewer's dimmer strip to see the combined effect
    of all four curves over time.

ANIMATION VIEWER TIPS:
  - For fastest playback, disable panels you don't need (uncheck in Show).
  - Dimmer-only mode runs at ~100 FPS.
  - Use Follow mode with a 5-10 second window for a "scrolling scope" view.
  - The waterfall view is best for comparing individual electrode shapes.
  - The heatmap is best for seeing the overall spatial pattern at a glance.
  - Zoom to 800-3200% to inspect individual strokes in the dimmer strip.

SIGNAL ANALYZER TIPS:
  - Always run the analyzer before manually tuning settings — it gives
    you a rational starting point based on the actual signal.
  - The analyzer's recommendations are conservative. Feel free to push
    values further once you understand what each setting does.
  - "Apply Selected" lets you cherry-pick recommendations — click the
    rows you want, then apply only those.
  - After applying, reprocess and test. The analyzer doesn't know your
    subjective preferences — it optimizes for the signal's statistics.
  - Toggle "Apply trochoid quantization to source" to see how
    quantization changes the statistics — useful for understanding
    whether your chosen N is preserving the signal's character or
    flattening too much.

SHAFT VIEWER:
  - Fastest way to see what trochoid-spatial is doing to your file:
    open the Shaft Viewer with 'auto' intensity mode after enabling
    Trochoid Spatial in its tab — the intensity bars on the shaft
    will pulse with the spatial pattern.
  - Put a matching video next to the funscript (same base name,
    .mp4 / .mov / etc.) and the viewer loads it automatically. No
    need to drag-drop every time.
  - Video out of sync on first load? Scrub to a distinctive stroke
    peak, nudge Offset until visibly aligned, then click Sync here —
    the offset becomes permanent for this session.
  - Use the intensity mode dropdown to A/B compare 'spatial' vs
    'curves' vs 'wave' in real-time without touching the main tabs.
    The electrode bars make the difference obvious.
  - Uncheck "Show video" to hide the video panel when you only care
    about the shaft — the shaft canvas grows to fill the freed space
    and the video decoder is skipped, saving a bit of CPU. Video
    state is preserved; toggling back on resumes exactly where it was.
  - Proximity mode is the geometric control — use it to sanity-check
    "what would a simple proximity model do for these electrode
    positions?" before turning on the full processing stack.
  - The horizontal 'Proximity reach' slider sweeps between sharp
    (each electrode fires only in its narrow zone) and broad (all
    electrodes fire simultaneously). Only relevant in proximity mode
    and the fallback path.

TRAVELING WAVE TAB:
  - Default OFF. When on, TAKES PRIORITY over Trochoid Spatial and
    the Motion Axis response curves for E1-E4. Disable it if you
    want the other paths to run.
  - Not sure if it's actually doing anything? Set envelope=constant,
    speed=3 Hz, width=0.08, sharpness=2, noise_gate=0.2 — each
    electrode now fires as a distinct pulse three times per second,
    impossible to miss. Then tune back toward something musical.
  - signal_position is the tightest funscript sync — the crest's
    axial position = y(t) exactly. Wave_speed_hz and speed_mod are
    ignored. Great baseline for "I want electrodes to follow the
    signal, no extra motion".
  - Combine signal_position + exclusive + narrow width (0.10) to
    get a clean 1-of-4 spotlight that hops as the signal crosses
    electrode positions.
  - Noise gate 0.10 (default) is a gentle fuzz-killer. Push to 0.25
    for crisp edges; 0.40+ for "only direct hits fire" feel.
  - The per-axis modulation block from Motion Axis (4P) applies here
    too — enable 8 Hz on E2, 16 Hz on E4, etc. Good way to layer
    per-electrode texture on top of the wave without adding a new
    processor.
  - Saved .e1-.e4 outputs are resampled to 60 Hz internally so the
    wave's motion is actually captured. Without this, a sparse
    funscript can alias the wave away completely. If you're scripting
    against the API and want raw input-grid output, pass
    densify_hz=0 to generate_wave_funscripts.

TROCHOID VIEWER:
  - Launched from the "Trochoid Viewer" button in the main window's
    bottom button row. Pairs the 2D trochoid curve with its shadow
    on the shaft.
  - Shaft mode "shadow" shows continuous projection; "lobes" shows
    the discrete lobe bar-chart with active-lobe highlight. Toggle
    the mode combobox to see both interpretations on the same data.
  - Projection matters a lot for lobes mode. Rose k=5 on projection=
    'radius' detects 9-10 lobes (mathematically correct for |r|);
    on projection='y' detects the visual 5 petals. Pick the one that
    matches what you want to drive electrodes with.
  - Curve parameters (R, r, d, a, k, ...) read from config at open
    time. To reshape the curve, edit the Trochoid Spatial tab and
    reopen the viewer.
  - The viewer's electrode intensity is a SIMPLIFIED proximity model
    for display only — NOT what the processor writes to .e1-.e4
    files. For the true processor output, enable Trochoid Spatial
    (section 14) or Traveling Wave (section 15) and process.

COMPARISON VIEWER (COMPARE FUNSCRIPTS):
  - The fastest sanity check after processing: open the viewer (button
    is in the bottom row) — slot A is pre-loaded with your input file.
    Browse to load the .e1 (or .alpha) output as B. Drag the scrubber
    through the file to spot mismatches.
  - Enable "Difference (B-A)" to get RMS and peak drift numbers —
    great for quantifying "how much did processing change this signal".
  - Enable "Overlay" to spot timing alignment issues — the two signals
    rendered on the same axes make small offsets immediately visible.
  - Use the standalone form (python funscript_compare.py file_a file_b)
    when you don't need the rest of the app — it's the same viewer
    without the main window's overhead.
  - Scroll-wheel zoom is anchored on the cursor — point at the moment
    you want to inspect, then scroll up. Much faster than the Fit
    button + manual scrubber.

PERFORMANCE:
  - EMA is O(n) vs Rolling Average's O(n^2). On long scripts (>60s),
    EMA is noticeably faster.
  - Savitzky-Golay is O(n) per pass but does two passes (derivative +
    smoothing), so it's comparable to EMA in practice.
  - Interpolation Interval of 0.02 (50 pts/sec) is the sweet spot.
    Going to 0.01 doubles processing time for marginal benefit.
  - In the Animation Viewer, disabling the Trajectory panel saves the
    most rendering time (especially in 3D mode).

KEYBOARD SHORTCUTS:
  Animation Viewer:
    Enter (in time field):  Jump to typed time.
    Scrubber drag:          Jump to any point.
  Curve Editor:
    Enter (in X/Y fields):  Add or update point (smart — updates if
                            a point is selected, adds if not).
    Escape:                 Cancel and close.
    Enter (in dialog):      Save and close.
"""


def _parse_help_text(text):
    """Parse HELP_TEXT into a list of sections.

    Each section is a dict:
        title: str, content: str, subsections: list of {title, content}

    Sections are delimited by ===== lines with a numbered title.
    Subsections are ALL-CAPS lines ending with a colon (or not) that
    appear within a section.
    """
    import re
    lines = text.strip().split('\n')
    sections = []
    current_section = None
    current_sub = None
    buf = []

    def flush_buf():
        nonlocal current_sub
        text_block = '\n'.join(buf).strip()
        if current_sub is not None and current_section is not None:
            current_section['subsections'].append({
                'title': current_sub, 'content': text_block})
            current_sub = None
        elif current_section is not None and text_block:
            # Content before any subsection — becomes the section intro
            if current_section['subsections']:
                current_section['subsections'].append({
                    'title': '(continued)', 'content': text_block})
            else:
                current_section['intro'] = text_block
        buf.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Section header: a line of === followed by a numbered title
        if stripped.startswith('======') and i + 1 < len(lines):
            # Look for the title on the next line
            next_line = lines[i + 1].strip()
            match = re.match(r'^(\d+)\.\s+(.+)$', next_line)
            if match:
                # Flush previous
                flush_buf()
                if current_section is not None:
                    sections.append(current_section)
                current_section = {
                    'title': f"{match.group(1)}. {match.group(2)}",
                    'intro': '',
                    'subsections': [],
                }
                current_sub = None
                # Skip the === line, the title line, and the closing === line
                i += 2
                if i < len(lines) and lines[i].strip().startswith('======'):
                    i += 1
                continue
        # Skip standalone === lines (e.g., the top header block)
        elif stripped.startswith('======'):
            i += 1
            continue
        # Skip the top title
        elif 'RESTIM FUNSCRIPT PROCESSOR' in stripped:
            i += 1
            continue
        # Skip TOC (lines starting with digits followed by a period in the first section area)
        elif current_section is None and re.match(r'^\s+\d+\.', line):
            i += 1
            continue
        elif current_section is None and stripped in ('TABLE OF CONTENTS', ''):
            i += 1
            continue

        # Subsection header: ALL-CAPS line with >3 chars, first char alpha
        # Exclude lines that are just list items or separators
        if (stripped and len(stripped) > 3
                and stripped.rstrip(':') == stripped.rstrip(':').upper()
                and stripped[0].isalpha()
                and not stripped.startswith('-')
                and current_section is not None):
            flush_buf()
            current_sub = stripped.rstrip(':')
            i += 1
            continue

        buf.append(line)
        i += 1

    # Flush last
    flush_buf()
    if current_section is not None:
        sections.append(current_section)

    return sections


class HelpViewer(tk.Toplevel):
    """Help window with expandable tree navigation + content pane."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Help — Restim Funscript Processor")
        self.geometry("950x650")
        self.minsize(650, 400)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Parse sections
        self._sections = _parse_help_text(HELP_TEXT)

        # Split pane: tree left, content right
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # ── Left: tree ───────────────────────────────────────────────
        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=0)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(tree_frame, show='tree', selectmode='browse')
        self._tree.grid(row=0, column=0, sticky='nsew')
        tree_sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                command=self._tree.yview)
        tree_sb.grid(row=0, column=1, sticky='ns')
        self._tree.config(yscrollcommand=tree_sb.set)

        # Populate tree
        self._node_content = {}  # node_id -> text content
        for sec in self._sections:
            sec_id = self._tree.insert('', 'end', text=sec['title'], open=False)
            # The section intro is shown when clicking the section node
            self._node_content[sec_id] = sec.get('intro', '')
            for sub in sec['subsections']:
                sub_id = self._tree.insert(sec_id, 'end', text=sub['title'])
                self._node_content[sub_id] = sub['content']

        self._tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # Expand All / Collapse All buttons
        tree_btn_frame = ttk.Frame(tree_frame)
        tree_btn_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(3, 0))
        ttk.Button(tree_btn_frame, text="Expand All", width=10,
                   command=self._expand_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(tree_btn_frame, text="Collapse All", width=10,
                   command=self._collapse_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(tree_btn_frame, text="Show All", width=10,
                   command=self._show_all_text).pack(side=tk.LEFT, padx=2)

        # ── Right: content ───────────────────────────────────────────
        content_frame = ttk.Frame(paned)
        paned.add(content_frame, weight=1)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        content_sb = ttk.Scrollbar(content_frame)
        content_sb.grid(row=0, column=1, sticky='ns')

        self._text = tk.Text(content_frame, wrap=tk.WORD, font=('Menlo', 11),
                             padx=15, pady=10, spacing1=1, spacing3=1,
                             yscrollcommand=content_sb.set, state=tk.DISABLED)
        self._text.grid(row=0, column=0, sticky='nsew')
        content_sb.config(command=self._text.yview)

        # Text tags
        self._text.tag_configure('header', font=('Menlo', 12, 'bold'),
                                 foreground='#1565C0', spacing1=8, spacing3=4)
        self._text.tag_configure('subheader', font=('Menlo', 11, 'bold'),
                                 foreground='#333', spacing1=6, spacing3=2)
        self._text.tag_configure('highlight', background='#FFEB3B')

        # ── Bottom: search bar ───────────────────────────────────────
        search_frame = ttk.Frame(self, padding="5")
        search_frame.grid(row=1, column=0, sticky='ew')
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(5, 5))
        search_entry.bind('<Return>', self._do_search)
        ttk.Button(search_frame, text="Find", command=self._do_search).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=(5, 0))
        self._search_count_label = ttk.Label(search_frame, text="", foreground='#666')
        self._search_count_label.pack(side=tk.LEFT, padx=(10, 0))

        # Show welcome / overview on open
        if self._sections:
            first = self._tree.get_children()[0]
            self._tree.selection_set(first)
            self._tree.see(first)
            self._show_section_content(first)

    def _on_tree_select(self, event=None):
        """Show content for the selected tree node."""
        selection = self._tree.selection()
        if not selection:
            return
        node_id = selection[0]
        parent = self._tree.parent(node_id)

        if parent == '':
            # Top-level section — show intro + all subsections
            self._show_section_content(node_id)
        else:
            # Subsection — show just that subsection
            self._show_node_content(node_id)

    def _show_section_content(self, section_id):
        """Show the full section: intro + all subsections."""
        self._text.config(state=tk.NORMAL)
        self._text.delete('1.0', tk.END)

        title = self._tree.item(section_id, 'text')
        self._text.insert(tk.END, title + '\n\n', 'header')

        intro = self._node_content.get(section_id, '')
        if intro:
            self._text.insert(tk.END, intro + '\n\n')

        for child_id in self._tree.get_children(section_id):
            sub_title = self._tree.item(child_id, 'text')
            sub_content = self._node_content.get(child_id, '')
            if sub_title != '(continued)':
                self._text.insert(tk.END, sub_title + '\n', 'subheader')
            if sub_content:
                self._text.insert(tk.END, sub_content + '\n\n')

        self._text.config(state=tk.DISABLED)

    def _show_node_content(self, node_id):
        """Show a single subsection."""
        self._text.config(state=tk.NORMAL)
        self._text.delete('1.0', tk.END)

        # Show parent section title for context
        parent = self._tree.parent(node_id)
        if parent:
            parent_title = self._tree.item(parent, 'text')
            self._text.insert(tk.END, parent_title + '\n', 'header')

        title = self._tree.item(node_id, 'text')
        if title != '(continued)':
            self._text.insert(tk.END, '\n' + title + '\n', 'subheader')

        content = self._node_content.get(node_id, '')
        if content:
            self._text.insert(tk.END, content + '\n')

        self._text.config(state=tk.DISABLED)

    def _show_all_text(self):
        """Show the entire help text in the content pane."""
        self._text.config(state=tk.NORMAL)
        self._text.delete('1.0', tk.END)

        for sec in self._sections:
            self._text.insert(tk.END, sec['title'] + '\n\n', 'header')
            intro = sec.get('intro', '')
            if intro:
                self._text.insert(tk.END, intro + '\n\n')
            for sub in sec['subsections']:
                if sub['title'] != '(continued)':
                    self._text.insert(tk.END, sub['title'] + '\n', 'subheader')
                if sub['content']:
                    self._text.insert(tk.END, sub['content'] + '\n\n')

        self._text.config(state=tk.DISABLED)

    def _expand_all(self):
        for item in self._tree.get_children():
            self._tree.item(item, open=True)

    def _collapse_all(self):
        for item in self._tree.get_children():
            self._tree.item(item, open=False)

    def _do_search(self, event=None):
        """Search across all content, highlight matches, and jump to first."""
        query = self._search_var.get().strip()
        if not query:
            self._search_count_label.config(text="")
            return

        # Show all text so we can search it
        self._show_all_text()
        self._text.tag_remove('highlight', '1.0', tk.END)

        count = 0
        start = '1.0'
        first_pos = None
        while True:
            pos = self._text.search(query, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self._text.tag_add('highlight', pos, end)
            if first_pos is None:
                first_pos = pos
            start = end
            count += 1

        if count > 0 and first_pos:
            self._text.see(first_pos)
            self._search_count_label.config(
                text=f"{count} match{'es' if count != 1 else ''}")
        else:
            self._search_count_label.config(text="No matches")

    def _clear_search(self):
        self._text.tag_remove('highlight', '1.0', tk.END)
        self._search_var.set("")
        self._search_count_label.config(text="")
