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
    def __init__(self, funscripts_by_axis: Dict[str, Funscript], filename_stem: str, normalization_config: Dict[str, Dict[str, float]] = None, apply_to_linked: bool = True):
        """
        Initializes the editor with a dictionary of funscript objects mapped by their axis name.
        e.g., {'volume': FunscriptObject, 'pulse_frequency': FunscriptObject}

        Args:
            funscripts_by_axis: Dictionary mapping axis names to Funscript objects
            filename_stem: Base filename for saving
            normalization_config: Dictionary with normalization max values per axis
            apply_to_linked: Whether to apply operations to linked axes (default True)
        """
        self.funscripts = funscripts_by_axis
        self.filename_stem = filename_stem
        self.history = [] # For potential undo/redo functionality later
        self.apply_to_linked = apply_to_linked

        # Set normalization config with defaults if not provided
        self.normalization_config = normalization_config or {
            'pulse_frequency': {'max': 200.0},
            'pulse_width': {'max': 100.0},
            'frequency': {'max': 360.0},
            'volume': {'max': 1.0}
        }

        # Define linked axes - operations on the primary axis also apply to linked axes
        self.linked_axes = {
            'volume': ['volume-prostate'],
            'alpha': ['alpha-prostate'],
            'beta': ['beta-prostate']
        }

    def _get_target_axes(self, axis: str) -> List[str]:
        """
        Returns a list of all axes that should be affected by an operation on the given axis.
        Includes the primary axis and any linked axes that exist in the loaded funscripts.

        Args:
            axis: The primary axis name

        Returns:
            List of axis names to apply the operation to
        """
        target_axes = [axis] if axis in self.funscripts else []

        # Add linked axes if they exist and apply_to_linked is enabled
        if self.apply_to_linked and axis in self.linked_axes:
            for linked_axis in self.linked_axes[axis]:
                if linked_axis in self.funscripts:
                    target_axes.append(linked_axis)

        return target_axes

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
                if max_value > 1.0 and value <= 1.0:
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
        Applies a linear change to the specified axis and any linked axes.

        Args:
            axis (str): The funscript axis to target (e.g., 'volume', 'pulse_frequency').
            start_time_ms (int): The timestamp to start the effect, in milliseconds.
            duration_ms (int): The duration of the effect, in milliseconds.
            start_value (float): The value of the effect at its beginning (0.0-1.0).
            end_value (float): The value of the effect at its end (0.0-1.0).
            ramp_in_ms (int): Duration in milliseconds for a linear fade-in of the effect's intensity.
            ramp_out_ms (int): Duration in milliseconds for a linear fade-out of the effect's intensity.
            mode (str): How to apply the effect: 'additive' or 'overwrite'.
        """
        # Get all target axes (primary + linked)
        target_axes = self._get_target_axes(axis)

        if not target_axes:
            print(f"WARNING: Axis '{axis}' not found. Skipping linear change operation.")
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

        # Apply ramp_in and ramp_out envelopes
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
        
        # Combine linear values with envelope
        final_effect_values = linear_values * envelope

        # Apply based on mode
        if mode == 'additive':
            fs.y[indices] = fs.y[indices] + final_effect_values
        elif mode == 'overwrite':
            fs.y[indices] = final_effect_values
        else:
            print(f"WARNING: Unknown mode '{mode}' for apply_linear_change. Skipping.")
            return

        # Ensure values remain within [0.0, 1.0] after operation
        fs.y[indices] = np.clip(fs.y[indices], 0.0, 1.0)

    def apply_modulation(self, axis: str, start_time_ms: int, duration_ms: int,
                         waveform: str, frequency: float, amplitude: float,
                         offset: float = 0.0, phase: float = 0.0,
                         ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                         mode: str = 'additive'):
        """
        Applies a modulation (e.g., sine wave) to the specified axis and any linked axes.

        Args:
            axis (str): The funscript axis to target.
            start_time_ms (int): The timestamp to start the effect, in milliseconds.
            duration_ms (int): The duration of the effect, in milliseconds.
            waveform (str): The shape of the wave. Currently supports 'sin'.
            frequency (float): The frequency of the wave in Hz.
            amplitude (float): The swing amplitude of the wave (direct value in axis units).
                               The wave oscillates ±amplitude around the baseline.
            offset (float): Additive shift to the baseline. In additive mode, shifts the center
                           point of oscillation. In overwrite mode, sets the baseline value.
            phase (float): The starting phase of the wave, in degrees (0-360).
            ramp_in_ms (int): Duration in milliseconds for a linear fade-in of the wave's amplitude.
            ramp_out_ms (int): Duration in milliseconds for a linear fade-out of the wave's amplitude.
            mode (str): How to apply the effect:
                       'additive': final = original + offset + amplitude*sin(...)
                       'overwrite': final = offset + amplitude*sin(...)
        """
        # Get all target axes (primary + linked)
        target_axes = self._get_target_axes(axis)

        if not target_axes:
            print(f"WARNING: Axis '{axis}' not found. Skipping modulation operation.")
            return
        if waveform.lower() != 'sin':
            print(f"WARNING: Waveform '{waveform}' not supported. Skipping modulation.")
            return

        # Apply operation to all target axes
        for target_axis in target_axes:
            self._apply_modulation_single(target_axis, start_time_ms, duration_ms,
                                         waveform, frequency, amplitude, offset, phase,
                                         ramp_in_ms, ramp_out_ms, mode)

    def _apply_modulation_single(self, axis: str, start_time_ms: int, duration_ms: int,
                                  waveform: str, frequency: float, amplitude: float,
                                  offset: float = 0.0, phase: float = 0.0,
                                  ramp_in_ms: int = 0, ramp_out_ms: int = 0,
                                  mode: str = 'additive'):
        """Internal method to apply modulation to a single axis."""
        fs = self.funscripts[axis]
        indices = self._get_indices_for_range(fs, start_time_ms, duration_ms)

        if indices.size == 0:
            return # No points in range

        duration_s = duration_ms / 1000.0
        start_time_s = start_time_ms / 1000.0
        ramp_in_s = ramp_in_ms / 1000.0
        ramp_out_s = ramp_out_ms / 1000.0

        relative_time_s = fs.x[indices] - start_time_s

        # Convert phase from degrees to radians
        phase_rad = np.deg2rad(phase)

        # DEBUG: Check array shapes
        print(f"DEBUG shapes:")
        print(f"  - frequency type: {type(frequency)}, value: {frequency}")
        print(f"  - phase_rad type: {type(phase_rad)}, value: {phase_rad}")
        print(f"  - relative_time_s type: {type(relative_time_s)}, shape: {relative_time_s.shape if hasattr(relative_time_s, 'shape') else 'no shape'}")

        # Manual calculation test
        sin_arg = 2 * np.pi * frequency * relative_time_s + phase_rad
        print(f"  - sin_arg type: {type(sin_arg)}, shape: {sin_arg.shape if hasattr(sin_arg, 'shape') else 'no shape'}")
        print(f"  - sin_arg first 5: {sin_arg[:5]}")
        print(f"  - sin_arg last 5: {sin_arg[-5:]}")

        # Generate base sine wave [-1, 1] (bipolar for true oscillations)
        base_wave = np.sin(sin_arg)
        print(f"  - base_wave calculated from sin_arg")
        print(f"  - Manually: sin({sin_arg[0]:.3f}) = {np.sin(sin_arg[0]):.10f}")
        print(f"  - Manually: sin({sin_arg[1]:.3f}) = {np.sin(sin_arg[1]):.10f}")
        print(f"  - Manually: sin({sin_arg[2]:.3f}) = {np.sin(sin_arg[2]):.10f}")

        # Normalize amplitude and offset to funscript range
        normalized_amplitude = self._normalize_value(axis, amplitude)
        normalized_offset = self._normalize_value(axis, offset)

        # DEBUG OUTPUT
        print(f"DEBUG apply_modulation on {axis}:")
        print(f"  - Points in range: {indices.size}")
        print(f"  - Raw amplitude: {amplitude}, normalized: {normalized_amplitude}")
        print(f"  - Raw offset: {offset}, normalized: {normalized_offset}")
        print(f"  - Frequency: {frequency} Hz")
        print(f"  - Time range: {relative_time_s[0]:.3f}s to {relative_time_s[-1]:.3f}s" if indices.size > 0 else "  - No points")
        if indices.size > 0:
            print(f"  - relative_time_s unique values: {np.unique(relative_time_s).size}")
            print(f"  - First 5 relative times: {relative_time_s[:5]}")
            print(f"  - Sin argument range: [{(2 * np.pi * frequency * relative_time_s).min():.2f}, {(2 * np.pi * frequency * relative_time_s).max():.2f}] radians")
            print(f"  - base_wave range: [{base_wave.min():.10f}, {base_wave.max():.10f}]")
            print(f"  - base_wave first 10 values: {base_wave[:10]}")
            print(f"  - base_wave last 10 values: {base_wave[-10:]}")
            print(f"  - base_wave std deviation: {base_wave.std():.10f}")
            print(f"  - Are all values identical? {np.all(base_wave == base_wave[0])}")
            print(f"  - Original values range: [{fs.y[indices].min():.3f}, {fs.y[indices].max():.3f}]")

        # Generate modulation wave: offset + amplitude * sin(...)
        # This creates oscillations of ±amplitude around the offset baseline
        modulation_wave = normalized_amplitude * base_wave
        generated_wave = normalized_offset + modulation_wave

        # Apply ramp_in and ramp_out envelopes to the generated wave
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
        
        # Apply envelope to the generated wave
        final_effect_values = generated_wave * envelope

        print(f"DEBUG before applying:")
        print(f"  - generated_wave range: [{generated_wave.min():.10f}, {generated_wave.max():.10f}]")
        print(f"  - final_effect_values range: [{final_effect_values.min():.10f}, {final_effect_values.max():.10f}]")
        print(f"  - Original y values before: [{fs.y[indices].min():.3f}, {fs.y[indices].max():.3f}]")

        # Apply based on mode
        if mode == 'additive':
            # Additive: add (offset + modulation) to original values
            # Result: original_value + offset + amplitude*sin(...)
            fs.y[indices] = fs.y[indices] + final_effect_values

            print(f"DEBUG after additive application:")
            print(f"  - New y values: [{fs.y[indices].min():.3f}, {fs.y[indices].max():.3f}]")
        elif mode == 'overwrite':
            # Overwrite: replace values with (offset + modulation)
            # Result: offset + amplitude*sin(...)
            fs.y[indices] = final_effect_values
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