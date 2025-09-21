#!/usr/bin/env python3
"""
Compare basic circular and prostate standard algorithms.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from funscript import Funscript
from processing.funscript_1d_to_2d import generate_alpha_beta_from_main
from processing.funscript_prostate_2d import generate_alpha_beta_prostate_from_main

def test_compare_algorithms():
    """Compare basic and prostate algorithms."""
    print("Comparing basic circular and prostate standard algorithms...")

    # Use the real test funscript
    test_file = Path(__file__).parent.parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load the original funscript
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript loaded: {len(original_funscript.y)} actions")

        # Test basic circular conversion
        print("\n=== BASIC CIRCULAR ===")
        alpha_basic, beta_basic = generate_alpha_beta_from_main(
            original_funscript,
            points_per_second=10,
            algorithm="circular",
            min_distance_from_center=0.1,
            speed_at_edge_hz=2.0
        )

        print(f"Basic circular results:")
        print(f"Alpha range: {min(alpha_basic.y):.3f} to {max(alpha_basic.y):.3f}")
        print(f"Beta range: {min(beta_basic.y):.3f} to {max(beta_basic.y):.3f}")
        print(f"Output points: {len(alpha_basic.y)}")
        print(f"First 5 alpha: {alpha_basic.y[:5]}")
        print(f"First 5 beta: {beta_basic.y[:5]}")

        # Test prostate standard conversion
        print("\n=== PROSTATE STANDARD ===")
        alpha_prostate, beta_prostate = generate_alpha_beta_prostate_from_main(
            original_funscript,
            points_per_second=10,
            algorithm="standard",
            min_distance_from_center=0.5,  # This should be ignored for standard
            generate_from_inverted=True
        )

        print(f"Prostate standard results:")
        print(f"Alpha range: {min(alpha_prostate.y):.3f} to {max(alpha_prostate.y):.3f}")
        print(f"Beta range: {min(beta_prostate.y):.3f} to {max(beta_prostate.y):.3f}")
        print(f"Output points: {len(alpha_prostate.y)}")
        print(f"First 5 alpha: {alpha_prostate.y[:5]}")
        print(f"First 5 beta: {beta_prostate.y[:5]}")

        # Check if they're similar
        print("\n=== COMPARISON ===")
        if abs(min(alpha_basic.y) - min(alpha_prostate.y)) < 0.1 and abs(max(alpha_basic.y) - max(alpha_prostate.y)) < 0.1:
            print("✓ Alpha ranges are similar")
        else:
            print("✗ Alpha ranges are different")

        if abs(min(beta_basic.y) - min(beta_prostate.y)) < 0.1 and abs(max(beta_basic.y) - max(beta_prostate.y)) < 0.1:
            print("✓ Beta ranges are similar")
        else:
            print("✗ Beta ranges are different")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_compare_algorithms()