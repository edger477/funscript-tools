# Restim Funscript Processor - Complete Guide

## How It Works

### What This Program Does

The Restim Funscript Processor takes a standard `.funscript` file (a time-stamped sequence of positions 0-100) and generates multiple output files that control different aspects of electrostimulation: frequency, volume, pulse characteristics, and multi-axis motion patterns.

### The Big Picture

A single input funscript describes movement over time. This program analyzes that movement and produces specialized output signals:

```
Input: 123.funscript (position over time)
    |
    v
Processing Engine
    |
    +---> 123.speed.funscript        (how fast things move)
    +---> 123.frequency.funscript    (carrier frequency)
    +---> 123.volume.funscript       (stimulation intensity)
    +---> 123.pulse-freq.funscript   (pulse repetition rate)
    +---> 123.pulse-width.funscript  (pulse duration)
    +---> 123.pulse-rise.funscript   (pulse attack shape)
    +---> 123.alpha.funscript        (2D motion axis 1)
    +---> 123.beta.funscript         (2D motion axis 2)
    +---> 123.e1.funscript           (4-channel motion axis 1)
    +---> 123.e2.funscript           (4-channel motion axis 2)
    +---> 123.e3.funscript           (4-channel motion axis 3)
    +---> 123.e4.funscript           (4-channel motion axis 4)
    +---> (phase-shifted -2 variants of the above)
```

### Processing Pipeline Step by Step

#### Step 1: Analyze Motion
The input funscript's position values are analyzed to extract two fundamental signals:

- **Speed** — how fast the position is changing at each moment (calculated with a rolling window)
- **Acceleration** — how fast the speed itself is changing (a second rolling window on top of speed)

These derived signals drive everything downstream.

#### Step 2: Generate Volume Ramp
A slow linear ramp is generated based on the script's total duration. This creates a gradual intensity build over time (like a volume knob slowly turning up).

#### Step 3: Combine Signals
The speed, acceleration, and ramp signals are blended together using weighted ratios to produce each output:

- **Frequency** = Ramp + Speed (weighted)
- **Volume** = Ramp + Speed (weighted, with rest level)
- **Pulse Frequency** = Speed + Alpha (weighted)
- **Pulse Width** = Speed + Alpha-Limited (weighted)
- **Pulse Rise** = Beta-Mirrored + Speed-Inverted (weighted)

Each combine ratio controls the mix between two source signals. A ratio of 3.0 means ~67%/33% split.

#### Step 4: Generate Motion Axes

**3P (Legacy Alpha/Beta):**
The 1D funscript is converted into 2D circular motion using one of four algorithms. This produces alpha (X-axis) and beta (Y-axis) files that trace a path around a circle or arc, with the radius proportional to speed.

**4P (E1-E4 Motion Axes):**
Each of four axes receives the input signal (optionally rotated by an angle) and passes it through a configurable response curve. The curve transforms input positions into output positions — for example, an "Ease In" curve suppresses low-level movement but amplifies high-level movement.

#### Step 5: Phase Shifting
Optionally, phase-shifted copies of the motion axes are created by delaying all timestamps by a fixed millisecond offset. This creates a "trailing" version that follows the original with a slight lag.

#### Step 6: Output
All generated files are saved alongside the input file (local mode) or to a central folder. Optional normalization, backup, and ZIP packaging are applied.

### Understanding the Signal Chain

```
Position (raw)
    |
    +--> Speed Window --> Speed (how fast)
    |        |
    |        +--> Accel Window --> Acceleration (speed of speed)
    |
    +--> Volume Ramp --> Ramp (slow crescendo over time)
    |
    +--> [Signal Rotation by angle] --> Rotated Position
              |
              +--> [Response Curve] --> Axis Output (e1-e4)
```

Each step transforms the signal. The windows smooth it, the ramp adds time-based dynamics, the rotation changes polarity, and the curves reshape the response.

---

## Settings Reference

### General Tab

#### Rest Level
- **Default:** 0.4 | **Range:** 0.0 - 1.0
- The minimum signal output when there's no motion (volume or speed is zero).
- **0.0** = complete silence during rest, **1.0** = full output even when idle.
- *Example:* Set to 0.2 for a subtle baseline hum during pauses, or 0.0 for total silence.

#### Ramp Up Duration After Rest
- **Default:** 5.0 seconds | **Range:** 0.0 - 10.0
- How quickly the signal transitions from rest level back to normal when motion resumes.
- **0.0** = instant jump, **5.0** = gradual 5-second fade-in.
- *Example:* Set to 0.0 for immediate response, or 3.0 for a smooth ramp after pauses.

#### Speed Window (sec)
- **Default:** 2 | **Range:** 1 - 30
- Rolling window in seconds used to calculate how fast the position is changing.
- Small values = reactive to quick bursts (spiky output). Large values = smooth, averaged speed.
- Chain: Position -> **Speed Window** -> Speed signal -> everything downstream.
- *Example:* Set to 1 for fast-paced content with distinct strokes. Set to 10+ for slow ambient scripts where you want smooth, flowing speed curves.

#### Accel Window (sec)
- **Default:** 3 | **Range:** 1 - 10
- Rolling window for calculating how fast the *speed* is changing (acceleration).
- Chain: Speed -> **Accel Window** -> Acceleration signal.
- Compounds with Speed Window: both large = very smooth and delayed. Both small = highly reactive.
- *Example:* Set to 1-2 for sharp detection of sudden starts/stops. Set to 5+ for gradual, averaged acceleration tracking.

#### Processing Options

**Normalize Volume** (Default: On)
- Scales the volume output so the peak reaches 100%. Turn off to preserve raw calculated values.
- *Example:* Turn off when processing multiple files that should maintain relative volume differences.

**Delete Intermediary Files When Done** (Default: On)
- Removes temporary working files after processing completes. Turn off to inspect intermediate results like raw speed calculations.

**Overwrite Existing Output Files** (Default: Off)
- When off, existing output files are preserved and processing skips them. Turn on to always regenerate.
- *Example:* Turn on when tweaking settings iteratively on the same file.

#### File Management

**Output Mode**
- **Local:** Output files saved in the same folder as the source funscript.
- **Central:** All outputs saved to a single designated folder.
- *Example:* Use Central mode when building a library of processed files for a specific device.

**Central Folder** — Path to the central output directory (only used in Central mode).

**Create Backups** (Default: On) — Creates timestamped ZIP backups before overwriting files in central mode.

**Zip Output Files** (Default: Off) — Packages all output files into a single ZIP instead of individual files.

---

### Speed Tab

#### Interpolation Interval
- **Default:** 0.02 seconds | **Range:** 0.01 - 1.0
- Time between interpolated data points. Smaller = higher resolution, larger = fewer points.
- Also determines Points Per Second for 1D-to-2D conversion (PPS = 1 / interval).
- *Example:* 0.02 = 50 points/sec (high detail, larger files). 0.1 = 10 points/sec (lighter processing, smaller files).

#### Normalization Method
- **Default:** "max"
- **max:** Scales so the fastest speed = 1.0. Consistent output levels regardless of content intensity.
- **rms:** Scales based on average energy. Preserves relative dynamics — a mostly-slow script with one fast burst won't have the burst dominate.
- *Example:* Use "max" for general use. Switch to "rms" for scripts with widely varying intensity that you want to feel more even.

---

### Frequency Tab

#### Pulse Frequency Min / Max
- **Default:** Min: 0.5, Max: 0.99 | **Range:** 0.0 - 1.0
- Floor and ceiling for the pulse frequency output. The output is clamped to this range.
- *Example:* Set Min to 0.3 and Max to 0.8 for a wider band with more variation. Narrow to 0.6-0.9 for consistently high-frequency output.

#### Frequency Combine Ratio (Ramp | Speed)
- **Default:** 3.7 | **Range:** 1 - 10
- Blends the ramp signal with the speed signal to produce the carrier frequency.
- At 3.7: ~73% ramp, ~27% speed. Frequency mostly follows the ramp envelope with speed adding dynamics.
- *Example:* Set to 1.0 for pure speed-driven frequency (fast motion = high frequency). Set to 10.0 for frequency that follows the ramp almost exclusively.

#### Pulse Frequency Combine Ratio (Speed | Alpha)
- **Default:** 3.0 | **Range:** 1 - 10
- Blends speed with the alpha signal for pulse repetition rate.
- At 3.0: ~67% speed, ~33% alpha. Faster motion = faster pulses, with alpha adding rhythmic texture.
- *Example:* Set to 1.0 for pure alpha-driven pulse rate (tied to the funscript pattern). Set higher for pulses that mostly respond to motion speed.

---

### Volume Tab

#### Volume Combine Ratio (Ramp | Speed)
- **Default:** 25.2 | **Range:** 10.0 - 40.0
- Blends the ramp envelope with speed for the volume output. Very ramp-dominant by default.
- At 25.2: ~96% ramp, ~4% speed. Volume mostly follows the slow crescendo with subtle speed variation.
- *Example:* Set to 10 for more speed-reactive volume (movement directly affects intensity). Set to 40 for volume that only follows the ramp.

#### Prostate Volume Multiplier
- **Default:** 1.5 | **Range:** 1.0 - 3.0
- Scales the combine ratio specifically for the prostate channel.
- Effective prostate ratio = Volume Combine Ratio x Multiplier.
- *Example:* At 1.5, prostate ratio becomes 25.2 x 1.5 = 37.8 (even smoother than standard volume). Increase to 2.0+ for very steady prostate stimulation.

#### Prostate Volume Rest Level
- **Default:** 0.7 | **Range:** 0.0 - 1.0
- Minimum prostate volume during rest periods. Higher than the general rest level to maintain baseline sensation.
- *Example:* Set to 0.5 for moderate baseline during pauses. Set to 0.9 for nearly constant prostate stimulation.

#### Ramp (% per hour)
- **Default:** 10 | **Range:** 0 - 40
- Volume crescendo rate over the script's total duration.
- At 10%/hr on a 1-hour script: starts at 90%, ramps to 100%.
- At 10%/hr on a 4-hour script: starts at 60%, ramps to 100%.
- *Example:* Set to 0 for flat volume throughout. Set to 30 for a dramatic build from quiet to loud over the session.

---

### Pulse Tab

#### Pulse Width Min / Max
- **Default:** Min: 0.1, Max: 0.55 | **Range:** 0.0 - 1.0
- Output range limits for pulse width. Values are clamped to this range.
- *Example:* Narrow to 0.3-0.6 for subtle variation. Widen to 0.0-1.0 for maximum contrast between narrow and wide pulses.

#### Pulse Width Combine Ratio (Speed | Alpha-Limited)
- **Default:** 3.0 | **Range:** 1 - 10
- Blends speed with alpha-limited signal for pulse width.
- *Example:* Set to 1.0 for width driven purely by the alpha pattern. Set higher for speed-dominant width control.

#### Beta Mirror Threshold
- **Default:** 0.5 | **Range:** 0.0 - 0.5
- Threshold for mirroring the beta signal in pulse calculations.
- *Example:* Set to 0.0 to disable mirroring entirely. Set to 0.5 for maximum mirror effect.

#### Pulse Rise Time Min / Max
- **Default:** Min: 0.0, Max: 0.8 | **Range:** 0.0 - 1.0
- Output range limits for how quickly each pulse ramps up.
- *Example:* Set Max to 1.0 for full variation from sharp to gradual attacks. Set to 0.3-0.5 for consistently moderate rise times.

#### Pulse Rise Combine Ratio (Beta-Mirrored | Speed-Inverted)
- **Default:** 2.0 | **Range:** 1 - 10
- Blends beta-mirrored with speed-inverted signal for pulse rise time.
- *Example:* Set to 1.0 for rise controlled purely by inverted speed (fast motion = slow rise). Set higher for beta-dominant control.

---

### Motion Axis (3P) Tab — Legacy Alpha/Beta

The 3P system converts the 1D funscript into 2D spatial motion for dual-electrode stimulation.

#### Generate Motion Scripts (Default: On)
Enable/disable generation of legacy alpha and beta funscript files.

#### Generate Phase-Shifted Versions (Default: Off)
Creates *-2.funscript files (alpha-2, beta-2) with a fixed time delay applied to all timestamps.

#### Phase Shift Delay
- **Default:** 100 ms
- Fixed time delay in milliseconds applied to the phase-shifted versions.
- *Example:* Set to 50ms for subtle trailing effect. Set to 200ms for a noticeable echo between channels.

#### 1D to 2D Conversion

**Algorithm** — How the 1D position is converted into 2D circular motion:
- **top-left-right:** Circular pattern: Top -> Left -> Bottom -> Right. Good for general use.
- **top-right-left:** Circular pattern: Top -> Right -> Bottom -> Left. Opposite rotation.
- **circular:** 0deg-180deg arc motion. Simpler, less spatial variation.
- **restim-original:** Full 0-360deg rotation with random direction changes. Most dynamic.
- *Example:* Start with "top-right-left" for predictable motion. Try "restim-original" with Direction Change Probability at 0.3 for more varied patterns.

**Points Per Second** — Auto-calculated from the Speed tab's Interpolation Interval (PPS = 1/interval). Read-only. Higher values = smoother 2D paths.

**Min Distance From Center**
- **Default:** 0.2 | **Range:** 0.1 - 0.9
- Minimum radius from center in the 2D conversion. Even at zero speed, the position stays at least this far from center.
- *Example:* Set to 0.1 for tight center-focused motion. Set to 0.5 for wide circular patterns even during slow movement.

**Speed Threshold (%)**
- **Default:** 57 | **Range:** 0 - 100
- Speed percentile that maps to maximum radius. Lower values mean more of the motion reaches full radius.
- *Example:* Set to 30 so most movement reaches max radius. Set to 80 so only the fastest bursts hit full radius.

**Direction Change Probability**
- **Default:** 0.2 | **Range:** 0.0 - 1.0
- Probability of reversing circular direction per segment. Only used with restim-original algorithm.
- *Example:* Set to 0.0 for consistent one-direction rotation. Set to 0.5 for frequent random reversals.

#### Prostate Generation

**Generate Prostate Files** (Default: On) — Creates prostate-specific alpha/beta variants.

**Generate From Inverted** (Default: On) — Uses the inverted input funscript as the source for prostate generation.

**Algorithm:**
- **standard:** 0deg-180deg standard circular pattern.
- **tear-shaped:** Tear-shaped 0deg-180deg pattern with a constant zone. Better for prostate-specific stimulation patterns.

**Min Distance From Center (Prostate)**
- **Default:** 0.5 | **Range:** 0.3 - 0.9
- Controls the constant zone size in the tear-shaped algorithm.

---

### Motion Axis (4P) Tab — E1-E4 Generation

The 4P system provides four independent output channels, each processing the input signal through a configurable response curve. Unlike the spatial 3P system, these are independent intensity channels.

#### Generate Motion Scripts (Default: On)
Enable/disable generation of E1-E4 funscript files.

#### Generate Phase-Shifted Versions (Default: Off)
Creates *-2.funscript files for each enabled axis with a fixed time delay.

#### Phase Shift Delay
- **Default:** 100 ms
- Fixed time delay in milliseconds for 4P phase-shifted versions.
- *Example:* Set to 100ms for a subtle trailing channel. Set to 500ms for distinct echo effects.

#### Config Preset
- **New:** Create a new named preset from current E1-E4 settings.
- **Delete/Rename:** Manage existing presets.
- **Export/Import:** Share presets as JSON files.
- Each preset stores: axis enabled states, response curves, signal angles, and phase shift settings.

#### E1-E4 Axis Configuration

Each axis has:
- **Enabled:** Toggle the axis on/off.
- **Curve:** Response curve (transfer function) that maps input position (0-100) to output position (0-100).
- **Edit Curve:** Opens a visual editor with draggable control points.

**What Response Curves Do:**
The curve is a transfer function — it remaps the input signal's position values. At every moment in time, the input position is looked up on the curve's X axis, and the corresponding Y value becomes the output.

**Built-in Curves:**
| Curve | Behavior | Use Case |
|-------|----------|----------|
| **Linear** | Output = Input (1:1) | Baseline reference |
| **Ease In** | Suppresses low values, amplifies high | Responds mainly to strong movement |
| **Ease Out** | Amplifies low values, suppresses high | Sensitive to subtle movement |
| **Sharp Peak** | Spikes at mid-range, zero at extremes | Triggers only at specific intensity |
| **Inverted** | High input -> low output, vice versa | Opposite response to another axis |
| **Gentle Wave** | Oscillates across the range | Rhythmic, undulating patterns |
| **S-Curve** | Compressed at extremes, expanded in middle | Enhanced mid-range contrast |
| **Bell Curve** | Peak at center, tapers to edges | Emphasis on medium-intensity input |

*Example:* Set E1 to Linear (faithful reproduction), E2 to Ease In (only activates on strong movement), E3 to Inverted (active when E1 is quiet), E4 to Sharp Peak (brief intense bursts at mid-range). Each channel produces a completely different stimulation pattern from the same input.

#### Angle Manipulation (Signal Rotation)

The angle rotates the **input signal** before it passes through each axis's response curve. The curves themselves are not modified — instead, each axis receives a differently-transformed version of the input.

**Formula:** `rotated_position = 50 + (position - 50) x cos(angle)`

| Angle | Effect on Input Signal | Description |
|-------|----------------------|-------------|
| **0deg** | Unchanged | Original signal |
| **30deg** | Slightly compressed toward 50 | ~87% of original contrast |
| **45deg** | Moderately compressed | ~71% of original contrast |
| **60deg** | Significantly compressed | ~50% of original contrast |
| **90deg** | Completely flat at 50 | No variation (everything = 50) |
| **120deg** | Compressed + inverted | ~50% contrast, polarity flipped |
| **135deg** | Moderately inverted | ~71% contrast, polarity flipped |
| **180deg** | Fully inverted | 0 becomes 100, 100 becomes 0 |

*Example — Complementary channels:*
- E1 at 0deg: Original signal through Ease In curve
- E2 at 60deg: Compressed signal through Sharp Peak curve (more centered response)
- E3 at 180deg: Inverted signal through Linear curve (active when E1 is quiet)
- E4 at 90deg: Flat input through any curve = constant output (baseline channel)

*Example — Subtle variation:*
- All axes at 0deg, 15deg, 30deg, 45deg with different curves: creates four channels with slightly different dynamic ranges, each emphasizing different parts of the movement.

#### Waveform Preview

- **Input Row:** Shows the actual loaded funscript (or synthetic sine wave if no file is loaded).
- **E1-E4 Rows:** Shows each axis's output after signal rotation + curve application.
- **Overlay Row:** All enabled axes overlaid on one chart with transparent fills for comparison.
- **Zoom:** 100% to 8000%, with preset dropdown or arbitrary keyboard entry.
- **Scroll:** Horizontal slider for panning through the waveform when zoomed in.
- **Refresh Preview:** Reloads the input file and recomputes all outputs with current settings.

---

### Advanced Tab

#### Enable Pulse Frequency Inversion (Default: Off)
Generates an additional inverted version of the pulse frequency output file.

#### Enable Volume Inversion (Default: Off)
Generates an additional inverted version of the volume output file.

#### Enable Frequency Inversion (Default: Off)
Generates an additional inverted version of the frequency output file.

*Example:* Enable volume inversion to get both a normal volume envelope and its complement — useful for dual-channel setups where one channel follows the script and the other does the opposite.

---

### Bottom Toolbar

#### Process All Files
Runs the complete processing pipeline on all selected input files (speed, frequency, volume, pulse, 3P, and 4P outputs).

#### Process Motion Files
Runs only the motion axis generation (3P alpha/beta and 4P E1-E4) without regenerating speed/frequency/volume/pulse files. Faster when you only need to update motion settings.

#### Custom Event Builder
Opens a visual timeline editor for creating custom event markers.

#### Save Config
Saves the current settings to `config.json` in the application directory. These become the defaults for next launch.

#### Save Preset
Exports the complete current configuration to a named `.json` file anywhere on disk. Use this to save settings that produce good results for a specific type of content.
- *Example:* Save "gentle_session.json" with low ramp, high rest level, compressed angles. Save "intense_session.json" with zero rest, fast windows, full-range angles.

#### Load Preset
Imports a previously saved preset file. All UI controls update to reflect the loaded settings. Invalid files are rejected.
- *Example:* Load a preset before processing a batch of similar files to ensure consistent output.

#### Reset to Defaults
Resets all settings to factory defaults after confirmation.

#### Dark Mode Toggle
Switches between light and dark UI themes. Preference persists between sessions.

---

## Understanding Combine Ratios

All combine ratios throughout the application use the same weighted average formula:

```
output = (signal_A x (ratio - 1) + signal_B) / ratio
```

| Ratio | Signal A | Signal B | Character |
|-------|----------|----------|-----------|
| 1.0   | 0%       | 100%     | Pure B |
| 2.0   | 50%      | 50%      | Even blend |
| 3.0   | 66.7%    | 33.3%    | A-dominant |
| 5.0   | 80%      | 20%      | Strongly A |
| 10.0  | 90%      | 10%      | Almost pure A |
| 25.0  | 96%      | 4%       | Nearly all A |

The UI shows the exact percentage split in real time as you adjust each slider. The signals being combined vary by context:

| Setting | Signal A | Signal B |
|---------|----------|----------|
| Frequency Combine | Ramp | Speed |
| Volume Combine | Ramp | Speed |
| Pulse Frequency Combine | Speed | Alpha |
| Pulse Width Combine | Speed | Alpha-Limited |
| Pulse Rise Combine | Beta-Mirrored | Speed-Inverted |

---

## Complete Processing Pipeline

```
Input Funscript (.funscript)
    |
    +---> Interpolation (at configured interval)
    |
    +---> Speed Calculation (Speed Window)
    |        |
    |        +---> Speed Signal
    |        |       |
    |        |       +---> Acceleration (Accel Window) ---> Accel Signal
    |        |
    |        +---> Speed Normalization (max or rms)
    |
    +---> Volume Ramp Generation (% per hour)
    |        |
    |        +---> Ramp Signal
    |
    +---> 1D to 2D Conversion (algorithm + parameters)
    |        |
    |        +---> Alpha / Beta (3P)
    |        |       |
    |        |       +---> Phase Shift (delay ms) ---> Alpha-2 / Beta-2
    |        |
    |        +---> Prostate Alpha / Beta (if enabled)
    |
    +---> Signal Rotation (per-axis angle)
    |        |
    |        +---> E1-E4 Response Curves ---> E1-E4 Output (4P)
    |                |
    |                +---> Phase Shift (delay ms) ---> E1-2 through E4-2
    |
    +---> Frequency Combine (Ramp + Speed) ---> frequency.funscript
    |        |
    |        +---> Min/Max clamping
    |
    +---> Volume Combine (Ramp + Speed + Rest Level) ---> volume.funscript
    |        |
    |        +---> Prostate Volume (x Multiplier, own Rest Level)
    |        +---> Normalization (if enabled)
    |
    +---> Pulse Frequency Combine (Speed + Alpha) ---> pulse-freq.funscript
    |        |
    |        +---> Min/Max clamping
    |
    +---> Pulse Width Combine (Speed + Alpha-Limited) ---> pulse-width.funscript
    |        |
    |        +---> Min/Max clamping
    |
    +---> Pulse Rise Combine (Beta-Mirrored + Speed-Inverted) ---> pulse-rise.funscript
             |
             +---> Min/Max clamping

Optional: Inverted versions of frequency, volume, pulse-freq (if Advanced options enabled)
```

---

## Quick Start Recipes

### Recipe 1: Gentle, Slow Build
Best for long relaxation sessions.
```
Rest Level: 0.6          (maintain baseline)
Ramp Up Duration: 5.0    (smooth transitions)
Speed Window: 10          (very smooth speed)
Accel Window: 5           (gradual acceleration)
Volume Ramp: 5%/hr        (very slow build)
Volume Combine: 35        (almost pure ramp)
```

### Recipe 2: Responsive, Dynamic
Best for fast-paced, interactive content.
```
Rest Level: 0.0           (silent during pauses)
Ramp Up Duration: 0.5     (quick recovery)
Speed Window: 2            (reactive to bursts)
Accel Window: 1            (sharp acceleration)
Volume Ramp: 0%/hr         (flat, no build)
Volume Combine: 12         (speed-reactive)
Frequency Combine: 2.0     (speed-dominant frequency)
```

### Recipe 3: Complementary 4-Channel
Four E1-E4 axes that take turns activating.
```
E1: Linear curve,     0deg angle   (faithful reproduction)
E2: Ease In curve,    0deg angle   (responds to strong movement only)
E3: Linear curve,     180deg angle (inverted - active when E1 is quiet)
E4: Sharp Peak curve, 0deg angle   (bursts at mid-intensity moments)
```

### Recipe 4: Subtle Layered Texture
Four channels with slight variations for richness.
```
E1: Linear curve,   0deg angle    (full range)
E2: Ease In curve,  30deg angle   (slightly compressed, high-end emphasis)
E3: Ease Out curve,  15deg angle  (slightly compressed, low-end emphasis)
E4: S-Curve,         0deg angle   (enhanced mid-range contrast)
```
