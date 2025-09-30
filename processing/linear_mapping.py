"""
Linear mapping module for Motion Axis Generation system.

Provides mathematical functions for mapping input values through configurable response curves
using linear interpolation between control points.
"""

from typing import List, Tuple, Dict, Any
import numpy as np
from funscript import Funscript


def apply_linear_response_curve(value: float, control_points: List[Tuple[float, float]]) -> float:
    """
    Apply linear response curve to a single value using control points.

    Args:
        value: Input value (0.0-1.0)
        control_points: List of (input, output) tuples defining the curve

    Returns:
        Mapped output value (0.0-1.0)
    """
    # Clamp input value to valid range
    value = max(0.0, min(1.0, value))

    # Sort control points by input value
    sorted_points = sorted(control_points, key=lambda p: p[0])

    # Find the two control points to interpolate between
    for i in range(len(sorted_points) - 1):
        x1, y1 = sorted_points[i]
        x2, y2 = sorted_points[i + 1]

        if x1 <= value <= x2:
            # Linear interpolation
            if x2 == x1:  # Avoid division by zero
                return y1
            t = (value - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)

    # If value is outside range, use nearest point
    if value <= sorted_points[0][0]:
        return sorted_points[0][1]
    else:
        return sorted_points[-1][1]


def apply_response_curve_to_funscript(
    funscript: Funscript,
    control_points: List[Tuple[float, float]]
) -> Funscript:
    """
    Apply response curve to entire funscript.

    Args:
        funscript: Input funscript
        control_points: List of (input, output) tuples defining the curve

    Returns:
        New funscript with curve applied
    """
    # Get time and position arrays
    times = funscript.x.copy()
    positions = funscript.y.copy()  # Already normalized 0-1

    # Apply response curve to each position
    new_positions = []
    for pos in positions:
        # Apply response curve and clamp to valid range
        mapped_pos = apply_linear_response_curve(pos, control_points)
        final_pos = max(0.0, min(1.0, mapped_pos))
        new_positions.append(final_pos)

    return Funscript(times, new_positions)


def get_default_response_curves() -> Dict[str, Dict[str, Any]]:
    """
    Get default response curve definitions for all motion axes.

    Returns:
        Dictionary containing default curve configurations
    """
    return {
        "e1": {
            "name": "Linear",
            "description": "Direct 1:1 mapping",
            "control_points": [(0.0, 0.0), (1.0, 1.0)]
        },
        "e2": {
            "name": "Ease In",
            "description": "Gradual start, strong finish",
            "control_points": [(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)]
        },
        "e3": {
            "name": "Ease Out",
            "description": "Strong start, gradual finish",
            "control_points": [(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)]
        },
        "e4": {
            "name": "Bell Curve",
            "description": "Emphasis on middle range",
            "control_points": [(0.0, 0.0), (0.25, 0.3), (0.5, 1.0), (0.75, 0.3), (1.0, 0.0)]
        }
    }


def validate_control_points(control_points: List[Tuple[float, float]]) -> bool:
    """
    Validate control points for response curve.

    Args:
        control_points: List of (input, output) tuples

    Returns:
        True if valid, False otherwise
    """
    if len(control_points) < 2:
        return False

    for x, y in control_points:
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            return False

    # Check that input values are unique when sorted
    x_values = [x for x, y in control_points]
    if len(set(x_values)) != len(x_values):
        return False

    return True


def normalize_funscript_positions(funscript: Funscript) -> List[float]:
    """
    Extract normalized position values (0.0-1.0) from funscript.

    Args:
        funscript: Input funscript

    Returns:
        List of normalized position values
    """
    return funscript.y.tolist()  # Already normalized 0-1


def create_preview_data(
    control_points: List[Tuple[float, float]],
    num_points: int = 100
) -> Tuple[List[float], List[float]]:
    """
    Generate preview data for plotting response curves.

    Args:
        control_points: Response curve definition
        num_points: Number of points to generate for smooth curve

    Returns:
        Tuple of (input_values, output_values) for plotting
    """
    input_values = [i / (num_points - 1) for i in range(num_points)]
    output_values = []

    for x in input_values:
        y = apply_linear_response_curve(x, control_points)
        y = max(0.0, min(1.0, y))  # Clamp to valid range
        output_values.append(y)

    return input_values, output_values