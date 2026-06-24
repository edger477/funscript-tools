import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript


class FunscriptEditorError(Exception):
    """Custom exception for errors during funscript editing."""
    pass


class FunscriptEditor:
    """
    A class to perform complex, layered editing operations on a set of funscripts.
    All time-based parameters (duration, start_time, ramp_in, ramp_out) are expected in milliseconds.
    """
    def __init__(self, funscripts_by_axis: Dict[str, Funscript], filename_stem: str, normalization_config: Dict[str, Dict[str, float]] = None):
        """
        Initializes the editor with a dictionary of funscript objects mapped by their axis name.
        e.g., {'volume': FunscriptObject, 'pulse_frequency': FunscriptObject}

        Args:
            funscripts_by_axis: Dictionary mapping axis names to Funscript objects
            filename_stem: Base filename for saving
            normalization_config: Dictionary with normalization max values per axis
        """
        self.funscripts = funscripts_by_axis
        self.filename_stem = filename_stem
        self.history = [] # For potential undo/redo functionality later

        # Set normalization config with defaults if not provided
        self.normalization_config = normalization_config or {
            'pulse_frequency': {'max': 200.0},
            'pulse_width': {'max': 100.0},
            'frequency': {'max': 360.0},
            'volume': {'max': 1.0}
        }

    def _get_target_axes(self, axis: str) -> List[str]:
        """
        Returns a list of all axes that should be affected by an operation.
        Supports comma-separated axis names for explicit multi-axis targeting.

        Args:
            axis: The axis name(s) - can be a single axis or comma-separated list (e.g., "volume,volume-prostate")

        Returns:
            List of axis names to apply the operation to
        """
        # Parse comma-separated axis names
        axis_names = [name.strip() for name in axis.split(',')]

        # Filter to only existing funscripts
        target_axes = [name for name in axis_names if name in self.funscripts]

        # Warn about any non-existent axes
        for name in axis_names:
            if name not in self.funscripts:
                print(f"WARNING: Axis '{name}' not found in loaded funscripts. Skipping.")

        return target_axes

    def _ensure_dense_timestamps(self, axis: str, start_time_s: float, end_time_s: float, points_per_second: float = 25.0):
        """Insert evenly-spaced timestamps within [start_time_s, end_time_s] for the given axis.

        Positions at new timestamps are linearly interpolated from existing data.
        Timestamps already within 10% of a step size are skipped (no-op for dense axes like alpha/beta).
        This ensures event modulation waveforms have enough data points to be accurately represented.
        """
        fs = self.funscripts[axis]
        step = 1.0 / points_per_second

        dense_times = np.arange(start_time_s, end_time_s, step)
        if len(dense_times) == 0:
            return

        # Vectorised near-duplicate check: skip any dense time already covered
        tolerance = step * 0.1
        nearest_idx = np.searchsorted(fs.x, dense_times, side='left')
        prev_idx = np.clip(nearest_idx - 1, 0, len(fs.x) - 1)
        next_idx = np.clip(nearest_idx, 0, len(fs.x) - 1)
        dist = np.minimum(
            np.abs(fs.x[prev_idx] - dense_times),
            np.abs(fs.x[next_idx] - dense_times)
        )
        new_times = dense_times[dist > tolerance]

        if len(new_times) == 0:
            return

        new_positions = np.interp(new_times, fs.x, fs.y)

        all_times = np.concatenate([fs.x, new_times])
        all_positions = np.concatenate([fs.y, new_positions])
        sort_idx = np.argsort(all_times, kind='stable')
        fs.x = all_times[sort_idx]
        fs.y = all_positions[sort_idx]

    def _get_indices_for_range(self, fs: Funscript, start_time_ms: int, duration_ms: int) -> np.ndarray:
        """Returns the numpy array indices for a given time window (in ms)."""
        start_time_s = start_time_ms / 1000.0
        
        if duration_ms == 0:
            # For instantaneous events, find the first point at or after start_time_s
            idx = np.searchsorted(fs.x, start_time_s, side='left')
            if idx < len(fs.x) and fs.x[idx] == start_time_s:
                return np.array([idx])
            elif idx < len(fs.x): # If no exact match, apply to the next point
                return np.array([idx])
            return np.array([]) # No points found
        
        end_time_s = (start_time_ms + duration_ms) / 1000.0
        return np.where((fs.x >= start_time_s) & (fs.x < end_time_s))[0]

    def _normalize_value(self, axis: str, value: float) -> float:
        """Normalizes a raw value (e.g., Hz, percentage) to the 0.0-1.0 funscript range using config."""
        # Find matching normalization config for this axis
        for axis_key, config in self.normalization_config.items():
            if axis_key in axis:
                max_value = config.get('max', 1.0)
                # If max is 1.0, value is already normalized
                if max_value == 1.0:
                    return value
                # If value is already in 0.0-1.0 range and max is large, assume it's already normalized
                # Note: negative values are NOT treated as pre-normalized — they must be divided by max
                if max_value > 1.0 and 0.0 <= value <= 1.0:
                    return value
                # Otherwise normalize by dividing by max
                return value / max_value

        # Default: assume already normalized
        return value


    def apply_linear_change(self, axis: str, start_time_ms: int, duration_ms: int,
                              start_value: float, end_value: float,
                              ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                              mode: str = 'additive'):
        """
        Applies a linear change to the specified axis or axes.

        Args:
            axis (str): The funscript axis to target. Can be a single axis (e.g., 'volume')
                       or comma-separated list for multiple axes (e.g., 'volume,volume-prostate').
            start_time_ms (int): The timestamp to start the effect, in milliseconds.
            duration_ms (int): The duration of the effect, in milliseconds.
            start_value (float): The value of the effect at its beginning (0.0-1.0).
            end_value (float): The value of the effect at its end (0.0-1.0).
            ramp_in_ms (int): Duration in milliseconds for a linear fade-in of the effect's intensity.
            ramp_out_ms (int): Duration in milliseconds for a linear fade-out of the effect's intensity.
            mode (str): How to apply the effect: 'additive' or 'overwrite'.
        """
        # Get all target axes
        target_axes = self._get_target_axes(axis)

        if not target_axes:
            print(f"WARNING: No valid axes found in '{axis}'. Skipping linear change operation.")
            return

        # Apply operation to all target axes
        for target_axis in target_axes:
            self._apply_linear_change_single(target_axis, start_time_ms, duration_ms,
                                            start_value, end_value, ramp_in_ms, ramp_out_ms, mode)

    def _apply_linear_change_single(self, axis: str, start_time_ms: int, duration_ms: int,
                                      start_value: float, end_value: float,
                                      ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                                      mode: str = 'additive'):
        """Internal method to apply linear change to a single axis."""
        fs = self.funscripts[axis]
        indices = self._get_indices_for_range(fs, start_time_ms, duration_ms)

        if indices.size == 0:
            return # No points in range

        # Convert raw values to normalized funscript range
        normalized_start_value = self._normalize_value(axis, start_value)
        normalized_end_value = self._normalize_value(axis, end_value)

        # Convert times to seconds for calculations
        duration_s = duration_ms / 1000.0
        ramp_in_s = ramp_in_ms / 1000.0
        ramp_out_s = ramp_out_ms / 1000.0

        # Calculate base linear change values
        # relative_time_s = fs.x[indices] - (start_time_ms / 1000.0) # Not needed for linear values itself
        
        if indices.size > 1: # Only create a ramp if there's more than one point
            linear_values = np.linspace(normalized_start_value, normalized_end_value, indices.size)
        else: # For single point or duration=0
            linear_values = np.full(indices.size, normalized_start_value)

        # Apply based on mode
        if mode == 'additive':
            # Additive mode: use envelope multiplication as before
            envelope = np.ones_like(linear_values)

            if ramp_in_s > 0:
                ramp_in_end_s = min(ramp_in_s, duration_s)
                ramp_in_indices = np.where(fs.x[indices] - (start_time_ms / 1000.0) < ramp_in_end_s)[0]
                if ramp_in_indices.size > 0:
                    envelope[ramp_in_indices] *= np.linspace(0, 1, ramp_in_indices.size)

            if ramp_out_s > 0:
                ramp_out_start_s = duration_s - min(ramp_out_s, duration_s)
                ramp_out_indices = np.where(fs.x[indices] - (start_time_ms / 1000.0) > ramp_out_start_s)[0]
                if ramp_out_indices.size > 0:
                    envelope[ramp_out_indices] *= np.linspace(1, 0, ramp_out_indices.size)

            final_effect_values = linear_values * envelope
            fs.y[indices] = fs.y[indices] + final_effect_values

        elif mode == 'overwrite':
            # Overwrite mode: blend from/to original values during ramps
            # Save original values before any modification
            original_values = fs.y[indices].copy()

            # Start with the full effect
            fs.y[indices] = linear_values

            # Handle ramp_in: blend from original to effect
            if ramp_in_s > 0:
                ramp_in_end_s = min(ramp_in_s, duration_s)
                ramp_in_indices = np.where(fs.x[indices] - (start_time_ms / 1000.0) < ramp_in_end_s)[0]

                if ramp_in_indices.size > 0:
                    # Blend factor: 0 (100% original) → 1 (100% effect)
                    blend = np.linspace(0, 1, ramp_in_indices.size)
                    fs.y[indices[ramp_in_indices]] = (1 - blend) * original_values[ramp_in_indices] + blend * linear_values[ramp_in_indices]

            # Handle ramp_out: blend from effect back to original
            if ramp_out_s > 0:
                ramp_out_start_s = duration_s - min(ramp_out_s, duration_s)
                ramp_out_indices = np.where(fs.x[indices] - (start_time_ms / 1000.0) > ramp_out_start_s)[0]

                if ramp_out_indices.size > 0:
                    # Blend factor: 1 (100% effect) → 0 (100% original)
                    blend = np.linspace(1, 0, ramp_out_indices.size)
                    fs.y[indices[ramp_out_indices]] = blend * linear_values[ramp_out_indices] + (1 - blend) * original_values[ramp_out_indices]
        else:
            print(f"WARNING: Unknown mode '{mode}' for apply_linear_change. Skipping.")
            return

        # Ensure values remain within [0.0, 1.0] after operation
        fs.y[indices] = np.clip(fs.y[indices], 0.0, 1.0)

    def apply_modulation(self, axis: str, start_time_ms: int, duration_ms: int,
                         waveform: str, frequency: float, amplitude: float,
                         max_level_offset: float = 0.0, phase: float = 0.0,
                         ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                         mode: str = 'additive', duty_cycle: float = 0.5):
        """
        Applies a modulation (e.g., sine wave) to the specified axis or axes.

        Args:
            axis (str): The funscript axis to target. Can be a single axis (e.g., 'volume')
                       or comma-separated list for multiple axes (e.g., 'volume,volume-prostate').
            start_time_ms (int): The timestamp to start the effect, in milliseconds.
            duration_ms (int): The duration of the effect, in milliseconds.
            waveform (str): The shape of the wave. Supports 'sin', 'square', 'triangle', 'sawtooth'.
            frequency (float): The frequency of the wave in Hz.
            amplitude (float): The swing amplitude of the wave (direct value in axis units).
                               The wave oscillates ±amplitude around the center point.
            max_level_offset (float): Offset for the maximum level of the waveform in axis units.
                                     In additive mode, this is relative to the original values.
                                     In overwrite mode, this sets the absolute maximum level.
                                     The center point is calculated as: max_level_offset - amplitude.
            phase (float): The starting phase of the wave, in degrees (0-360).
            ramp_in_ms (int): Duration in milliseconds for a linear fade-in of the wave's amplitude.
            ramp_out_ms (int): Duration in milliseconds for a linear fade-out of the wave's amplitude.
            mode (str): How to apply the effect:
                       'additive': final = original + (max_level_offset - amplitude) + amplitude*waveform(...)
                       'overwrite': final = (max_level_offset - amplitude) + amplitude*waveform(...)
            duty_cycle (float): For square wave, the percentage of time at max value (0.01-0.99).
                               Default 0.5 (50% duty cycle). Ignored for other waveforms.
        """
        # Get all target axes
        target_axes = self._get_target_axes(axis)

        if not target_axes:
            print(f"WARNING: No valid axes found in '{axis}'. Skipping modulation operation.")
            return

        # Validate waveform
        supported_waveforms = ['sin', 'square', 'triangle', 'sawtooth']
        if waveform.lower() not in supported_waveforms:
            print(f"WARNING: Waveform '{waveform}' not supported. Supported: {supported_waveforms}. Skipping modulation.")
            return

        # Validate frequency
        if frequency > 30:
            print(f"WARNING: Modulation frequency {frequency} Hz exceeds recommended maximum of 30 Hz.")
            print(f"         High frequencies may not be accurately captured due to funscript data point spacing.")
            print(f"         Consider using a lower frequency (3-30 Hz) for better results.")

        # Apply operation to all target axes
        for target_axis in target_axes:
            self._apply_modulation_single(target_axis, start_time_ms, duration_ms,
                                         waveform, frequency, amplitude, max_level_offset, phase,
                                         ramp_in_ms, ramp_out_ms, mode, duty_cycle)

    def _apply_modulation_single(self, axis: str, start_time_ms: int, duration_ms: int,
                                  waveform: str, frequency: float, amplitude: float,
                                  max_level_offset: float = 0.0, phase: float = 0.0,
                                  ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                                  mode: str = 'additive', duty_cycle: float = 0.5):
        """Internal method to apply modulation to a single axis."""
        fs = self.funscripts[axis]
        self._ensure_dense_timestamps(axis, start_time_ms / 1000.0, (start_time_ms + duration_ms) / 1000.0)
        indices = self._get_indices_for_range(fs, start_time_ms, duration_ms)

        if indices.size == 0:
            return # No points in range

        duration_s = duration_ms / 1000.0
        start_time_s = start_time_ms / 1000.0
        ramp_in_s = ramp_in_ms / 1000.0
        ramp_out_s = ramp_out_ms / 1000.0

        relative_time_s = fs.x[indices] - start_time_s

        # Convert phase from degrees to radians and normalize to [0, 1]
        phase_rad = np.deg2rad(phase)
        phase_normalized = (phase / 360.0) % 1.0  # Phase as fraction of period

        # Calculate the phase of each point in the waveform (0 to 1 for each period)
        waveform_phase = (frequency * relative_time_s + phase_normalized) % 1.0

        # Generate base wave [-1, 1] (bipolar for true oscillations) based on waveform type
        waveform_lower = waveform.lower()

        if waveform_lower == 'sin':
            sin_arg = 2 * np.pi * frequency * relative_time_s + phase_rad
            base_wave = np.sin(sin_arg)

        elif waveform_lower == 'square':
            clipped_dc = np.clip(duty_cycle, 0.01, 0.99)
            base_wave = np.where(waveform_phase < clipped_dc, 1.0, -1.0)

        elif waveform_lower == 'triangle':
            base_wave = np.where(
                waveform_phase < 0.5,
                -1.0 + 4.0 * waveform_phase,
                3.0 - 4.0 * waveform_phase
            )

        elif waveform_lower == 'sawtooth':
            base_wave = -1.0 + 2.0 * waveform_phase

        else:
            print(f"ERROR: Unsupported waveform '{waveform}'. This should have been caught earlier.")
            return

        # Normalize amplitude and max_level_offset independently.
        # max_level_offset is the DC center of the wave relative to the current signal.
        # The wave oscillates ±amplitude around (current + max_level_offset).
        normalized_amplitude = self._normalize_value(axis, amplitude)
        normalized_max_offset = self._normalize_value(axis, max_level_offset)

        # generated_wave oscillates from (max_level_offset - amplitude) to (max_level_offset + amplitude)
        generated_wave = normalized_max_offset + normalized_amplitude * base_wave

        # Apply based on mode
        if mode == 'additive':
            # Additive mode: use envelope multiplication as before
            envelope = np.ones_like(generated_wave)

            if ramp_in_s > 0 and duration_s > 0:
                ramp_in_end_s = min(ramp_in_s, duration_s)
                ramp_in_indices = np.where(relative_time_s < ramp_in_end_s)[0]
                if ramp_in_indices.size > 0:
                    envelope[ramp_in_indices] *= np.linspace(0, 1, ramp_in_indices.size)

            if ramp_out_s > 0 and duration_s > 0:
                ramp_out_start_s = duration_s - min(ramp_out_s, duration_s)
                ramp_out_indices = np.where(relative_time_s > ramp_out_start_s)[0]
                if ramp_out_indices.size > 0:
                    envelope[ramp_out_indices] *= np.linspace(1, 0, ramp_out_indices.size)

            final_effect_values = generated_wave * envelope
            fs.y[indices] = fs.y[indices] + final_effect_values

        elif mode == 'overwrite':
            # Overwrite mode: blend from/to original values during ramps
            # Save original values before any modification
            original_values = fs.y[indices].copy()

            # Start with the full effect
            fs.y[indices] = generated_wave

            # Handle ramp_in: blend from original to effect
            if ramp_in_s > 0 and duration_s > 0:
                ramp_in_end_s = min(ramp_in_s, duration_s)
                ramp_in_indices = np.where(relative_time_s < ramp_in_end_s)[0]

                if ramp_in_indices.size > 0:
                    # Blend factor: 0 (100% original) → 1 (100% effect)
                    blend = np.linspace(0, 1, ramp_in_indices.size)
                    fs.y[indices[ramp_in_indices]] = (1 - blend) * original_values[ramp_in_indices] + blend * generated_wave[ramp_in_indices]

            # Handle ramp_out: blend from effect back to original
            if ramp_out_s > 0 and duration_s > 0:
                ramp_out_start_s = duration_s - min(ramp_out_s, duration_s)
                ramp_out_indices = np.where(relative_time_s > ramp_out_start_s)[0]

                if ramp_out_indices.size > 0:
                    # Blend factor: 1 (100% effect) → 0 (100% original)
                    blend = np.linspace(1, 0, ramp_out_indices.size)
                    fs.y[indices[ramp_out_indices]] = blend * generated_wave[ramp_out_indices] + (1 - blend) * original_values[ramp_out_indices]
        else:
            print(f"WARNING: Unknown mode '{mode}' for apply_modulation. Skipping.")
            return

        # Ensure values remain within [0.0, 1.0] after operation
        fs.y[indices] = np.clip(fs.y[indices], 0.0, 1.0)

    def get_validation_report(self) -> Dict[str, str]:
        """
        Analyzes the current state of the funscripts and reports any out-of-bounds values.
        (Implementation to be added)
        """
        report = {}
        for axis, fs in self.funscripts.items():
            min_val, max_val = np.min(fs.y), np.max(fs.y)
            if min_val < 0 or max_val > 1.0:
                report[axis] = f"Axis '{axis}' is out of bounds. Min: {min_val:.2f}, Max: {max_val:.2f}."
            else:
                report[axis] = "OK"
        return report

    def save_funscripts(self, output_dir: Path):
        """
        Saves all modified funscript objects to the specified directory.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        for axis_name, fs in self.funscripts.items():
            # Use the stored filename_stem and axis_name to reconstruct the full filename
            filename = f"{self.filename_stem}.{axis_name}.funscript"
            fs.save_to_path(output_dir / filename)
        print(f"INFO: Saved {len(self.funscripts)} files to {output_dir}")