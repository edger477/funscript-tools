# Examples

These examples show the two ways to drive funscript-tools:

- **Shell script** — drop into a build pipeline, file watcher, or batch job
- **Python script** — import `cli.py` directly for scripted or automated workflows

Both use the same default settings and produce the same outputs.
They are also the foundation of the test suite — `tests/test_cli.py` runs
the same scenarios with assertions instead of printed output.

> Processing engine by edger477: https://github.com/edger477/funscript-tools
> All algorithm credit belongs to edger477 and contributors.

---

## Why you might want these

| Scenario | Use |
|----------|-----|
| You have a config you like and just want to process new files quickly | bash script in a loop or file watcher |
| You're building a pipeline that generates restim-ready files as part of a larger workflow | Python import — call `cli.process()` programmatically |
| You want to understand what cli.py exposes before building a UI | Python script — it demos every public function |
| You want to verify your install is working | Run either script against `sample.funscript` |

---

## Prerequisites

```bash
# From the repo root
pip install -r requirements.txt
```

Python 3.10+ required. No other setup needed.

---

## The sample file

`sample.funscript` is a minimal 10-second funscript with realistic up/down
motion. It's used by both examples and by the test suite. You can replace it
with any `.funscript` file from your own library.

**What's in it:** 18 actions over 10 seconds, position range 0–100.

---

## process_default.sh

Processes a funscript file using all default settings.
Outputs are written next to the input file.

### What it does

1. Shows file info (name, action count, duration, position range)
2. Runs the full processing pipeline with default config
3. Lists all generated output files with sizes

### Run it

```bash
# Against the included sample
bash examples/process_default.sh

# Against your own file
bash examples/process_default.sh path/to/your/file.funscript

# With a custom output directory
bash examples/process_default.sh path/to/file.funscript --output-dir ~/restim/outputs/
```

### Expected output

```
========================================
 funscript-tools — default processing
 Engine by edger477
========================================

[ Info ]
  File:     sample.funscript
  Actions:  18
  Duration: 00:10
  Range:    0 – 100

[ Processing ]
  [████████████████████] 100%  Processing complete!

[ Outputs ]
  alpha                          2.4 KB
  alpha-prostate                 1.8 KB
  beta                           2.4 KB
  beta-prostate                  1.8 KB
  frequency                      1.2 KB
  pulse_frequency                1.3 KB
  pulse_rise_time                1.1 KB
  pulse_width                    1.2 KB
  volume                         1.1 KB
  volume-prostate                1.0 KB

Done.
```

File sizes will vary with input length and config.

---

## process_default.py

The Python equivalent — and a tour of every public `cli.py` function.

In addition to processing the file, it also calls the **preview functions**:
fast computations that return visualization data without writing any files.
These are the same calls the UI makes to update plots on every slider move.

### What it does

1. `cli.load_file()` — loads the funscript, returns metadata + waveform arrays
2. `cli.get_default_config()` — shows the key creative settings
3. `cli.preview_electrode_path()` — 2D path shape data (no file I/O)
4. `cli.preview_frequency_blend()` — plain-language blend description
5. `cli.preview_pulse_shape()` — pulse silhouette data
6. `cli.process()` — runs the full pipeline, returns output file list
7. Shows all generated outputs with sizes

### Run it

```bash
# Against the included sample
python examples/process_default.py

# Against your own file
python examples/process_default.py path/to/your/file.funscript

# With a custom output directory
python examples/process_default.py path/to/file.funscript --output-dir ~/restim/outputs/
```

### Expected output

```
==================================================
 funscript-tools — default processing
 Engine by edger477
==================================================

[ File Info ]
  Name:     sample.funscript
  Actions:  18
  Duration: 00:10
  Range:    0 – 100

[ Default Config (key creative settings) ]
  Algorithm:          top-right-left
  Min dist. center:   0.1
  Freq ramp blend:    2
  Pulse freq range:   0.4 – 0.95
  Pulse width range:  0.1 – 0.45

[ Previews ]
  Electrode path:  Top-Right-Bottom-Left (0°–270°)
                   Wider arc. More variation, stronger contrast between strokes.
                   200 points generated
  Frequency blend: Frequency feel: gradual, builds slowly
                   50.0% slow build + 50.0% scene energy
  Pulse shape:     Pulse: medium width, medium — smooth ramp

[ Processing ]
  [████████████████████] 100%  Processing complete!

[ Outputs — 10 files ]
  alpha                           2.4 KB
  alpha-prostate                  1.8 KB
  beta                            2.4 KB
  beta-prostate                   1.8 KB
  frequency                       1.2 KB
  pulse_frequency                 1.3 KB
  pulse_rise_time                 1.1 KB
  pulse_width                     1.2 KB
  volume                          1.1 KB
  volume-prostate                 1.0 KB

Done.
```

---

## Output files — what they are

All outputs are `.funscript` files that restim reads to control estim parameters:

| File | What it controls |
|------|-----------------|
| `alpha`, `beta` | 2D electrode position — *where* on the pad the stimulus sits |
| `alpha-prostate`, `beta-prostate` | Same for prostate electrode geometry |
| `frequency` | Pulse rate envelope — how fast pulses fire over time |
| `pulse_frequency` | Pulse rate modulated by action intensity |
| `volume` | Amplitude envelope — how strong the signal is |
| `volume-prostate` | Amplitude for the prostate channel |
| `pulse_width` | How wide each individual pulse is |
| `pulse_rise_time` | How fast each pulse ramps up — sharpness vs softness |

---

## Using as a batch pipeline

```bash
# Process every .funscript in a directory
for f in ~/scenes/*.funscript; do
    bash examples/process_default.sh "$f" --output-dir ~/restim/
done
```

```python
# Python batch processing
import cli

config = cli.get_default_config()
# Tune config once here if you want non-default settings

for path in Path("~/scenes").expanduser().glob("*.funscript"):
    result = cli.process(str(path), config)
    if result["success"]:
        print(f"{path.name}: {len(result['outputs'])} files generated")
    else:
        print(f"{path.name}: FAILED — {result['error']}")
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'numpy'`**
Run `pip install -r requirements.txt` from the repo root.

**`FileNotFoundError` or empty outputs**
Check that your input file ends in `.funscript` and is valid JSON.
Run `python cli.py info your_file.funscript` to verify it loads.

**Outputs written to the wrong place**
By default, outputs go next to the input file. Use `--output-dir` to redirect.
