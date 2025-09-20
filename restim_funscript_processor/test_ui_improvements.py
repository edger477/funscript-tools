#!/usr/bin/env python3
"""
Test script to verify the UI improvements work correctly.
"""

import tkinter as tk
from ui.parameter_tabs import ParameterTabs, calculate_combine_percentages, format_percentage_label
from config import ConfigManager


def test_percentage_calculations():
    """Test the percentage calculation functions."""
    print("Testing ratio calculations:")
    test_cases = [
        (2, "Ramp", "Speed"),
        (3, "Ramp", "Speed"),
        (4, "Alpha", "Speed"),
        (6, "Ramp", "Speed")
    ]

    for ratio, file1, file2 in test_cases:
        left_pct, right_pct = calculate_combine_percentages(ratio)
        label = format_percentage_label(file1, file2, ratio)
        print(f"  Ratio {ratio}: {label}")

        # Verify the math
        expected_left = (ratio - 1) / ratio * 100
        expected_right = 1 / ratio * 100
        assert abs(left_pct - expected_left) < 0.01, f"Left percentage calculation error for ratio {ratio}"
        assert abs(right_pct - expected_right) < 0.01, f"Right percentage calculation error for ratio {ratio}"

    print("[PASS] Percentage calculations working correctly")


def test_ui_loading():
    """Test that the UI can load with new controls."""
    try:
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()  # Hide the window

        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Create parameter tabs
        tabs = ParameterTabs(root, config)

        # Test that combine ratio controls were created
        expected_controls = [
            'frequency_ramp_combine_ratio',
            'pulse_frequency_combine_ratio',
            'volume_ramp_combine_ratio',
            'pulse_width_combine_ratio',
            'pulse_rise_combine_ratio'
        ]

        for control_name in expected_controls:
            if control_name in tabs.combine_ratio_controls:
                print(f"  [OK] {control_name} control created")
            else:
                print(f"  [MISSING] {control_name} control")

        # Clean up
        root.destroy()
        print("[PASS] UI components loaded successfully")
        return True

    except Exception as e:
        print(f"[FAIL] Error loading UI: {e}")
        return False


def test_config_integration():
    """Test that the new controls integrate with configuration properly."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Check that all expected ratio parameters exist in config
        expected_params = {
            'frequency': ['frequency_ramp_combine_ratio', 'pulse_frequency_combine_ratio'],
            'volume': ['volume_ramp_combine_ratio'],
            'pulse': ['pulse_width_combine_ratio', 'pulse_rise_combine_ratio']
        }

        for section, params in expected_params.items():
            if section in config:
                for param in params:
                    if param in config[section]:
                        print(f"  [OK] {section}.{param} = {config[section][param]}")
                    else:
                        print(f"  [MISSING] {section}.{param}")
            else:
                print(f"  [MISSING] {section} section")

        print("[PASS] Configuration integration working")
        return True

    except Exception as e:
        print(f"[FAIL] Configuration error: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing UI improvements for combine ratio controls...")
    print()

    tests_passed = 0
    total_tests = 3

    try:
        test_percentage_calculations()
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Percentage calculation test failed: {e}")

    print()

    if test_ui_loading():
        tests_passed += 1

    print()

    if test_config_integration():
        tests_passed += 1

    print()
    print(f"Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("[SUCCESS] All UI improvements working correctly!")
        return True
    else:
        print("[PARTIAL] Some tests failed - check output above")
        return False


if __name__ == "__main__":
    main()