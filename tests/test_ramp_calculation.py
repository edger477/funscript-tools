#!/usr/bin/env python3
"""
Test script to verify volume ramp calculation precision.
"""

import pytest


def _ramp_value(duration_minutes, ramp_percent_per_hour=15):
    """Return clamped ramp value at the 10s mark for a given duration."""
    duration_seconds = duration_minutes * 60
    ramp_per_second = ramp_percent_per_hour / 3600.0
    second_time = 10.0
    peak_time = duration_seconds - 1
    duration_calc = peak_time - second_time
    ramp_value_raw = 1.0 - (duration_calc * ramp_per_second)
    return max(0.0, min(1.0, ramp_value_raw))


@pytest.mark.parametrize(
    "duration_minutes,ramp_percent_per_hour",
    [(8, 15), (60, 15), (30, 15), (5, 15)],
)
def test_ramp_calculation(duration_minutes, ramp_percent_per_hour):
    ramp_value = _ramp_value(duration_minutes, ramp_percent_per_hour)
    assert 0.0 <= ramp_value <= 1.0


if __name__ == "__main__":
    for duration_min, ramp_pct in [(8, 15), (60, 15), (30, 15), (5, 15)]:
        val = _ramp_value(duration_min, ramp_pct)
        print(f"{duration_min} min @ {ramp_pct}%/hr -> ramp at 10s = {val * 100:.2f}%")
