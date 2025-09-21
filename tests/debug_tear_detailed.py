#!/usr/bin/env python3
"""
Detailed debug of the tear-shaped algorithm to see circle radii and segments.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))

from funscript import Funscript
from processing.funscript_prostate_2d import _find_local_extrema
from processing.basic_transforms import invert_funscript

def debug_tear_detailed():
    """Debug the tear-shaped algorithm with detailed output."""
    print("Detailed debugging of tear-shaped algorithm...")

    # Use the real test funscript
    test_file = Path(__file__).parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load and process like the real algorithm
        original_funscript = Funscript.from_file(test_file)
        working_funscript = invert_funscript(original_funscript)

        # Create smaller interpolated sample for analysis
        start_time = working_funscript.x[0]
        end_time = working_funscript.x[-1]
        duration = end_time - start_time
        points_per_second = 5  # Small sample
        num_points = int(duration * points_per_second)
        num_points = min(num_points, 50)  # Limit for debugging

        new_times = np.linspace(start_time, end_time, num_points)
        interpolated_positions = np.interp(new_times, working_funscript.x, working_funscript.y)

        print(f"Interpolated {num_points} points from {duration:.0f}ms duration")
        print(f"Position range: {min(interpolated_positions):.3f} to {max(interpolated_positions):.3f}")

        # Find extrema
        extrema = _find_local_extrema(interpolated_positions)
        print(f"\nFound {len(extrema)} extrema:")
        for i, ext in enumerate(extrema):
            print(f"  {i}: index={ext['index']}, value={ext['value']:.3f}, type={ext['type']}")

        # Group extrema into min/max pairs like the algorithm does
        segments = []
        min_distance_from_center = 0.5
        i = 0
        while i < len(extrema) - 1:
            current_extremum = extrema[i]
            next_extremum = extrema[i + 1]

            # Determine which is max and which is min
            if current_extremum['type'] == 'max' and next_extremum['type'] == 'min':
                local_max = current_extremum
                local_min = next_extremum
            elif current_extremum['type'] == 'min' and next_extremum['type'] == 'max':
                local_max = next_extremum
                local_min = current_extremum
            else:
                # Skip if we don't have a proper min/max pair
                i += 1
                continue

            # Calculate center and radius
            center_value = (local_max['value'] + local_min['value']) / 2.0
            center_alpha = (0.5 - min_distance_from_center) + center_value * (0.5 + min_distance_from_center)

            # Calculate circle radius based on local range: radius = (max - min) / 2
            local_range = local_max['value'] - local_min['value']
            circle_radius = local_range / 2.0
            circle_radius = min(circle_radius, 0.5)

            segments.append({
                'start_index': current_extremum['index'],
                'end_index': next_extremum['index'],
                'center_alpha': center_alpha,
                'center_value': center_value,
                'local_max': local_max,
                'local_min': local_min,
                'local_range': local_range,
                'circle_radius': circle_radius,
                'min_radius': min_distance_from_center * circle_radius
            })
            i += 2

        print(f"\nCreated {len(segments)} tear shape segments:")
        for i, seg in enumerate(segments):
            print(f"\nSegment {i}:")
            print(f"  Indices: {seg['start_index']} to {seg['end_index']}")
            print(f"  Local max: {seg['local_max']['value']:.3f} at index {seg['local_max']['index']}")
            print(f"  Local min: {seg['local_min']['value']:.3f} at index {seg['local_min']['index']}")
            print(f"  Local range: {seg['local_range']:.3f}")
            print(f"  Circle radius: {seg['circle_radius']:.3f}")
            print(f"  Min radius: {seg['min_radius']:.3f}")
            print(f"  Center alpha: {seg['center_alpha']:.3f}")
            print(f"  Center value: {seg['center_value']:.3f}")

    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tear_detailed()