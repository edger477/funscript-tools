#!/usr/bin/env python3
"""
Build script for creating Linux AppImage using PyInstaller
"""

import os
import sys
import subprocess
import shutil
import urllib.request
from pathlib import Path
from version import __version__, __app_name__

def download_appimagetool():
    """Download appimagetool if not present."""
    appimagetool_path = Path("appimagetool-x86_64.AppImage")

    if appimagetool_path.exists():
        print("appimagetool already exists")
        return str(appimagetool_path)

    print("Downloading appimagetool...")
    url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

    try:
        urllib.request.urlretrieve(url, appimagetool_path)
        os.chmod(appimagetool_path, 0o755)  # Make executable
        print(f"Downloaded: {appimagetool_path}")
        return str(appimagetool_path)
    except Exception as e:
        print(f"Failed to download appimagetool: {e}")
        return None

def build_linux_binary():
    """Build Linux binary using PyInstaller."""
    print(f"Building {__app_name__} v{__version__} for Linux...")

    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")

    if dist_dir.exists():
        print("Cleaning previous dist folder...")
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        print("Cleaning previous build folder...")
        shutil.rmtree(build_dir)

    # PyInstaller command for Linux
    cmd = [
        "pyinstaller",
        "--onedir",  # Directory bundle for AppImage
        "--name", "RestimFunscriptProcessor",
        "--paths", ".",  # Add current directory to Python path
        "--collect-all", "ui",  # Collect entire ui package
        "--collect-all", "processing",  # Collect entire processing package
        "--hidden-import", "tkinter",
        "--hidden-import", "numpy",
        "--hidden-import", "json",
        "--hidden-import", "pathlib",
        "--distpath", "dist/linux",
        "main.py"
    ]

    # Add config file if it exists
    if Path("restim_config.json").exists():
        cmd.insert(-1, "--add-data")
        cmd.insert(-1, "restim_config.json:.")

    print("Running PyInstaller...")
    print(" ".join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Binary build successful!")

        # Check output
        linux_dist = Path("dist/linux/RestimFunscriptProcessor")
        if linux_dist.exists():
            print(f"Created binary bundle: {linux_dist}")
            return str(linux_dist)
        else:
            print("Warning: Binary bundle not found")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return None

    except FileNotFoundError:
        print("Error: PyInstaller not found. Install with: pip install pyinstaller")
        return None

def create_appdir(binary_path):
    """Create AppDir structure for AppImage."""
    print("Creating AppDir structure...")

    appdir = Path(f"RestimFunscriptProcessor.AppDir")
    if appdir.exists():
        shutil.rmtree(appdir)

    appdir.mkdir()

    # Copy the binary bundle
    target_dir = appdir / "usr" / "bin"
    target_dir.mkdir(parents=True)

    binary_bundle = Path(binary_path)
    if binary_bundle.exists():
        shutil.copytree(binary_bundle, target_dir / "RestimFunscriptProcessor")
        print(f"Copied binary bundle to: {target_dir}")

    # Create desktop entry
    desktop_entry = appdir / "RestimFunscriptProcessor.desktop"
    with open(desktop_entry, 'w') as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name=Restim Funscript Processor
Comment=Process funscript files for electrostimulation devices
Exec=RestimFunscriptProcessor/RestimFunscriptProcessor
Icon=RestimFunscriptProcessor
Categories=AudioVideo;Audio;
Version={__version__}
""")

    # Create a simple icon (text-based for now)
    icon_path = appdir / "RestimFunscriptProcessor.png"
    # For now, we'll skip the icon or use a simple one
    # In a real setup, you'd include a proper PNG icon

    # Create AppRun script
    apprun = appdir / "AppRun"
    with open(apprun, 'w') as f:
        f.write(f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
exec "$HERE/usr/bin/RestimFunscriptProcessor/RestimFunscriptProcessor" "$@"
""")

    os.chmod(apprun, 0o755)  # Make executable

    print(f"Created AppDir: {appdir}")
    return str(appdir)

def create_appimage(appdir_path, appimagetool_path):
    """Create AppImage from AppDir."""
    print("Creating AppImage...")

    cmd = [appimagetool_path, appdir_path]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("AppImage creation successful!")

        # Find the created AppImage
        appimages = list(Path(".").glob("*.AppImage"))
        appimages = [ai for ai in appimages if "appimagetool" not in ai.name]

        if appimages:
            appimage = appimages[0]
            new_name = f"RestimFunscriptProcessor-v{__version__}-Linux-x86_64.AppImage"
            new_path = Path("dist") / new_name
            new_path.parent.mkdir(exist_ok=True)

            shutil.move(appimage, new_path)
            file_size = new_path.stat().st_size / (1024 * 1024)  # MB
            print(f"Created AppImage: {new_path}")
            print(f"Size: {file_size:.1f} MB")
            return str(new_path)

    except subprocess.CalledProcessError as e:
        print(f"AppImage creation failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return None

def create_release_package(appimage_path):
    """Create a release package with the AppImage and documentation."""
    print("Creating release package...")

    release_dir = Path(f"dist/RestimFunscriptProcessor-v{__version__}-Linux")
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy AppImage
    if appimage_path and Path(appimage_path).exists():
        target_appimage = release_dir / f"RestimFunscriptProcessor.AppImage"
        shutil.copy2(appimage_path, target_appimage)
        os.chmod(target_appimage, 0o755)  # Make executable
        print(f"Copied AppImage to: {target_appimage}")

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

    # Create Linux installation guide
    install_guide = release_dir / "INSTALLATION.txt"
    with open(install_guide, 'w') as f:
        f.write(f"""Restim Funscript Processor v{__version__} - Linux Installation

QUICK START:
1. Extract this folder to any location (e.g., ~/Applications or ~/Desktop)
2. Make the AppImage executable: chmod +x RestimFunscriptProcessor.AppImage
3. Double-click or run: ./RestimFunscriptProcessor.AppImage
4. No additional dependencies required!

ALTERNATIVE INSTALLATION:
- Move RestimFunscriptProcessor.AppImage to ~/.local/bin/ or /usr/local/bin/
- Run from terminal: RestimFunscriptProcessor.AppImage

USAGE:
- Select your .funscript file using the Browse button
- Configure parameters in the tabs
- Click "Process Files" to generate output files
- Output files will be created in the same folder as your input file

TROUBLESHOOTING:
- If you get permission errors, run: chmod +x RestimFunscriptProcessor.AppImage
- For FUSE issues on older systems, run with --appimage-extract-and-run
- Requires X11/Wayland display server (standard on most Linux desktops)

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

    # Create tar.gz archive
    archive_name = f"RestimFunscriptProcessor-v{__version__}-Linux"
    print(f"Creating tar.gz archive: {archive_name}.tar.gz")

    shutil.make_archive(
        f"dist/{archive_name}",
        'gztar',
        release_dir.parent,
        release_dir.name
    )

    archive_path = Path(f"dist/{archive_name}.tar.gz")
    if archive_path.exists():
        archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
        print(f"Release package created: {archive_path}")
        print(f"Archive size: {archive_size:.1f} MB")
        return str(archive_path)

    return None

def main():
    """Main build process."""
    print("=" * 60)
    print(f"Building {__app_name__} v{__version__} for Linux")
    print("=" * 60)

    # Check if we're on Linux (for warnings)
    if sys.platform != "linux":
        print("Warning: Building Linux AppImage on non-Linux platform")
        print("Cross-compilation may have issues. Consider using GitHub Actions.")

    # Download appimagetool
    appimagetool_path = download_appimagetool()
    if not appimagetool_path:
        print("Failed to get appimagetool!")
        return False

    # Build binary
    binary_path = build_linux_binary()
    if not binary_path:
        print("Binary build failed!")
        return False

    # Create AppDir
    appdir_path = create_appdir(binary_path)
    if not appdir_path:
        print("AppDir creation failed!")
        return False

    # Create AppImage
    appimage_path = create_appimage(appdir_path, appimagetool_path)
    if not appimage_path:
        print("AppImage creation failed!")
        return False

    # Create release package
    archive_path = create_release_package(appimage_path)
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