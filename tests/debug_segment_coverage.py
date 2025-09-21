#!/usr/bin/env python3
"""
Debug segment coverage to see why some points get linear mapping.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))

from funscript import Funscript
from processing.funscript_prostate_2d import _find_local_extrema
from processing.basic_transforms import invert_funscript

def debug_segment_coverage():
    """Debug which points are covered by segments vs linear mapping."""
    print("Debugging segment coverage...")

    # Use the real test funscript
    test_file = Path(__file__).parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load and process like the real algorithm
        original_funscript = Funscript.from_file(test_file)
        working_funscript = invert_funscript(original_funscript)

        # Create small interpolated sample
        start_time = working_funscript.x[0]
        end_time = working_funscript.x[-1]
        duration = end_time - start_time
        points_per_second = 10
        num_points = int(duration * points_per_second)
        num_points = min(num_points, 100)

        new_times = np.linspace(start_time, end_time, num_points)
        interpolated_positions = np.interp(new_times, working_funscript.x, working_funscript.y)

        print(f"Analyzing {num_points} points")

        # Find extrema
        extrema = _find_local_extrema(interpolated_positions)
        print(f"Found {len(extrema)} extrema")

        # Group extrema into segments (same logic as algorithm)
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
                i += 1
                continue

            segments.append({
                'start_index': current_extremum['index'],
                'end_index': next_extremum['index'],
                'local_max': local_max,
                'local_min': local_min
            })
            i += 2

        print(f"Created {len(segments)} segments:")
        for idx, seg in enumerate(segments):
            print(f"  Segment {idx}: indices {seg['start_index']} to {seg['end_index']}")

        # Check coverage for each point
        segment_points = 0
        linear_points = 0

        print(f"\nPoint analysis (first 30 points):")
        for i in range(min(30, num_points)):
            # Find which segment this point belongs to
            current_segment = None
            for segment in segments:
                if segment['start_index'] <= i <= segment['end_index']:
                    current_segment = segment
                    break

            if current_segment is None:
                linear_points += 1
                print(f"  Point {i}: LINEAR mapping (pos={interpolated_positions[i]:.3f})")
            else:
                segment_points += 1
                seg_idx = segments.index(current_segment)
                print(f"  Point {i}: SEGMENT {seg_idx} (pos={interpolated_positions[i]:.3f})")

        print(f"\nSummary:")
        print(f"  Points in segments: {segment_points}")
        print(f"  Points with linear mapping: {linear_points}")
        print(f"  Total points: {num_points}")

        # Check for gaps
        covered_indices = set()
        for segment in segments:
            for i in range(segment['start_index'], segment['end_index'] + 1):
                covered_indices.add(i)

        uncovered_indices = set(range(num_points)) - covered_indices
        print(f"  Uncovered indices: {sorted(uncovered_indices)}")

    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_segment_coverage()