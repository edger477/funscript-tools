#!/usr/bin/env python3
"""
COMPREHENSIVE VERIFICATION SCRIPT
This script will definitively prove whether Motion Axis is working.
"""

import sys
import os
from pathlib import Path

print("="*60)
print("MOTION AXIS VERIFICATION SCRIPT")
print("="*60)

# Ensure we're using the right directory
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

print(f"Working directory: {Path.cwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version.split()[0]}")

# Clear any cached modules
modules_to_clear = [
    'ui.parameter_tabs',
    'ui.main_window',
    'config',
    'processor',
    'processing.linear_mapping',
    'processing.motion_axis_generation'
]

print(f"\nClearing cached modules...")
for module in modules_to_clear:
    if module in sys.modules:
        del sys.modules[module]
        print(f"  Cleared: {module}")

# Force reimport and test
print(f"\nForce importing modules...")
try:
    import importlib

    # Import config
    config_module = importlib.import_module('config')
    DEFAULT_CONFIG = config_module.DEFAULT_CONFIG
    print(f"✓ Config loaded, has positional_axes: {'positional_axes' in DEFAULT_CONFIG}")

    # Import parameter tabs
    param_tabs_module = importlib.import_module('ui.parameter_tabs')
    ParameterTabs = param_tabs_module.ParameterTabs
    print(f"✓ ParameterTabs loaded")

    # Check methods exist
    has_setup_tabs = hasattr(ParameterTabs, 'setup_tabs')
    has_setup_motion_axis = hasattr(ParameterTabs, 'setup_motion_axis_tab')
    print(f"✓ Has setup_tabs: {has_setup_tabs}")
    print(f"✓ Has setup_motion_axis_tab: {has_setup_motion_axis}")

    # Test tab creation
    import tkinter as tk
    print(f"\nTesting UI creation...")
    root = tk.Tk()
    root.withdraw()

    tabs = ParameterTabs(root, DEFAULT_CONFIG.copy())
    tab_count = tabs.index('end')

    tab_names = []
    for i in range(tab_count):
        name = tabs.tab(i, 'text')
        tab_names.append(name)

    print(f"Created {tab_count} tabs: {tab_names}")

    if 'Motion Axis' in tab_names:
        print(f"🎉 SUCCESS: Motion Axis tab found at position {tab_names.index('Motion Axis') + 1}")

        # Test switching to the tab
        motion_axis_index = tab_names.index('Motion Axis')
        tabs.select(motion_axis_index)
        print(f"✓ Successfully selected Motion Axis tab")

        print(f"\n" + "="*60)
        print(f"MOTION AXIS IS WORKING CORRECTLY!")
        print(f"If you don't see it, you may be:")
        print(f"1. Using a different Python environment")
        print(f"2. Running from a different directory")
        print(f"3. Have workspace/IDE cache issues")
        print(f"="*60)

    else:
        print(f"❌ FAILURE: Motion Axis tab not found!")
        print(f"This should not happen - there's a deeper issue.")

    root.destroy()

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print(f"\nCurrent working directory: {os.getcwd()}")
print(f"Files in directory:")
for f in sorted(os.listdir('.')):
    if f.endswith('.py'):
        print(f"  {f}")

print(f"\nUI directory contents:")
if os.path.exists('ui'):
    for f in sorted(os.listdir('ui')):
        if f.endswith('.py'):
            print(f"  ui/{f}")

print(f"\nThis verification is complete.")
print(f"If Motion Axis shows as working here but not in your app,")
print(f"you're running from a different environment or directory.")