#!/usr/bin/env python3
"""
Build helper script for local testing and development
"""

import sys
import platform
import subprocess
from pathlib import Path

def main():
    """Main build dispatcher."""
    system = platform.system().lower()

    print(f"Detected system: {system}")
    print("Available build options:")
    print("  1. Windows executable (.exe)")
    print("  2. Linux AppImage")
    print("  3. Both (if supported)")
    print("  4. Test dependencies only")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect build option (1-4): ").strip()

    if choice == "1" or choice.lower() == "windows":
        print("\nBuilding Windows executable...")
        result = subprocess.run([sys.executable, "build_windows.py"])
        sys.exit(result.returncode)

    elif choice == "2" or choice.lower() == "linux":
        print("\nBuilding Linux AppImage...")
        result = subprocess.run([sys.executable, "build_linux.py"])
        sys.exit(result.returncode)

    elif choice == "3" or choice.lower() == "both":
        print("\nBuilding both Windows and Linux...")

        # Build Windows
        print("Step 1/2: Building Windows executable...")
        result = subprocess.run([sys.executable, "build_windows.py"])
        if result.returncode != 0:
            print("Windows build failed!")
            sys.exit(1)

        # Build Linux
        print("Step 2/2: Building Linux AppImage...")
        result = subprocess.run([sys.executable, "build_linux.py"])
        if result.returncode != 0:
            print("Linux build failed!")
            sys.exit(1)

        print("Both builds completed successfully!")

    elif choice == "4" or choice.lower() == "test":
        print("\nTesting dependencies...")
        test_dependencies()

    else:
        print("Invalid choice!")
        sys.exit(1)

def test_dependencies():
    """Test that all required dependencies are available."""
    print("Checking Python dependencies...")

    required_modules = [
        "numpy",
        "tkinter",
        "json",
        "pathlib",
        "pyinstaller"
    ]

    missing = []

    for module in required_modules:
        try:
            if module == "tkinter":
                import tkinter
            elif module == "numpy":
                import numpy
            elif module == "json":
                import json
            elif module == "pathlib":
                import pathlib
            elif module == "pyinstaller":
                import PyInstaller
            print(f"  [OK] {module}")
        except ImportError:
            print(f"  [MISSING] {module}")
            missing.append(module)

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All dependencies available!")

        # Test that the main application can import
        try:
            print("Testing main application import...")
            import main
            print("  [SUCCESS] Main application imports successfully")
        except Exception as e:
            print(f"  [FAILED] Main application import failed: {e}")
            sys.exit(1)

        print("\n[SUCCESS] Ready to build!")

if __name__ == "__main__":
    main()