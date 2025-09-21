#!/usr/bin/env python3
"""
Test the standard prostate algorithm to verify it produces proper semicircles.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from funscript import Funscript
from processing.funscript_prostate_2d import generate_alpha_beta_prostate_from_main

def test_standard_prostate():
    """Test the standard prostate algorithm."""
    print("Testing standard prostate algorithm...")

    # Use the real test funscript
    test_file = Path(__file__).parent.parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load the original funscript
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript loaded: {len(original_funscript.y)} actions")

        # Test standard prostate conversion
        alpha_prostate, beta_prostate = generate_alpha_beta_prostate_from_main(
            original_funscript,
            points_per_second=10,  # Reduce for faster processing
            algorithm="standard",
            min_distance_from_center=0.5,  # This parameter is not used in standard
            generate_from_inverted=True
        )

        print(f"\nStandard prostate conversion results:")
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
        else:
            print("OK: All alpha values in 0-1 range")

        if beta_out_of_range:
            print(f"WARNING: {len(beta_out_of_range)} beta values out of 0-1 range")
        else:
            print("OK: All beta values in 0-1 range")

        # Check if it's producing semicircular motion
        # For semicircle: alpha should range from 0 to 1, beta should range from 0.5 to 1.0
        expected_alpha_min = 0.0
        expected_alpha_max = 1.0
        expected_beta_min = 0.5
        expected_beta_max = 1.0

        actual_alpha_min = min(alpha_prostate.y)
        actual_alpha_max = max(alpha_prostate.y)
        actual_beta_min = min(beta_prostate.y)
        actual_beta_max = max(beta_prostate.y)

        print(f"\nSemicircle validation:")
        print(f"Alpha range: {actual_alpha_min:.3f} to {actual_alpha_max:.3f} (expected: {expected_alpha_min:.1f} to {expected_alpha_max:.1f})")
        print(f"Beta range: {actual_beta_min:.3f} to {actual_beta_max:.3f} (expected: {expected_beta_min:.1f} to {expected_beta_max:.1f})")

        # Check if ranges are approximately correct (within 0.1 tolerance)
        alpha_ok = abs(actual_alpha_min - expected_alpha_min) < 0.1 and abs(actual_alpha_max - expected_alpha_max) < 0.1
        beta_ok = abs(actual_beta_min - expected_beta_min) < 0.1 and abs(actual_beta_max - expected_beta_max) < 0.1

        if alpha_ok and beta_ok:
            print("✅ Semicircular motion ranges look correct!")
        else:
            print("❌ Semicircular motion ranges are not as expected")

        # Test saving
        output_dir = Path(__file__).parent
        alpha_file = output_dir / "test_standard_alpha.funscript"
        beta_file = output_dir / "test_standard_beta.funscript"

        alpha_prostate.save_to_path(alpha_file)
        beta_prostate.save_to_path(beta_file)

        print(f"\nTest files saved successfully")
        print("Standard prostate algorithm test completed!")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_standard_prostate()