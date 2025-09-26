#!/usr/bin/env python3
"""
Test script to verify volume ramp calculation precision.
"""

def test_ramp_calculation(duration_minutes, ramp_percent_per_hour=15):
    """Test the volume ramp calculation with exact precision."""
    print(f"Testing {duration_minutes}-minute file with {ramp_percent_per_hour}% per hour:")

    # Convert to seconds
    duration_seconds = duration_minutes * 60

    # Simulate the algorithm from special_generators.py
    ramp_per_second = ramp_percent_per_hour / 3600.0
    print(f"  ramp_per_second = {ramp_percent_per_hour} / 3600 = {ramp_per_second}")
    print(f"  ramp_per_second (precise) = {repr(ramp_per_second)}")

    # Calculate duration from second point (10s) to peak (end-1)
    # For testing, assume peak is at duration_seconds - 1
    second_time = 10.0
    peak_time = duration_seconds - 1  # second-to-last point

    duration_calc = peak_time - second_time
    print(f"  duration from 10s to peak: {duration_calc} seconds")

    # Calculate ramp value at second point
    ramp_value_raw = 1.0 - (duration_calc * ramp_per_second)
    print(f"  ramp_value_raw = 1.0 - ({duration_calc} * {ramp_per_second}) = {ramp_value_raw}")
    print(f"  ramp_value_raw (precise) = {repr(ramp_value_raw)}")

    # Clamp the ramp value
    ramp_value = max(0.0, min(1.0, ramp_value_raw))
    print(f"  ramp_value (clamped) = {ramp_value}")

    # Convert to percentage
    ramp_percentage = ramp_value * 100
    print(f"  ramp at 10 seconds = {ramp_percentage:.2f}%")

    return ramp_value

if __name__ == "__main__":
    print("Volume Ramp Calculation Test\n")

    # Test cases
    test_cases = [
        (8, 15),   # 8-minute file, 15% per hour
        (60, 15),  # 1-hour file, 15% per hour
        (30, 15),  # 30-minute file, 15% per hour
        (5, 15),   # 5-minute file, 15% per hour
    ]

    for duration_min, ramp_pct in test_cases:
        test_ramp_calculation(duration_min, ramp_pct)
        print()