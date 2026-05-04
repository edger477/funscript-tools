#!/usr/bin/env python3
"""
Standalone Funscript Comparison Viewer.

Usage:
    python funscript_compare.py [file_a.funscript [file_b.funscript]]

Both file arguments are optional. If omitted, load files via the
in-window Browse buttons.
"""

from ui.compare_viewer import main

if __name__ == '__main__':
    main()
