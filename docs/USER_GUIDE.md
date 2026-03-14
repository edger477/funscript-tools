# User Guide

> **Credit:** The processing engine is [edger477's funscript-tools](https://github.com/edger477/funscript-tools).
> This guide covers the CLI adapter layer built on top of it.

---

## What this tool does

You have a `.funscript` — a timeline of position movements, originally created for
a stroker device. This tool converts that file into a set of estim (e-stim) control
signals for use in [restim](https://github.com/edger477/restim).

One `.funscript` in → ten output files out. Each output controls a different
dimension of what you feel.

---

## The ten output files

| File | What it controls | What you feel |
|------|-----------------|---------------|
| `*.alpha.funscript` | Electrode X position | Left–right movement of sensation |
| `*.beta.funscript` | Electrode Y position | Up–down movement of sensation |
| `*.alpha-prostate.funscript` | Prostate electrode X | Spatial position for prostate channel |
| `*.beta-prostate.funscript` | Prostate electrode Y | Spatial position for prostate channel |
| `*.frequency.funscript` | Pulse rate envelope | Overall intensity rhythm |
| `*.pulse_frequency.funscript` | Pulse rate by action | How directly action speed maps to sensation rate |
| `*.volume.funscript` | Amplitude envelope | Overall strength |
| `*.volume-prostate.funscript` | Prostate amplitude | Prostate channel strength |
| `*.pulse_width.funscript` | Pulse duration | Fullness vs sharpness of each pulse |
| `*.pulse_rise_time.funscript` | Pulse attack | Hard edge vs soft onset of each pulse |

Think of the alpha/beta pair as *where* you feel it, frequency as *how fast*, pulse shape
as *what kind*, and volume as *how strong*.

---

## The three creative decisions

Most of the config is infrastructure you set once. Three things actually change
the character of the output:

### 1. Algorithm — where the sensation moves

The algorithm controls the path the electrode position traces as the source
funscript plays back. Different algorithms produce different spatial movement patterns.

| Algorithm | Path shape | Character |
|-----------|------------|-----------|
| `circular` | Semi-circle (0°–180°) | Smooth, balanced, good for most content |
| `top-right-left` | Wide arc (0°–270°) | More variation, stronger contrast between strokes |
| `top-left-right` | Narrow arc (0°–90°) | Subtle, suited to slower, gentler content |
| `restim-original` | Full circle with random reversals | Unpredictable, most varied |

**To explore algorithms before committing:**
```bash
python cli.py algorithms
python cli.py preview electrode-path --algorithm circular
python cli.py preview electrode-path --algorithm top-right-left
python cli.py preview electrode-path --algorithm restim-original
```

**What `--min-distance` does:**
The `min_distance_from_center` config setting (0.1–0.9) controls how far from center
the electrode can range. Higher = wider sweep, more pronounced movement.

```
low (0.1)   ████░░░░░░   electrode stays near center — subtle
mid (0.5)   ██░░░░░░░░   moderate range
high (0.9)  █░░░░░░░░░   full range — strong, sweeping movement
```

---

### 2. Frequency blend — how sensation tracks the action

The frequency output is a blend of two signals:

- **Scene energy (ramp):** A slow-building intensity curve that rises and falls with
  the overall pace of a scene. Think of it as the "mood arc."
- **Action speed:** Direct tracking of how fast the source funscript is moving.
  Fast strokes → faster pulse rate, immediately.

The `frequency_ramp_combine_ratio` (1–10) sets the blend:

```
ratio 1:  ████████████  100% action speed — highly reactive, follows every stroke
ratio 3:  ██████░░░░░░   75% action speed + 25% ramp
ratio 5:  ████████░░░░   50% / 50%  ← default, balanced
ratio 8:  ░░░░░░░░░░██   12% action speed + 88% ramp — slow, gradual build
ratio 10: ░░░░░░░░░░░░  100% ramp — ignores action speed entirely
```

**To hear what these mean before processing:**
```bash
python cli.py preview frequency-blend --ramp-ratio 1
python cli.py preview frequency-blend --ramp-ratio 5
python cli.py preview frequency-blend --ramp-ratio 8
```

**Rule of thumb:**
- Fast, intense content → lower ratio (reactive)
- Slow, scene-building content → higher ratio (gradual build)
- Mixed content → default (5)

---

### 3. Pulse shape — the character of each pulse

Each electrical pulse has two physical dimensions:

**Width** (how long each pulse lasts):
```
narrow  ▐█▌          short, sharp individual pulses
medium  ▐███▌
wide    ▐███████▌     long, full pulses — more "filled in" sensation
```

**Rise time** (how the pulse attacks):
```
sharp  ▐█▌  ▐█▌  immediate onset, hard edge
       ▐/▌  ▐\▌
soft   ▐  ▌▐  ▌  gradual build-in, rounded feel
```

The config sets a min and max for each — the output file sweeps between them based
on the source funscript's intensity.

```bash
python cli.py preview pulse-shape --width-min 0.05 --width-max 0.2 --rise-min 0.0 --rise-max 0.05
# → narrow width, sharp — immediate onset

python cli.py preview pulse-shape --width-min 0.3 --width-max 0.6 --rise-min 0.5 --rise-max 0.9
# → wide width, soft — gentle build
```

---

## Typical workflow

### One-off: explore and process

```bash
# 1. Inspect your file
python cli.py info my_scene.funscript

# 2. Preview your creative settings (no file written)
python cli.py preview electrode-path --algorithm circular
python cli.py preview frequency-blend --ramp-ratio 5
python cli.py preview pulse-shape

# 3. Process with defaults
python cli.py process my_scene.funscript

# 4. Check what was generated
python cli.py list-outputs . my_scene
```

### Iterative: save a config and tune it

```bash
# Save defaults to a file
python cli.py config save configs/my_style.json

# Edit the file — adjust algorithm, frequency blend, pulse shape
# (see Key settings below)

# Process with your config
python cli.py process my_scene.funscript --config configs/my_style.json

# Regenerate to refine
python cli.py process my_scene.funscript --config configs/my_style.json
```

### Toolchain: batch process a library

```bash
# Process every scene with the same config
for f in ~/scenes/*.funscript; do
    python cli.py process "$f" \
        --config configs/my_style.json \
        --output-dir ~/restim/outputs/
done
```

Or from Python (e.g. in a build script or CI pipeline):

```python
from cli import load_file, get_default_config, process, list_outputs
import json, pathlib

config = json.loads(pathlib.Path("configs/my_style.json").read_text())
scenes = pathlib.Path("~/scenes").expanduser().glob("*.funscript")

for scene in scenes:
    info = load_file(str(scene))
    print(f"Processing {info['name']} ({info['duration_fmt']})…")
    result = process(str(scene), config)
    if result["success"]:
        for out in result["outputs"]:
            print(f"  ✓ {out['suffix']}")
    else:
        print(f"  ✗ {result['error']}")
```

---

## Key config settings

Run `python cli.py config save my_config.json` to get a full config template.
The settings you'll actually want to change:

| Setting | Where | What to change it for |
|---------|-------|-----------------------|
| `algorithm` | `alpha_beta_generation` | Spatial movement character |
| `min_distance_from_center` | `alpha_beta_generation` | How wide the spatial sweep is |
| `frequency_ramp_combine_ratio` | `frequency` | Reactive vs gradual build |
| `pulse_freq_min` / `pulse_freq_max` | `frequency` | Overall pulse rate range |
| `pulse_width_min` / `pulse_width_max` | `pulse` | Pulse fullness range |
| `pulse_rise_min` / `pulse_rise_max` | `pulse` | Sharp vs soft attack range |
| `rest_level` | `general` | Baseline intensity during slow sections |
| `overwrite_existing_files` | `options` | Whether to regenerate existing outputs |

---

## Automating with `--json`

All `preview` commands return JSON when called with `--json`. This is designed
for toolchain use — pipe data to a plotter, feed it to a UI, or drive a CI
artifact check.

```bash
# Capture electrode path data for plotting
python cli.py preview electrode-path --algorithm circular --json > circular.json
python cli.py preview electrode-path --algorithm restim-original --json > original.json

# Compare frequency blend options
python cli.py preview frequency-blend --ramp-ratio 1 --json
python cli.py preview frequency-blend --ramp-ratio 8 --json

# Pull a single config value
python cli.py config show frequency | python -c "
import json, sys
cfg = json.load(sys.stdin)
print(f'Pulse rate range: {cfg[\"pulse_freq_min\"]} – {cfg[\"pulse_freq_max\"]}')
"
```

---

## Named config profiles (recommended for toolchains)

Save multiple profiles for different content types and call them by name:

```
configs/
  gentle.json       # soft pulse, gradual build, narrow arc
  reactive.json     # sharp pulse, high action-tracking, wide arc
  scene-builder.json  # high ramp ratio, builds over time
  default.json      # baseline — good starting point
```

```bash
# In a Makefile or build script:
python cli.py process $SCENE --config configs/reactive.json --output-dir dist/
```

---

## Next steps

- **Visualizations:** The UI (coming in FunScriptForge) shows live before/after
  waveform comparisons for every setting above. Every slider move updates the
  preview in real time.
- **More docs:** See [CLI_REFERENCE.md](CLI_REFERENCE.md) for flag-level detail
  on every command.
- **MkDocs:** This doc folder will be surfaced as a searchable site via GitHub Pages.
