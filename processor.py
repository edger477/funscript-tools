import os
import shutil
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from funscript import Funscript
from processing.speed_processing import convert_to_speed
from processing.basic_transforms import (
    invert_funscript, map_funscript, limit_funscript,
    normalize_funscript, mirror_up_funscript
)
from processing.combining import combine_funscripts
from processing.special_generators import make_volume_ramp
from processing.funscript_1d_to_2d import generate_alpha_beta_from_main


class RestimProcessor:
    def __init__(self, parameters: Dict[str, Any]):
        self.params = parameters
        self.temp_dir: Optional[Path] = None
        self.input_path: Optional[Path] = None
        self.filename_only: str = ""

    def process(self, input_file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Process the input funscript file and generate all output files.

        Args:
            input_file_path: Path to the input .funscript file
            progress_callback: Optional callback function for progress updates (progress_percent, status_message)

        Returns:
            bool: True if processing completed successfully, False otherwise
        """
        try:
            self._update_progress(progress_callback, 0, "Initializing...")

            # Setup
            self.input_path = Path(input_file_path)
            self.filename_only = self.input_path.stem
            self._setup_directories()

            # Load main funscript
            self._update_progress(progress_callback, 5, "Loading input file...")
            main_funscript = Funscript.from_file(self.input_path)

            # Execute processing pipeline
            self._execute_pipeline(main_funscript, progress_callback)

            # Cleanup if requested
            if self.params['options']['delete_intermediary_files']:
                self._update_progress(progress_callback, 95, "Cleaning up intermediary files...")
                self._cleanup_intermediary_files()

            self._update_progress(progress_callback, 100, "Processing complete!")
            return True

        except Exception as e:
            self._update_progress(progress_callback, -1, f"Error: {str(e)}")
            return False

    def _setup_directories(self):
        """Create the temporary directory for intermediary files."""
        self.temp_dir = self.input_path.parent / "funscript-temp"
        self.temp_dir.mkdir(exist_ok=True)

    def _cleanup_intermediary_files(self):
        """Remove the temporary directory and all its contents."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _update_progress(self, progress_callback: Optional[Callable], percent: int, message: str):
        """Update progress if callback is provided."""
        if progress_callback:
            progress_callback(percent, message)

    def _get_temp_path(self, suffix: str) -> Path:
        """Get path for a temporary file."""
        return self.temp_dir / f"{self.filename_only}.{suffix}.funscript"

    def _get_output_path(self, suffix: str) -> Path:
        """Get path for a final output file."""
        return self.input_path.parent / f"{self.filename_only}.{suffix}.funscript"

    def _copy_if_exists(self, source_suffix: str, dest_suffix: str) -> bool:
        """Copy auxiliary file if it exists."""
        source_path = self.input_path.parent / f"{self.filename_only}.{source_suffix}.funscript"
        if source_path.exists():
            dest_path = self._get_temp_path(dest_suffix)
            shutil.copy2(source_path, dest_path)
            return True
        return False

    def _execute_pipeline(self, main_funscript: Funscript, progress_callback: Optional[Callable]):
        """Execute the complete processing pipeline."""

        # Phase 1: Auxiliary File Preparation (10-20%)
        self._update_progress(progress_callback, 10, "Copying auxiliary files...")

        # Copy existing auxiliary files
        ramp_exists = self._copy_if_exists("ramp", "ramp")
        speed_exists = self._copy_if_exists("speed", "speed")
        alpha_exists = self._copy_if_exists("alpha", "alpha")
        beta_exists = self._copy_if_exists("beta", "beta")

        # Generate alpha and beta files if they don't exist and auto-generation is enabled
        if (not alpha_exists or not beta_exists) and self.params.get('alpha_beta_generation', {}).get('auto_generate', True):
            self._update_progress(progress_callback, 15, "Generating alpha and beta files from main funscript...")
            points_per_second = self.params.get('alpha_beta_generation', {}).get('points_per_second', 25)
            alpha_funscript, beta_funscript = generate_alpha_beta_from_main(main_funscript, points_per_second)

            if not alpha_exists:
                alpha_funscript.save_to_path(self._get_temp_path("alpha"))
                alpha_exists = True

            if not beta_exists:
                beta_funscript.save_to_path(self._get_temp_path("beta"))
                beta_exists = True

        # Phase 2: Core File Generation (20-40%)
        self._update_progress(progress_callback, 20, "Generating speed file...")

        # Generate speed if not provided
        if not speed_exists:
            speed_funscript = convert_to_speed(
                main_funscript,
                self.params['general']['speed_window_size'],
                self.params['speed']['interpolation_interval']
            )
            speed_funscript.save_to_path(self._get_temp_path("speed"))
        else:
            speed_funscript = Funscript.from_file(self._get_temp_path("speed"))

        # Invert speed
        speed_inverted = invert_funscript(speed_funscript)
        speed_inverted.save_to_path(self._get_temp_path("speed_inverted"))

        self._update_progress(progress_callback, 25, "Generating acceleration file...")

        # Generate acceleration from speed
        accel_funscript = convert_to_speed(
            speed_funscript,
            self.params['general']['accel_window_size'],
            self.params['speed']['interpolation_interval']
        )
        accel_funscript.save_to_path(self._get_temp_path("accel"))

        self._update_progress(progress_callback, 30, "Generating volume ramp...")

        # Generate volume ramp if not provided
        if not ramp_exists:
            ramp_funscript = make_volume_ramp(main_funscript)
            ramp_funscript.save_to_path(self._get_temp_path("ramp"))
        else:
            ramp_funscript = Funscript.from_file(self._get_temp_path("ramp"))

        # Invert ramp
        ramp_inverted = invert_funscript(ramp_funscript)
        ramp_inverted.save_to_path(self._get_temp_path("ramp_inverted"))

        # Phase 3: Frequency Processing (40-50%)
        self._update_progress(progress_callback, 40, "Processing frequency data...")

        if alpha_exists:
            alpha_funscript = Funscript.from_file(self._get_temp_path("alpha"))

            # Alpha-based frequency
            alpha_freq = map_funscript(
                alpha_funscript,
                self.params['frequency']['alpha_freq_min'],
                self.params['frequency']['alpha_freq_max']
            )
            alpha_freq.save_to_path(self._get_temp_path("pulse_frequency-alphabased"))

            # Combine with speed
            pulse_frequency = combine_funscripts(
                speed_funscript,
                alpha_freq,
                self.params['frequency']['pulse_frequency_combine_ratio']
            )
            pulse_frequency.save_to_path(self._get_output_path("pulse_frequency"))

            # Alpha inversion for prostate
            alpha_inverted = invert_funscript(alpha_funscript)
            alpha_inverted.save_to_path(self._get_temp_path("alpha_inverted"))
            alpha_inverted.save_to_path(self._get_output_path("alpha-prostate"))

        # Primary frequency generation
        frequency = combine_funscripts(
            ramp_funscript,
            speed_funscript,
            self.params['frequency']['frequency_ramp_combine_ratio']
        )
        frequency.save_to_path(self._get_output_path("frequency"))

        # Phase 4: Volume Processing (50-70%)
        self._update_progress(progress_callback, 50, "Processing volume data...")

        # Standard volume
        volume = combine_funscripts(
            ramp_funscript,
            speed_funscript,
            self.params['volume']['volume_ramp_combine_ratio'],
            self.params['general']['rest_level']
        )

        # Volume normalization
        if self.params['options']['normalize_volume']:
            volume_not_normalized = volume.copy()
            volume_not_normalized.save_to_path(self._get_temp_path("volume_not_normalized"))
            volume = normalize_funscript(volume)

        volume.save_to_path(self._get_output_path("volume"))

        # Prostate volume
        prostate_volume = combine_funscripts(
            ramp_funscript,
            speed_funscript,
            self.params['volume']['volume_ramp_combine_ratio'] * self.params['volume']['prostate_volume_multiplier'],
            self.params['volume']['prostate_rest_level']
        )
        prostate_volume.save_to_path(self._get_output_path("volume-prostate"))

        # Stereostim volume
        stereostim_volume = map_funscript(
            volume,
            self.params['volume']['stereostim_volume_min'],
            self.params['volume']['stereostim_volume_max']
        )
        stereostim_volume.save_to_path(self._get_output_path("volume-stereostim"))

        # Phase 5: Pulse Parameters (70-90%)
        self._update_progress(progress_callback, 70, "Processing pulse parameters...")

        if beta_exists:
            beta_funscript = Funscript.from_file(self._get_temp_path("beta"))

            # Beta mirror-up
            beta_mirrored = mirror_up_funscript(
                beta_funscript,
                self.params['pulse']['beta_mirror_threshold']
            )
            beta_mirrored.save_to_path(self._get_temp_path("beta-mirror-up"))

            # Pulse rise time (complex combination)
            pulse_rise_time = combine_funscripts(
                beta_mirrored,
                speed_inverted,
                self.params['pulse']['pulse_rise_combine_ratio']
            )
            pulse_rise_time = combine_funscripts(
                ramp_inverted,
                pulse_rise_time,
                self.params['pulse']['pulse_rise_combine_ratio']
            )
            pulse_rise_time = map_funscript(
                pulse_rise_time,
                self.params['pulse']['pulse_rise_min'],
                self.params['pulse']['pulse_rise_max']
            )
            pulse_rise_time.save_to_path(self._get_output_path("pulse_rise_time"))

        if alpha_exists:
            # Pulse width from limited inverted alpha
            pulse_width_alpha = limit_funscript(
                alpha_inverted,
                self.params['pulse']['pulse_width_min'],
                self.params['pulse']['pulse_width_max']
            )
            pulse_width_alpha.save_to_path(self._get_temp_path("pulse_width-alpha"))

            # Combine with speed for final pulse width
            pulse_width = combine_funscripts(
                speed_funscript,
                pulse_width_alpha,
                self.params['pulse']['pulse_width_combine_ratio']
            )
            pulse_width.save_to_path(self._get_output_path("pulse_width"))

        # Phase 6: Copy remaining outputs (90-95%)
        self._update_progress(progress_callback, 90, "Finalizing outputs...")

        # Copy alpha and beta to outputs if they exist
        if alpha_exists:
            shutil.copy2(self._get_temp_path("alpha"), self._get_output_path("alpha"))
        if beta_exists:
            shutil.copy2(self._get_temp_path("beta"), self._get_output_path("beta"))

        # Generate optional inverted files if enabled
        if self.params['advanced']['enable_pulse_frequency_inversion'] and alpha_exists:
            pulse_freq_inverted = invert_funscript(pulse_frequency)
            pulse_freq_inverted.save_to_path(self._get_output_path("pulse_frequency_inverted"))

        if self.params['advanced']['enable_volume_inversion']:
            volume_inverted = invert_funscript(volume)
            volume_inverted.save_to_path(self._get_output_path("volume_inverted"))

        if self.params['advanced']['enable_frequency_inversion']:
            freq_inverted = invert_funscript(frequency)
            freq_inverted.save_to_path(self._get_output_path("frequency_inverted"))