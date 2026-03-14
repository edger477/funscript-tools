"""
examples/process_default.py

Simplest possible usage: process a funscript with all defaults.
Also demonstrates the preview functions — the same calls the UI uses
to show visualizations without running the full pipeline.

Usage:
    python examples/process_default.py
    python examples/process_default.py path/to/your/file.funscript
    python examples/process_default.py path/to/file.funscript --output-dir /some/dir
"""

import argparse
import sys
from pathlib import Path

# cli.py is the only import needed — it wraps all upstream internals.
sys.path.insert(0, str(Path(__file__).parent.parent))
import cli


def main():
    parser = argparse.ArgumentParser(description="Process a funscript with default settings")
    parser.add_argument(
        "file",
        nargs="?",
        default=str(Path(__file__).parent / "sample.funscript"),
        help="Path to .funscript file (default: examples/sample.funscript)",
    )
    parser.add_argument("--output-dir", help="Output directory (default: same as input)")
    args = parser.parse_args()

    print("=" * 50)
    print(" funscript-tools — default processing")
    print(" Engine by edger477")
    print("=" * 50)

    # ── Step 1: load and inspect the file ────────────────────────────────────
    print("\n[ File Info ]")
    try:
        info = cli.load_file(args.file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Name:     {info['name']}")
    print(f"  Actions:  {info['actions']}")
    print(f"  Duration: {info['duration_fmt']}")
    print(f"  Range:    {info['pos_min']:.0f} – {info['pos_max']:.0f}")

    # ── Step 2: inspect default config ───────────────────────────────────────
    print("\n[ Default Config (key creative settings) ]")
    config = cli.get_default_config()
    ab = config["alpha_beta_generation"]
    fq = config["frequency"]
    pu = config["pulse"]
    print(f"  Algorithm:          {ab['algorithm']}")
    print(f"  Min dist. center:   {ab['min_distance_from_center']}")
    print(f"  Freq ramp blend:    {fq['frequency_ramp_combine_ratio']}")
    print(f"  Pulse freq range:   {fq['pulse_freq_min']} – {fq['pulse_freq_max']}")
    print(f"  Pulse width range:  {pu['pulse_width_min']} – {pu['pulse_width_max']}")

    # ── Step 3: preview without processing (UI uses these for live viz) ───────
    print("\n[ Previews ]")

    path_data = cli.preview_electrode_path(
        algorithm=ab["algorithm"],
        min_distance_from_center=ab["min_distance_from_center"],
    )
    print(f"  Electrode path:  {path_data['label']}")
    print(f"                   {path_data['description']}")
    print(f"                   {len(path_data['alpha'])} points generated")

    blend = cli.preview_frequency_blend(
        frequency_ramp_combine_ratio=fq["frequency_ramp_combine_ratio"],
        pulse_frequency_combine_ratio=fq["pulse_frequency_combine_ratio"],
    )
    print(f"  Frequency blend: {blend['overall_label']}")
    print(f"                   {blend['frequency_label']}")

    pulse = cli.preview_pulse_shape(
        width_min=pu["pulse_width_min"],
        width_max=pu["pulse_width_max"],
        rise_min=pu["pulse_rise_min"],
        rise_max=pu["pulse_rise_max"],
    )
    print(f"  Pulse shape:     {pulse['label']}")

    # ── Step 4: run the full pipeline ─────────────────────────────────────────
    print("\n[ Processing ]")
    if args.output_dir:
        config.setdefault("advanced", {})["custom_output_directory"] = args.output_dir

    def on_progress(pct, msg):
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  {msg:<45}", end="", flush=True)

    result = cli.process(args.file, config, on_progress=on_progress)
    print()  # newline after progress

    if not result["success"]:
        print(f"\nError: {result['error']}", file=sys.stderr)
        sys.exit(1)

    # ── Step 5: show outputs ──────────────────────────────────────────────────
    print(f"\n[ Outputs — {len(result['outputs'])} files ]")
    for out in result["outputs"]:
        size_kb = out["size_bytes"] / 1024
        print(f"  {out['suffix']:<30} {size_kb:6.1f} KB")

    print("\nDone.")
    return result


if __name__ == "__main__":
    main()
