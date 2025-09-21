#!/usr/bin/env python3
"""
Test that top-right-left is the vertical mirror of top-left-right.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from funscript import Funscript
from processing.funscript_1d_to_2d import generate_alpha_beta_from_main

def test_vertical_mirror():
    """Test that top-right-left is the vertical mirror of top-left-right."""
    print("Testing vertical mirror relationship...")

    # Use the real test funscript
    test_file = Path(__file__).parent.parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load the original funscript
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript loaded: {len(original_funscript.y)} actions")

        # Test top-left-right algorithm
        print("\n=== TOP-LEFT-RIGHT ===")
        alpha_tlr, beta_tlr = generate_alpha_beta_from_main(
            original_funscript,
            points_per_second=10,
            algorithm="top-left-right",
            min_distance_from_center=0.2,
            speed_at_edge_hz=2.0
        )

        print(f"Top-Left-Right results:")
        print(f"Alpha range: {min(alpha_tlr.y):.3f} to {max(alpha_tlr.y):.3f}")
        print(f"Beta range: {min(beta_tlr.y):.3f} to {max(beta_tlr.y):.3f}")
        print(f"First 5 alpha: {alpha_tlr.y[:5]}")
        print(f"First 5 beta: {beta_tlr.y[:5]}")

        # Test top-right-left algorithm (should be vertical mirror)
        print("\n=== TOP-RIGHT-LEFT (vertical mirror) ===")
        alpha_trl, beta_trl = generate_alpha_beta_from_main(
            original_funscript,
            points_per_second=10,
            algorithm="top-right-left",
            min_distance_from_center=0.2,
            speed_at_edge_hz=2.0
        )

        print(f"Top-Right-Left results:")
        print(f"Alpha range: {min(alpha_trl.y):.3f} to {max(alpha_trl.y):.3f}")
        print(f"Beta range: {min(beta_trl.y):.3f} to {max(beta_trl.y):.3f}")
        print(f"First 5 alpha: {alpha_trl.y[:5]}")
        print(f"First 5 beta: {beta_trl.y[:5]}")

        # Verify vertical mirroring
        print("\n=== VERIFICATION ===")

        # Alpha should be the same
        alpha_diff = np.abs(np.array(alpha_tlr.y) - np.array(alpha_trl.y))
        max_alpha_diff = np.max(alpha_diff)
        print(f"Max alpha difference: {max_alpha_diff:.6f}")

        # Beta should be inverted (1.0 - beta_tlr should equal beta_trl)
        beta_tlr_inverted = 1.0 - np.array(beta_tlr.y)
        beta_diff = np.abs(beta_tlr_inverted - np.array(beta_trl.y))
        max_beta_diff = np.max(beta_diff)
        print(f"Max beta difference (after inversion): {max_beta_diff:.6f}")

        # Check if they're properly mirrored
        if max_alpha_diff < 0.001:
            print("OK: Alpha values are identical (as expected)")
        else:
            print("WARNING: Alpha values are not identical")

        if max_beta_diff < 0.001:
            print("OK: Beta values are properly inverted (vertical mirror)")
        else:
            print("WARNING: Beta values are not properly inverted")

        # Show specific examples
        print(f"\nExample comparison:")
        print(f"TLR: Alpha={alpha_tlr.y[10]:.3f}, Beta={beta_tlr.y[10]:.3f}")
        print(f"TRL: Alpha={alpha_trl.y[10]:.3f}, Beta={beta_trl.y[10]:.3f}")
        print(f"TLR Beta inverted: {1.0 - beta_tlr.y[10]:.3f}")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vertical_mirror()