#!/usr/bin/env python3
"""
Simple test of the new tear-shaped algorithm.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from funscript import Funscript
from processing.funscript_prostate_2d import generate_alpha_beta_prostate_from_main

def test_tear_shaped_simple():
    """Simple test of the tear-shaped algorithm."""
    print("Testing tear-shaped algorithm (simple)...")

    # Use the real test funscript
    test_file = Path(__file__).parent.parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load the original funscript
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript loaded: {len(original_funscript.y)} actions")

        # Test tear-shaped conversion with small sample
        alpha_prostate, beta_prostate = generate_alpha_beta_prostate_from_main(
            original_funscript,
            points_per_second=10,  # Reduce for faster processing
            algorithm="tear-shaped",
            min_distance_from_center=0.5,
            generate_from_inverted=True
        )

        print(f"\nTear-shaped conversion results:")
        print(f"Alpha range: {min(alpha_prostate.y):.3f} to {max(alpha_prostate.y):.3f}")
        print(f"Beta range: {min(beta_prostate.y):.3f} to {max(beta_prostate.y):.3f}")
        print(f"Output points: {len(alpha_prostate.y)}")

        # Check first 10 values
        print(f"\nFirst 10 alpha values: {alpha_prostate.y[:10]}")
        print(f"First 10 beta values: {beta_prostate.y[:10]}")

        # Check for valid ranges
        alpha_out_of_range = [v for v in alpha_prostate.y if v < 0 or v > 1]
        beta_out_of_range = [v for v in beta_prostate.y if v < 0 or v > 1]

        if alpha_out_of_range:
            print(f"WARNING: {len(alpha_out_of_range)} alpha values out of 0-1 range")
            print(f"Examples: {alpha_out_of_range[:5]}")
        else:
            print("OK: All alpha values in 0-1 range")

        if beta_out_of_range:
            print(f"WARNING: {len(beta_out_of_range)} beta values out of 0-1 range")
            print(f"Examples: {beta_out_of_range[:5]}")
        else:
            print("OK: All beta values in 0-1 range")

        # Test saving
        output_dir = Path(__file__).parent
        alpha_file = output_dir / "test_tear_alpha_simple.funscript"
        beta_file = output_dir / "test_tear_beta_simple.funscript"

        alpha_prostate.save_to_path(alpha_file)
        beta_prostate.save_to_path(beta_file)

        print(f"\nTest files saved successfully")
        print("Tear-shaped algorithm test completed!")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tear_shaped_simple()