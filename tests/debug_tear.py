#!/usr/bin/env python3
"""
Debug the tear-shaped algorithm to see what's happening.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))

from funscript import Funscript
from processing.funscript_prostate_2d import _find_local_extrema, _convert_tear_shaped
from processing.basic_transforms import invert_funscript

def debug_tear_shaped():
    """Debug the tear-shaped algorithm step by step."""
    print("Debugging tear-shaped algorithm...")

    # Use the real test funscript
    test_file = Path(__file__).parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load and process like the real algorithm
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript: {len(original_funscript.y)} actions")
        print(f"Original y range: {min(original_funscript.y):.3f} to {max(original_funscript.y):.3f}")
        print(f"First 20 y values: {original_funscript.y[:20]}")

        # Apply inversion like the prostate algorithm does
        working_funscript = invert_funscript(original_funscript)
        print(f"\nInverted funscript:")
        print(f"Inverted y range: {min(working_funscript.y):.3f} to {max(working_funscript.y):.3f}")
        print(f"First 20 y values: {working_funscript.y[:20]}")

        # Create interpolated timeline (simplified)
        start_time = working_funscript.x[0]
        end_time = working_funscript.x[-1]
        duration = end_time - start_time
        points_per_second = 10
        num_points = int(duration * points_per_second)
        num_points = min(num_points, 100)  # Limit for debugging

        new_times = np.linspace(start_time, end_time, num_points)
        interpolated_positions = np.interp(new_times, working_funscript.x, working_funscript.y)

        print(f"\nInterpolated positions ({num_points} points):")
        print(f"Range: {min(interpolated_positions):.3f} to {max(interpolated_positions):.3f}")
        print(f"First 20 values: {interpolated_positions[:20]}")

        # Find extrema
        extrema = _find_local_extrema(interpolated_positions)
        print(f"\nFound {len(extrema)} extrema:")
        for i, ext in enumerate(extrema[:10]):  # Show first 10
            print(f"  {i}: index={ext['index']}, value={ext['value']:.3f}, type={ext['type']}")

        # Test tear-shaped conversion
        alpha_values, beta_values = _convert_tear_shaped(interpolated_positions, 0.5)
        print(f"\nTear-shaped conversion results:")
        print(f"Alpha range: {min(alpha_values):.3f} to {max(alpha_values):.3f}")
        print(f"Beta range: {min(beta_values):.3f} to {max(beta_values):.3f}")
        print(f"First 20 alpha values: {alpha_values[:20]}")
        print(f"First 20 beta values: {beta_values[:20]}")

        # Check for variation
        alpha_unique = len(set(np.round(alpha_values, 3)))
        beta_unique = len(set(np.round(beta_values, 3)))
        print(f"\nVariation check:")
        print(f"Unique alpha values (rounded): {alpha_unique}")
        print(f"Unique beta values (rounded): {beta_unique}")

    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tear_shaped()