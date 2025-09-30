"""
Motion Axis Generation module for creating E1-E4 axis files.

Generates motion axis files using linear mapping with configurable response curves
as an alternative to traditional alpha/beta generation.
"""

from typing import Dict, Any, List, Tuple
from pathlib import Path
from funscript import Funscript
from .linear_mapping import (
    apply_response_curve_to_funscript,
    get_default_response_curves,
    validate_control_points
)


def generate_motion_axes(
    main_funscript: Funscript,
    config: Dict[str, Any],
    output_directory: Path
) -> Dict[str, Path]:
    """
    Generate all enabled motion axis files (E1-E4) from main funscript.

    Args:
        main_funscript: Source funscript for generation
        config: Motion axis configuration
        output_directory: Directory to save generated files

    Returns:
        Dictionary mapping axis names to generated file paths
    """
    generated_files = {}
    default_curves = get_default_response_curves()

    for axis_name in ['e1', 'e2', 'e3', 'e4']:
        axis_config = config.get(axis_name, {})

        if not axis_config.get('enabled', False):
            continue

        # Get curve configuration
        curve_config = axis_config.get('curve', default_curves[axis_name])
        control_points = curve_config.get('control_points', default_curves[axis_name]['control_points'])

        # Validate control points
        if not validate_control_points(control_points):
            print(f"Warning: Invalid control points for {axis_name}, using default")
            control_points = default_curves[axis_name]['control_points']

        # Generate axis funscript
        axis_funscript = apply_response_curve_to_funscript(
            main_funscript,
            control_points
        )

        # Save to file
        output_path = output_directory / f"{output_directory.stem}.{axis_name}.funscript"
        axis_funscript.save_to_path(output_path)
        generated_files[axis_name] = output_path

        print(f"Generated {axis_name} axis: {output_path}")

    return generated_files


def get_motion_axis_config_template() -> Dict[str, Any]:
    """
    Get template configuration for motion axis generation.

    Returns:
        Template configuration dictionary
    """
    default_curves = get_default_response_curves()

    return {
        "enabled": True,
        "mode": "motion_axis",  # or "legacy" for alpha/beta
        "e1": {
            "enabled": True,
            "curve": default_curves["e1"]
        },
        "e2": {
            "enabled": True,
            "curve": default_curves["e2"]
        },
        "e3": {
            "enabled": False,  # Disabled by default
            "curve": default_curves["e3"]
        },
        "e4": {
            "enabled": False,  # Disabled by default
            "curve": default_curves["e4"]
        }
    }


def validate_motion_axis_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate motion axis configuration.

    Args:
        config: Motion axis configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not isinstance(config, dict):
        errors.append("Configuration must be a dictionary")
        return errors

    # Check mode
    mode = config.get('mode', 'motion_axis')
    if mode not in ['motion_axis', 'legacy']:
        errors.append(f"Invalid mode: {mode}. Must be 'motion_axis' or 'legacy'")

    # Check axis configurations
    for axis_name in ['e1', 'e2', 'e3', 'e4']:
        axis_config = config.get(axis_name, {})

        if not isinstance(axis_config, dict):
            errors.append(f"{axis_name} configuration must be a dictionary")
            continue

        # Check curve configuration if axis is enabled
        if axis_config.get('enabled', False):
            curve_config = axis_config.get('curve', {})

            if not isinstance(curve_config, dict):
                errors.append(f"{axis_name} curve configuration must be a dictionary")
                continue

            control_points = curve_config.get('control_points', [])
            if not validate_control_points(control_points):
                errors.append(f"{axis_name} has invalid control points")


    return errors


def create_custom_curve(
    name: str,
    description: str,
    control_points: List[Tuple[float, float]]
) -> Dict[str, Any]:
    """
    Create a custom response curve configuration.

    Args:
        name: Human-readable curve name
        description: Curve description
        control_points: List of (input, output) control points

    Returns:
        Curve configuration dictionary
    """
    if not validate_control_points(control_points):
        raise ValueError("Invalid control points provided")

    return {
        "name": name,
        "description": description,
        "control_points": control_points
    }


def get_curve_presets() -> Dict[str, Dict[str, Any]]:
    """
    Get all available curve presets including defaults and common variations.

    Returns:
        Dictionary of preset curve configurations
    """
    presets = get_default_response_curves()

    # Add additional preset variations
    presets.update({
        "inverted": {
            "name": "Inverted",
            "description": "Inverted linear mapping",
            "control_points": [(0.0, 1.0), (1.0, 0.0)]
        },
        "s_curve": {
            "name": "S-Curve",
            "description": "Smooth acceleration and deceleration",
            "control_points": [(0.0, 0.0), (0.2, 0.1), (0.5, 0.5), (0.8, 0.9), (1.0, 1.0)]
        },
        "sharp_peak": {
            "name": "Sharp Peak",
            "description": "Sharp emphasis on middle range",
            "control_points": [(0.0, 0.0), (0.4, 0.1), (0.5, 1.0), (0.6, 0.1), (1.0, 0.0)]
        },
        "gentle_wave": {
            "name": "Gentle Wave",
            "description": "Gentle wave-like response",
            "control_points": [(0.0, 0.2), (0.25, 0.7), (0.5, 0.3), (0.75, 0.8), (1.0, 0.4)]
        }
    })

    return presets


def copy_existing_axis_files(
    input_directory: Path,
    output_directory: Path,
    filename_base: str,
    enabled_axes: List[str]
) -> Dict[str, Path]:
    """
    Copy existing motion axis files if they exist.

    Args:
        input_directory: Directory containing existing files
        output_directory: Directory to copy files to
        filename_base: Base filename without extension
        enabled_axes: List of axis names to look for

    Returns:
        Dictionary mapping axis names to copied file paths
    """
    copied_files = {}

    for axis_name in enabled_axes:
        source_path = input_directory / f"{filename_base}.{axis_name}.funscript"

        if source_path.exists():
            dest_path = output_directory / f"{filename_base}.{axis_name}.funscript"

            # Copy file (could use shutil.copy2 for metadata preservation)
            with open(source_path, 'r') as src, open(dest_path, 'w') as dst:
                dst.write(src.read())

            copied_files[axis_name] = dest_path
            print(f"Copied existing {axis_name} file: {dest_path}")

    return copied_files