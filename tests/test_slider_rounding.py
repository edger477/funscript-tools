#!/usr/bin/env python3
"""
Test script to verify slider rounding works correctly.
"""

import tkinter as tk
from ui.parameter_tabs import CombineRatioControl


def test_slider_rounding():
    """Test that sliders round to one decimal place."""
    print("Testing slider rounding behavior...")

    # Create a test window
    root = tk.Tk()
    root.title("Slider Rounding Test")
    root.geometry("600x200")

    # Create a test control
    control = CombineRatioControl(
        root, "Test Ratio:",
        "File1", "File2",
        initial_value=2.0,
        min_val=1.0, max_val=10.0, row=0
    )

    # Test various values
    test_values = [2.95, 3.14159, 6.666666, 1.12345, 9.87654]

    print("\nTesting value rounding:")
    for test_val in test_values:
        control.var.set(test_val)
        control._on_change()  # Trigger rounding
        result = control.var.get()
        expected = round(test_val, 1)
        print(f"  Input: {test_val:.6f} -> Output: {result} (Expected: {expected})")

        if abs(result - expected) < 0.01:
            print(f"    [PASS] Correctly rounded")
        else:
            print(f"    [FAIL] Rounding error")

    print("\nSlider value test:")
    print(f"  Current value: {control.var.get()}")
    print(f"  Value type: {type(control.var.get())}")

    # Add a button to close
    close_button = tk.Button(root, text="Close Test", command=root.destroy)
    close_button.grid(row=1, column=0, pady=20)

    # Display instructions
    instructions = tk.Label(root, text="Move the slider and observe that values stay at one decimal place.\nCheck the console output for rounding test results.")
    instructions.grid(row=2, column=0, columnspan=4, pady=10)

    print("\n[INFO] Test window opened. Move the slider to test rounding behavior.")
    print("       Close the window when done testing.")

    # Don't run mainloop in automated testing
    if __name__ == "__main__":
        root.mainloop()
    else:
        root.destroy()

    return True


if __name__ == "__main__":
    test_slider_rounding()