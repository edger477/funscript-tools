#!/usr/bin/env python3
"""
Test the fixed volume ramp calculation.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from funscript import Funscript
from processing.special_generators import make_volume_ramp

def test_fixed_ramp_calculation():
    """Test the fixed volume ramp calculation with various file durations."""

    # Test cases: (duration_minutes, expected_behavior)
    test_cases = [
        (8, "8-minute file"),
        (30, "30-minute file"),
        (60, "1-hour file"),
        (5, "5-minute file"),
    ]

    ramp_percent_per_hour = 15

    print(f"Testing Fixed Volume Ramp Calculation (${ramp_percent_per_hour}% per hour)\n")

    for duration_minutes, description in test_cases:
        print(f"=== {description} ===")

        # Create mock funscript with appropriate timing
        duration_seconds = duration_minutes * 60
        x = [0, 10, duration_seconds - 1, duration_seconds]  # start, 10s, near-end, end
        y = [50, 60, 70, 80]  # dummy values

        mock_funscript = Funscript(x, y)

        # Generate volume ramp
        ramp = make_volume_ramp(mock_funscript, ramp_percent_per_hour)

        # Calculate expected values
        file_duration_hours = duration_seconds / 3600.0
        total_ramp_increase = (ramp_percent_per_hour / 100.0) * file_duration_hours
        expected_start = max(0.0, 1.0 - total_ramp_increase)

        print(f"  File duration: {duration_minutes} min ({file_duration_hours:.3f} hours)")
        print(f"  Total ramp increase: {total_ramp_increase:.3f} ({total_ramp_increase*100:.1f}%)")
        print(f"  Expected start value: {expected_start:.3f} ({expected_start*100:.1f}%)")
        print(f"  Actual ramp values: {[f'{y:.3f}' for y in ramp.y]}")
        print(f"  Start: {ramp.y[0]*100:.1f}%, 10s: {ramp.y[1]*100:.1f}%, Peak: {ramp.y[2]*100:.1f}%, End: {ramp.y[3]*100:.1f}%")
        print()

def test_combination_effect():
    """Test how the fixed ramp combines with speed."""
    print("=== Testing Combination Effect ===")

    # Mock 8-minute file
    duration_seconds = 8 * 60
    x = [0, 10, duration_seconds - 1, duration_seconds]
    y = [50, 60, 70, 80]
    mock_funscript = Funscript(x, y)

    # Generate ramp
    ramp = make_volume_ramp(mock_funscript, 15)

    # Mock speed (assume constant 50% for simplicity)
    speed_value = 0.5
    ramp_value = ramp.y[1]  # Value at 10 seconds

    # Simulate combination (ratio = 6.0, rest_level = 0.5)
    ratio = 6.0
    combined_value = (ramp_value * (ratio - 1) + speed_value) / ratio

    print(f"  Ramp at 10s: {ramp_value*100:.1f}%")
    print(f"  Speed: {speed_value*100:.1f}%")
    print(f"  Combined (ratio {ratio}): {combined_value*100:.1f}%")
    print(f"  Ramp weight: {(ratio-1)/ratio*100:.1f}%, Speed weight: {1/ratio*100:.1f}%")

if __name__ == "__main__":
    test_fixed_ramp_calculation()
    test_combination_effect()