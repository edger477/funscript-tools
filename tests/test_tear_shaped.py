#!/usr/bin/env python3
"""
Test the new tear-shaped algorithm to verify it works correctly.
"""
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).parent))

from funscript import Funscript
from processing.funscript_prostate_2d import generate_alpha_beta_prostate_from_main

def test_tear_shaped_algorithm():
    """Test the tear-shaped algorithm with real funscript data."""
    print("Testing tear-shaped algorithm...")

    # Use the real test funscript
    test_file = Path(__file__).parent / "testdata" / "test.funscript"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        return

    try:
        # Load the original funscript
        original_funscript = Funscript.from_file(test_file)
        print(f"Original funscript loaded: {len(original_funscript.y)} actions")
        print(f"Y range: {min(original_funscript.y):.3f} to {max(original_funscript.y):.3f}")

        # Test tear-shaped conversion
        alpha_prostate, beta_prostate = generate_alpha_beta_prostate_from_main(
            original_funscript,
            points_per_second=25,
            algorithm="tear-shaped",
            min_distance_from_center=0.5,
            generate_from_inverted=True
        )

        print(f"\nTear-shaped conversion results:")
        print(f"Alpha range: {min(alpha_prostate.y):.3f} to {max(alpha_prostate.y):.3f}")
        print(f"Beta range: {min(beta_prostate.y):.3f} to {max(beta_prostate.y):.3f}")
        print(f"Output points: {len(alpha_prostate.y)}")

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

        # Create a simple visualization
        plt.figure(figsize=(12, 5))

        # Plot 1: Original vs time
        plt.subplot(1, 3, 1)
        plt.plot(original_funscript.x[:100], original_funscript.y[:100])
        plt.title("Original Funscript (first 100 points)")
        plt.xlabel("Time (ms)")
        plt.ylabel("Position (0-1)")
        plt.grid(True)

        # Plot 2: Alpha/Beta vs time
        plt.subplot(1, 3, 2)
        plt.plot(alpha_prostate.x[:100], alpha_prostate.y[:100], label="Alpha", alpha=0.7)
        plt.plot(beta_prostate.x[:100], beta_prostate.y[:100], label="Beta", alpha=0.7)
        plt.title("Tear-shaped Output (first 100 points)")
        plt.xlabel("Time (ms)")
        plt.ylabel("Position (0-1)")
        plt.legend()
        plt.grid(True)

        # Plot 3: 2D trajectory (Alpha vs Beta)
        plt.subplot(1, 3, 3)
        plt.scatter(alpha_prostate.y[:200], beta_prostate.y[:200], s=1, alpha=0.6)
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.xlabel("Alpha (0-1)")
        plt.ylabel("Beta (0-1)")
        plt.title("2D Trajectory (first 200 points)")
        plt.grid(True)

        # Draw circle reference
        circle = plt.Circle((0.5, 0.5), 0.5, fill=False, color='red', linestyle='--', alpha=0.5)
        plt.gca().add_patch(circle)
        plt.gca().set_aspect('equal')

        plt.tight_layout()

        # Save plot
        plot_file = Path(__file__).parent / "tear_shaped_test_plot.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"\nVisualization saved to: {plot_file}")

        plt.show()

        # Save test output files
        output_dir = Path(__file__).parent
        alpha_file = output_dir / "test_tear_alpha.funscript"
        beta_file = output_dir / "test_tear_beta.funscript"

        alpha_prostate.save_to_path(alpha_file)
        beta_prostate.save_to_path(beta_file)

        print(f"Test files saved:")
        print(f"  {alpha_file}")
        print(f"  {beta_file}")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tear_shaped_algorithm()