# CLI Reference

All commands go through `cli.py` — the adapter layer over edger477's processing engine.

> Engine: https://github.com/edger477/funscript-tools — all algorithm credit to edger477.

```
python cli.py <command> [options]
python cli.py <command> --help      # detailed help for any command
```

---

## Commands at a glance

| Command | What it does |
|---------|-------------|
| `info` | Show metadata about a .funscript file |
| `process` | Run the full pipeline — generates all restim output files |
| `list-outputs` | List generated output files for a given input |
| `algorithms` | List 2D conversion algorithms with descriptions |
| `config show` | Print the default configuration as JSON |
| `config save` | Save default config to a file for editing |
| `preview electrode-path` | Show 2D electrode path shape for an algorithm |
| `preview frequency-blend` | Plain-language description of frequency blend settings |
| `preview pulse-shape` | Pulse silhouette for given width and rise time settings |

---

## `info`

Show metadata about a .funscript file without processing it.

```bash
python cli.py info <file>
```

```bash
# Example
python cli.py info examples/sample.funscript

# Output
File:     sample.funscript
Actions:  18
Duration: 00:10
Range:    0 – 100
```

---

## `process`

Run the full processing pipeline. Generates all restim output files.

```bash
python cli.py process <file> [--config FILE] [--output-dir DIR]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `file` | Path to the .funscript file to process |
| `--config FILE` | JSON config file (from `config save`). Uses defaults if omitted. |
| `--output-dir DIR` | Where to write output files. Default: same folder as input. |

```bash
# Default settings, outputs next to input
python cli.py process my_scene.funscript

# Custom output directory
python cli.py process my_scene.funscript --output-dir ~/restim/outputs/

# Saved config (see config save below)
python cli.py process my_scene.funscript --config my_config.json

# Both
python cli.py process my_scene.funscript --config my_config.json --output-dir ~/restim/

# Batch — process every file in a folder
for f in ~/scenes/*.funscript; do
    python cli.py process "$f" --output-dir ~/restim/
done
```

**Output files generated:**

| File | What it controls in restim |
|------|---------------------------|
| `*.alpha.funscript` | 2D electrode X position |
| `*.beta.funscript` | 2D electrode Y position |
| `*.alpha-prostate.funscript` | Prostate electrode X |
| `*.beta-prostate.funscript` | Prostate electrode Y |
| `*.frequency.funscript` | Pulse rate envelope |
| `*.pulse_frequency.funscript` | Pulse rate by action intensity |
| `*.volume.funscript` | Amplitude envelope |
| `*.volume-prostate.funscript` | Prostate amplitude |
| `*.pulse_width.funscript` | Pulse width |
| `*.pulse_rise_time.funscript` | Pulse sharpness |

---

## `list-outputs`

List generated output files for a given input stem.

```bash
python cli.py list-outputs <directory> <stem>
```

```bash
# Example
python cli.py list-outputs . my_scene

# Output
  alpha                          2.4 KB
  beta                           2.4 KB
  frequency                      1.2 KB
  ...
```

---

## `algorithms`

List all available 2D electrode path algorithms with plain-language descriptions.

```bash
python cli.py algorithms

# Output
  circular             Circular (0°–180°)
                       Smooth semi-circle. Balanced, works well for most content.

  top-right-left       Top-Right-Bottom-Left (0°–270°)
                       Wider arc. More variation, stronger contrast between strokes.

  top-left-right       Top-Left-Bottom-Right (0°–90°)
                       Narrower arc. Subtle, good for slower content.

  restim-original      Restim Original (0°–360°)
                       Full circle with random direction changes. Most unpredictable.
```

Set your preferred algorithm in a saved config:

```bash
python cli.py config save my_config.json
# Edit my_config.json → alpha_beta_generation.algorithm → "circular"
python cli.py process scene.funscript --config my_config.json
```

---

## `config show`

Print the default configuration (or a single section) as formatted JSON.

```bash
python cli.py config show [section]
```

```bash
# Full config
python cli.py config show

# Just the frequency settings
python cli.py config show frequency

# Just the pulse settings
python cli.py config show pulse
```

Available sections: `general`, `frequency`, `pulse`, `volume`,
`alpha_beta_generation`, `prostate_generation`, `advanced`,
`options`, `positional_axes`, `speed`

---

## `config save`

Save the default configuration to a JSON file so you can edit and reuse it.

```bash
python cli.py config save <output> [--force]
```

```bash
# Save defaults
python cli.py config save my_config.json

# Overwrite existing file
python cli.py config save my_config.json --force

# Typical workflow
python cli.py config save configs/gentle.json
# → edit gentle.json: lower frequency ratios, softer pulse rise
python cli.py process scene.funscript --config configs/gentle.json
```

**Key settings to tune:**

| JSON path | What it changes |
|-----------|----------------|
| `alpha_beta_generation.algorithm` | 2D path algorithm (`circular`, `top-right-left`, etc.) |
| `alpha_beta_generation.min_distance_from_center` | How wide the electrode motion range is (0.1–0.9) |
| `frequency.frequency_ramp_combine_ratio` | Slow build vs scene energy blend (1–10) |
| `frequency.pulse_freq_min` / `pulse_freq_max` | Pulse rate output range (0.0–1.0) |
| `pulse.pulse_width_min` / `pulse_width_max` | Pulse width range |
| `pulse.pulse_rise_min` / `pulse_rise_max` | Pulse sharpness — low = sharp, high = soft |
| `volume.volume_ramp_combine_ratio` | Volume blend ratio |
| `options.overwrite_existing_files` | Whether to regenerate existing outputs |

---

## `preview electrode-path`

Show the 2D electrode path shape an algorithm produces — no processing required.

```bash
python cli.py preview electrode-path [--algorithm ALGO] [--min-distance N]
                                     [--speed-threshold N] [--points N] [--json]
```

```bash
# Default algorithm (circular)
python cli.py preview electrode-path

# Output
Algorithm:    Circular (0°–180°)
Description:  Smooth semi-circle. Balanced, works well for most content.
Points:       200 alpha, 200 beta
Alpha range:  0.100 – 0.900
Beta range:   0.500 – 0.900

# Compare algorithms
python cli.py preview electrode-path --algorithm top-right-left
python cli.py preview electrode-path --algorithm restim-original

# Wider motion range
python cli.py preview electrode-path --algorithm circular --min-distance 0.3

# Machine-readable output (pipe to plotting tools)
python cli.py preview electrode-path --json
```

---

## `preview frequency-blend`

Translate frequency combine ratios into plain English.

```bash
python cli.py preview frequency-blend [--ramp-ratio N] [--pulse-ratio N] [--json]
```

```bash
# Default ratios
python cli.py preview frequency-blend

# Output
  Frequency feel: balanced — responsive with a slow build
  Frequency:  50.0% slow build + 50.0% scene energy
  Pulse:      66.7% scene energy + 33.3% spatial position

# Ramp-heavy (slow, gradual build)
python cli.py preview frequency-blend --ramp-ratio 8

# Output
  Frequency feel: gradual, builds slowly
  Frequency:  87.5% slow build + 12.5% scene energy

# Speed-heavy (reactive to action)
python cli.py preview frequency-blend --ramp-ratio 1

# Output
  Frequency feel: reactive, follows action closely
  Frequency:  0.0% slow build + 100.0% scene energy
```

---

## `preview pulse-shape`

Describe the pulse silhouette for given width and rise time settings.

```bash
python cli.py preview pulse-shape [--width-min N] [--width-max N]
                                  [--rise-min N] [--rise-max N] [--json]
```

```bash
# Default settings
python cli.py preview pulse-shape

# Output
  Pulse: medium width, medium — smooth ramp
  Width (mid): 0.275
  Rise  (mid): 0.4
  Sharpness:   medium

# Sharp, narrow pulses
python cli.py preview pulse-shape --width-min 0.05 --width-max 0.2 --rise-min 0.0 --rise-max 0.05

# Output
  Pulse: narrow width, sharp — immediate onset

# Soft, wide pulses
python cli.py preview pulse-shape --width-min 0.3 --width-max 0.6 --rise-min 0.5 --rise-max 0.9

# Output
  Pulse: wide width, soft — gentle build
```

---

## Using `--json` for scripting

All `preview` commands and `config show` output valid JSON with `--json`,
making them pipeable to other tools:

```bash
# Pipe to Python for further processing
python cli.py preview electrode-path --json | python -c "
import json, sys
data = json.load(sys.stdin)
print(f'Path covers {len(data[\"alpha\"])} points')
"

# Pipe to jq
python cli.py config show frequency --json | jq '.pulse_freq_min'

# Save preview data for plotting
python cli.py preview electrode-path --algorithm circular --json > path_circular.json
python cli.py preview electrode-path --algorithm top-right-left --json > path_trl.json
```
