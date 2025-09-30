#!/usr/bin/env python3
"""
Build script for creating Windows executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from version import __version__, __app_name__

def build_windows_exe():
    """Build Windows executable using PyInstaller."""
    print(f"Building {__app_name__} v{__version__} for Windows...")

    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")

    if dist_dir.exists():
        print("Cleaning previous dist folder...")
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        print("Cleaning previous build folder...")
        shutil.rmtree(build_dir)

    # Try spec file first, then fallback to command line
    spec_file = Path("funscript_processor.spec")
    use_spec_file = spec_file.exists()

    if use_spec_file:
        print("Using spec file for build...")
        cmd = [
            "pyinstaller",
            "--clean",  # Clean PyInstaller cache
            "--distpath", "dist/windows",
            str(spec_file)
        ]
    else:
        print("Using command line arguments for build...")
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--onefile",  # Single executable file
            "--windowed",  # No console window (GUI app)
            "--name", f"RestimFunscriptProcessor-v{__version__}",
            "--paths", ".",  # Add current directory to Python path
            "--collect-all", "ui",  # Collect entire ui package
            "--collect-all", "processing",  # Collect entire processing package
            "--hidden-import", "tkinter",
            "--hidden-import", "numpy",
            "--hidden-import", "json",
            "--hidden-import", "pathlib",
            "--hidden-import", "processing.linear_mapping",  # New motion axis module
            "--hidden-import", "processing.motion_axis_generation",  # New motion axis module
            "--clean",  # Clean PyInstaller cache
            "--distpath", "dist/windows",
            "main.py"
        ]

    # Add config file if it exists
    if Path("restim_config.json").exists():
        cmd.insert(-1, "--add-data")
        cmd.insert(-1, "restim_config.json;.")

    # Add icon if it exists
    if Path("assets/icon.ico").exists():
        cmd.insert(-1, "--icon")
        cmd.insert(-1, "assets/icon.ico")

    print("Running PyInstaller...")
    print(" ".join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")

        # Show output files
        windows_dist = Path("dist/windows")
        if windows_dist.exists():
            exe_files = list(windows_dist.glob("*.exe"))
            if exe_files:
                exe_file = exe_files[0]
                file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
                print(f"Created: {exe_file}")
                print(f"Size: {file_size:.1f} MB")
                return str(exe_file)
            else:
                print("Warning: No .exe files found in dist folder")

    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return None

    except FileNotFoundError:
        print("Error: PyInstaller not found. Install with: pip install pyinstaller")
        return None

def create_release_package():
    """Create a release package with the executable and documentation."""
    print("Creating release package...")

    release_dir = Path(f"dist/RestimFunscriptProcessor-v{__version__}-Windows")
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy executable
    windows_dist = Path("dist/windows")
    exe_files = list(windows_dist.glob("*.exe"))
    if exe_files:
        exe_file = exe_files[0]
        target_exe = release_dir / f"RestimFunscriptProcessor.exe"
        shutil.copy2(exe_file, target_exe)
        print(f"Copied executable to: {target_exe}")

    # Copy documentation
    docs_to_copy = [
        "README.md",
        "PYTHON_GUI_APPLICATION_SPECIFICATION.md",
        "RESTIM_FUNSCRIPT_PROCESSING_REQUIREMENTS.md"
    ]

    for doc in docs_to_copy:
        if Path(doc).exists():
            shutil.copy2(doc, release_dir / doc)
            print(f"Copied: {doc}")

    # Create a simple install guide
    install_guide = release_dir / "INSTALLATION.txt"
    with open(install_guide, 'w') as f:
        f.write(f"""Restim Funscript Processor v{__version__} - Windows Installation

QUICK START:
1. Extract this folder to any location (e.g., Desktop or Program Files)
2. Double-click "RestimFunscriptProcessor.exe" to run the application
3. No Python installation required!

USAGE:
- Select your .funscript file using the Browse button
- Configure parameters in the tabs
- Click "Process Files" to generate output files
- Output files will be created in the same folder as your input file

DOCUMENTATION:
- README.md - Complete user guide and features
- PYTHON_GUI_APPLICATION_SPECIFICATION.md - Technical specification
- RESTIM_FUNSCRIPT_PROCESSING_REQUIREMENTS.md - Processing details

SUPPORT:
- Report issues at: https://github.com/your-username/funscript-tools/issues
- Documentation: See included README.md

VERSION: {__version__}
""")

    print(f"Created installation guide: {install_guide}")

    # Create ZIP archive
    archive_name = f"RestimFunscriptProcessor-v{__version__}-Windows"
    print(f"Creating ZIP archive: {archive_name}.zip")

    shutil.make_archive(
        f"dist/{archive_name}",
        'zip',
        release_dir.parent,
        release_dir.name
    )

    archive_path = Path(f"dist/{archive_name}.zip")
    if archive_path.exists():
        archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
        print(f"Release package created: {archive_path}")
        print(f"Archive size: {archive_size:.1f} MB")
        return str(archive_path)

    return None

def main():
    """Main build process."""
    print("=" * 60)
    print(f"Building {__app_name__} v{__version__} for Windows")
    print("=" * 60)

    # Check if we're on Windows (for warnings)
    if sys.platform != "win32":
        print("Warning: Building Windows executable on non-Windows platform")
        print("Cross-compilation may have issues. Consider using GitHub Actions.")

    # Build executable
    exe_path = build_windows_exe()
    if not exe_path:
        print("Build failed!")
        return False

    # Create release package
    archive_path = create_release_package()
    if archive_path:
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print(f"Release package: {archive_path}")
        print("Ready for distribution!")
        print("=" * 60)
        return True
    else:
        print("Failed to create release package")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)