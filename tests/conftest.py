"""
conftest.py — pytest configuration for funscript-tools tests.

All tests go through cli.py only — never import upstream internals directly.
"""
import sys
from pathlib import Path

# Ensure repo root is on the path so `import cli` works
sys.path.insert(0, str(Path(__file__).parent.parent))
