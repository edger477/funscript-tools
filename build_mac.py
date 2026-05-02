#!/usr/bin/env python3
"""
Build script for creating macOS application bundle using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from version import __version__, __app_name__

APP_NAME = "RestimFunscriptProcessor"


def build_mac_app():
    """Build macOS .app bundle using PyInstaller."""
    print(f"Building {__app_name__} v{__version__} for macOS...")

    for d in (Path("dist"), Path("build")):
        if d.exists():
            print(f"Cleaning {d}/")
            shutil.rmtree(d)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--windowed",
        "--name", APP_NAME,
        "--paths", ".",
        "--collect-all", "ui",
        "--collect-all", "processing",
        "--collect-all", "tkinterdnd2",
        "--hidden-import", "tkinter",
        "--hidden-import", "numpy",
        "--hidden-import", "matplotlib",
        "--hidden-import", "matplotlib.pyplot",
        "--hidden-import", "matplotlib.backends.backend_tkagg",
        "--hidden-import", "matplotlib.figure",
        "--hidden-import", "matplotlib.patches",
        "--hidden-import", "json",
        "--hidden-import", "pathlib",
        "--hidden-import", "processing.linear_mapping",
        "--hidden-import", "processing.motion_axis_generation",
        "--clean",
        "--distpath", "dist",
        "main.py"
    ]

    if Path("config.event_definitions.yml").exists():
        cmd += ["--add-data", "config.event_definitions.yml:."]

    print("Running PyInstaller...")
    print(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        app_path = Path("dist") / f"{APP_NAME}.app"
        if app_path.exists():
            size_mb = sum(f.stat().st_size for f in app_path.rglob("*") if f.is_file()) / (1024 * 1024)
            print(f"Created: {app_path} ({size_mb:.1f} MB)")
            return str(app_path)
        print("ERROR: .app bundle not found after build")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return None


def create_dmg(app_path):
    """Package .app into a .dmg installer using hdiutil."""
    print("Creating DMG...")

    app = Path(app_path)
    dmg_name = f"{APP_NAME}-v{__version__}-macOS"
    staging = Path(f"dist/{dmg_name}-staging")
    dmg_path = Path(f"dist/{dmg_name}.dmg")

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    shutil.copytree(app, staging / app.name)
    (staging / "Applications").symlink_to("/Applications")

    cmd = [
        "hdiutil", "create",
        "-volname", APP_NAME,
        "-srcfolder", str(staging),
        "-ov",
        "-format", "UDZO",
        str(dmg_path),
    ]

    try:
        subprocess.run(cmd, check=True)
        shutil.rmtree(staging)
        size_mb = dmg_path.stat().st_size / (1024 * 1024)
        print(f"Created DMG: {dmg_path} ({size_mb:.1f} MB)")
        return str(dmg_path)
    except subprocess.CalledProcessError as e:
        print(f"DMG creation failed: {e}")
        return None


def main():
    if sys.platform != "darwin":
        print("Warning: This script is intended for macOS")

    app_path = build_mac_app()
    if not app_path:
        print("Build failed!")
        sys.exit(1)

    dmg_path = create_dmg(app_path)
    if not dmg_path:
        print("DMG creation failed!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BUILD SUCCESSFUL!")
    print(f"DMG: {dmg_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
