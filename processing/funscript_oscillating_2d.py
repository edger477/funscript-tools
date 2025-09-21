import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


def convert_funscript_oscillating(funscript, points_per_second=25, algorithm="top-left-right", min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    """
    Convert a 1D funscript into 2D (alpha/beta) using oscillating algorithms.

    Args:
        funscript: Input Funscript object
        points_per_second: Number of interpolated points per second
        algorithm: Oscillating algorithm - "top-left-right", "top-right-left"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_at_edge_hz: Speed in Hz at which dot reaches maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    at = funscript.x  # Time in seconds
    pos = funscript.y  # Position 0.0-1.0

    t_out = []
    x_out = []  # Alpha (x-axis)
    y_out = []  # Beta (y-axis)

    # Convert speed_at_edge_hz to time needed to go from 0 to 1
    # If speed_at_edge_hz = 2Hz, then full range (0 to 1) takes 0.5 seconds
    max_speed_threshold = abs(1.0) / (1.0 / speed_at_edge_hz)  # Speed for full range in 1/Hz seconds

    for i in range(len(pos) - 1):
        start_t, end_t = at[i:i+2]
        start_p, end_p = pos[i:i+2]

        # Calculate number of points for this segment
        n = int(np.clip(float((end_t - start_t) * points_per_second), 1, None))

        # Calculate speed for this segment (position change per second)
        segment_duration = end_t - start_t
        position_change = abs(end_p - start_p)
        current_speed = position_change / segment_duration if segment_duration > 0 else 0

        # Map speed to radius (min_distance_from_center to 1.0)
        speed_ratio = min(current_speed / max_speed_threshold, 1.0)  # Clamp to 1.0
        radius_scale = min_distance_from_center + (1.0 - min_distance_from_center) * speed_ratio

        # Create time array
        t = np.linspace(0.0, end_t - start_t, n, endpoint=False)

        # Calculate movement parameters
        center = (end_p + start_p) / 2
        movement_range = abs(end_p - start_p)

        # Check if this is a small vertical movement (should move toward center)
        is_small_movement = movement_range < 0.1  # Small threshold for center movement

        if is_small_movement:
            # Small movements - still use direct position mapping but with smaller radius
            progress = np.linspace(0, 1, n, endpoint=False)
            funscript_positions = np.interp(progress, [0, 1], [start_p, end_p])

            if algorithm == "top-left-right":
                # Map funscript position to angle: 1.0 → 0°, 0.0 → 270°
                theta = (1.0 - funscript_positions) * (3*np.pi/2)
                # Use speed-based radius with scaling for small movements
                small_radius = radius_scale * (0.1 + 0.2 * movement_range)  # Scale radius based on movement size and speed
                x = 0.5 + small_radius * np.cos(theta)
                y = 0.5 + small_radius * np.sin(theta)
            elif algorithm == "top-right-left":
                # Map funscript position to angle: 1.0 → 0°, 0.0 → 90°
                theta = (1.0 - funscript_positions) * (np.pi/2)
                # Use speed-based radius with scaling for small movements
                small_radius = radius_scale * (0.1 + 0.2 * movement_range)  # Scale radius based on movement size and speed
                x = 0.5 + small_radius * np.cos(theta)
                y = 0.5 + small_radius * np.sin(theta)
        else:
            # Large movements - use algorithm-specific patterns
            if algorithm == "top-left-right":
                # Map funscript position directly to angular position
                # 1.0 (top) → 0°, 0.0 (bottom) → 270° (3π/2)
                # Create smooth interpolation between start and end positions
                progress = np.linspace(0, 1, n, endpoint=False)
                funscript_positions = np.interp(progress, [0, 1], [start_p, end_p])

                # Convert funscript position (0.0-1.0) to angle (270°-0°)
                # funscript 1.0 → 0°, funscript 0.0 → 270°
                theta = (1.0 - funscript_positions) * (3*np.pi/2)  # 0° to 270°

                # Calculate positions on the arc using speed-based radius
                radius = 0.3 * radius_scale  # Speed-based radius for oscillating motion
                x = 0.5 + radius * np.cos(theta)
                y = 0.5 + radius * np.sin(theta)

            elif algorithm == "top-right-left":
                # Map funscript position directly to angular position
                # 1.0 (top) → 0°, 0.0 (bottom) → 90° (π/2)
                # Create smooth interpolation between start and end positions
                progress = np.linspace(0, 1, n, endpoint=False)
                funscript_positions = np.interp(progress, [0, 1], [start_p, end_p])

                # Convert funscript position (0.0-1.0) to angle (90°-0°)
                # funscript 1.0 → 0°, funscript 0.0 → 90°
                theta = (1.0 - funscript_positions) * (np.pi/2)  # 0° to 90°

                # Calculate positions on the arc using speed-based radius
                radius = 0.3 * radius_scale  # Speed-based radius for oscillating motion
                x = 0.5 + radius * np.cos(theta)
                y = 0.5 + radius * np.sin(theta)

        # Append to output arrays
        t_out += list(t + start_t)
        x_out += list(x)
        y_out += list(y)

    # Create alpha and beta funscripts
    alpha_funscript = Funscript(t_out, x_out)
    beta_funscript = Funscript(t_out, y_out)

    return alpha_funscript, beta_funscript


def generate_alpha_beta_oscillating(main_funscript, points_per_second=25, algorithm="top-left-right", min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    """
    Generate alpha and beta funscripts from a main 1D funscript using oscillating algorithms.

    Args:
        main_funscript: Input Funscript object
        points_per_second: Number of interpolated points per second
        algorithm: Oscillating algorithm - "top-left-right", "top-right-left"
        min_distance_from_center: Minimum radius from center (0.1-0.9)
        speed_at_edge_hz: Speed in Hz at which dot reaches maximum radius

    Returns:
        tuple: (alpha_funscript, beta_funscript)
    """
    return convert_funscript_oscillating(main_funscript, points_per_second, algorithm, min_distance_from_center, speed_at_edge_hz)