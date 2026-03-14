#!/usr/bin/env bash
# examples/process_default.sh
#
# Simplest possible usage: process a funscript with all defaults.
# Outputs land next to the input file.
#
# Usage:
#   ./examples/process_default.sh
#   ./examples/process_default.sh path/to/your/file.funscript
#   ./examples/process_default.sh path/to/file.funscript --output-dir /some/dir

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT="${1:-$SCRIPT_DIR/sample.funscript}"
SHIFT_DONE=false
if [ $# -ge 1 ]; then shift; SHIFT_DONE=true; fi

echo "========================================"
echo " funscript-tools — default processing"
echo " Engine by edger477"
echo "========================================"
echo

# ── Step 1: show file info ────────────────────────────────────────────────────
echo "[ Info ]"
python "$REPO_ROOT/cli.py" info "$INPUT"
echo

# ── Step 2: process with defaults ────────────────────────────────────────────
echo "[ Processing ]"
python "$REPO_ROOT/cli.py" process "$INPUT" "$@"
echo

# ── Step 3: list what was generated ──────────────────────────────────────────
STEM="$(basename "$INPUT" .funscript)"
DIR="$(dirname "$INPUT")"

echo "[ Outputs ]"
python "$REPO_ROOT/cli.py" list-outputs "$DIR" "$STEM"
echo
echo "Done."
