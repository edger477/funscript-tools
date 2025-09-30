#!/usr/bin/env python3
"""
Debug script to verify the actual application state.
This runs the real application and checks what tabs exist.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import tkinter as tk
from ui.main_window import MainWindow

def debug_application():
    print("=== DEBUGGING REAL APPLICATION ===")
    print(f"Python: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")
    print(f"Script location: {Path(__file__).parent}")

    # Create the real application
    print("\nCreating MainWindow...")
    main_window = MainWindow()

    # Check parameter tabs
    print("\nChecking parameter tabs...")
    tabs = main_window.parameter_tabs
    tab_count = tabs.index('end')
    print(f"Total tabs: {tab_count}")

    tab_names = []
    for i in range(tab_count):
        tab_name = tabs.tab(i, 'text')
        tab_names.append(tab_name)
        print(f"  Tab {i+1}: {tab_name}")

    # Check if Motion Axis exists
    motion_axis_exists = "Motion Axis" in tab_names
    print(f"\nMotion Axis tab exists: {motion_axis_exists}")

    if motion_axis_exists:
        # Switch to Motion Axis tab
        for i in range(tab_count):
            if tabs.tab(i, 'text') == "Motion Axis":
                tabs.select(i)
                print(f"Switched to Motion Axis tab (index {i})")
                break

        print("\n[SUCCESS] Motion Axis tab is working!")
        print("You should see the Motion Axis tab selected with:")
        print("- Mode selection (Legacy vs Motion Axis)")
        print("- E1, E2, E3, E4 axis controls")
        print("- Amplitude sliders")
    else:
        print("\n[FAILURE] Motion Axis tab not found!")
        print("This indicates a serious integration issue.")

    # Check configuration
    config = main_window.current_config
    has_positional_axes = 'positional_axes' in config
    print(f"\nConfig has positional_axes: {has_positional_axes}")

    if has_positional_axes:
        mode = config['positional_axes'].get('mode', 'unknown')
        print(f"Current mode: {mode}")

    print("\n=== APPLICATION IS NOW RUNNING ===")
    print("Check the window to see if Motion Axis tab is visible.")
    print("Close the window when done testing.")

    # Run the application
    main_window.run()

if __name__ == "__main__":
    debug_application()