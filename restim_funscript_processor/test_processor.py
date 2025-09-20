#!/usr/bin/env python3
"""
Simple test script to verify the processor works correctly.
"""

import json
import tempfile
import os
from pathlib import Path
from config import ConfigManager
from processor import RestimProcessor


def create_test_funscript():
    """Create a simple test funscript file."""
    test_data = {
        "actions": [
            {"at": 0, "pos": 0},
            {"at": 1000, "pos": 50},
            {"at": 2000, "pos": 100},
            {"at": 3000, "pos": 25},
            {"at": 4000, "pos": 75},
            {"at": 5000, "pos": 0}
        ]
    }

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.funscript', delete=False)
    json.dump(test_data, temp_file)
    temp_file.close()

    return temp_file.name


def test_processor():
    """Test the processor with a simple funscript."""
    print("Creating test funscript...")
    test_file = create_test_funscript()

    try:
        print(f"Test file created: {test_file}")

        # Load default configuration
        print("Loading configuration...")
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Create processor
        print("Creating processor...")
        processor = RestimProcessor(config)

        # Process the file
        print("Starting processing...")

        def progress_callback(percent, message):
            print(f"Progress: {percent}% - {message}")

        success = processor.process(test_file, progress_callback)

        if success:
            print("\n[SUCCESS] Processing completed successfully!")

            # Check what files were created
            test_path = Path(test_file)
            parent_dir = test_path.parent
            filename_only = test_path.stem

            print("\nGenerated files:")
            expected_outputs = [
                "alpha", "alpha-prostate", "beta", "frequency",
                "pulse_frequency", "pulse_rise_time", "pulse_width",
                "volume", "volume-prostate", "volume-stereostim"
            ]

            generated_count = 0
            for suffix in expected_outputs:
                output_file = parent_dir / f"{filename_only}.{suffix}.funscript"
                if output_file.exists():
                    print(f"  [OK] {output_file.name}")
                    generated_count += 1
                else:
                    print(f"  [MISSING] {output_file.name}")

            print(f"\nSummary: {generated_count}/{len(expected_outputs)} files generated")

            # Check temp directory
            temp_dir = parent_dir / "funscript-temp"
            if config['options']['delete_intermediary_files']:
                if not temp_dir.exists():
                    print(f"  [OK] Temporary directory cleaned up")
                else:
                    print(f"  [ERROR] Temporary directory still exists")
            else:
                if temp_dir.exists():
                    print(f"  [OK] Temporary directory preserved")
                    temp_files = list(temp_dir.glob("*.funscript"))
                    print(f"    Contains {len(temp_files)} intermediary files")

        else:
            print("\n[FAILED] Processing failed!")

    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
            print(f"\nCleaned up test file: {test_file}")
        except:
            pass


if __name__ == "__main__":
    test_processor()