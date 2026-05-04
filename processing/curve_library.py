"""
Persistent curve library — stores user-saved response curves independently
of the full motion-axis preset system. Curves are keyed by user-chosen
names and live in curve_library.json next to config.json.
"""

import json
import copy
from pathlib import Path
from typing import Dict, Any, Optional, List


_LIBRARY_FILENAME = 'curve_library.json'


def _library_path() -> Path:
    """Return the path to the curve library file."""
    return Path(__file__).parent.parent / _LIBRARY_FILENAME


def load_library() -> Dict[str, Dict[str, Any]]:
    """Load the curve library from disk. Returns empty dict if missing."""
    path = _library_path()
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def save_library(library: Dict[str, Dict[str, Any]]) -> None:
    """Write the curve library to disk."""
    path = _library_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(library, f, indent=2)


def save_curve(name: str, curve: Dict[str, Any]) -> None:
    """Save a single curve to the library (overwrites if name exists)."""
    lib = load_library()
    lib[name] = copy.deepcopy(curve)
    save_library(lib)


def delete_curve(name: str) -> bool:
    """Delete a curve from the library. Returns True if it existed."""
    lib = load_library()
    if name in lib:
        del lib[name]
        save_library(lib)
        return True
    return False


def rename_curve(old_name: str, new_name: str) -> bool:
    """Rename a curve. Returns True if successful."""
    lib = load_library()
    if old_name not in lib or new_name in lib:
        return False
    lib[new_name] = lib.pop(old_name)
    save_library(lib)
    return True


def get_curve(name: str) -> Optional[Dict[str, Any]]:
    """Get a single curve by name, or None if not found."""
    lib = load_library()
    curve = lib.get(name)
    return copy.deepcopy(curve) if curve else None


def list_curves() -> List[str]:
    """Return sorted list of curve names in the library."""
    return sorted(load_library().keys())
