"""
Version information for Restim Funscript Processor
1.0.2 - fixed ramp calculation bug
1.0.3 - added motion axis generation (E1-E4)
1.0.4 - fixed output folder config; added option to not generate prostate files
1.0.5 - added batch processing and zip packaging features
1.0.6 - speed threshold redesign (Hz to %), global center algorithm for alpha/beta
1.0.7 - change allowed range for volume ratio (combine of speed and ramp)
1.0.8 - add restim-original algorithm with random direction changes to motion axis generation
1.1.0 - add custom events system with YAML-based event definitions, configurable axis normalization, and volume headroom control
2.0.0 - major custom events upgrade: visual timeline editor with event library, parameter editing UI with real-time preview,
        file management modes (Local/Central with backups), additional waveforms (square/triangle/sawtooth with duty cycle),
        formalized event groups, max_level_offset API for intuitive peak control
2.0.1 - bugfixes:
        1. Direction change probability saved/loaded correctly
        2. Convert to 2D button working in Motion Axis tab
        3. Auto-generate option replaced with overwrite option
        4. Smart overwrite behavior implemented
        5. Prostate generation checkbox working correctly
2.0.2 - improvements and bugfixes:
        1. Added comprehensive metadata to all generated funscript files (generator, version, algorithms, parameters)
        2. Added rest level ramp-up feature with centered transition window for smooth volume recovery
        3. Fixed file overwrite issue in central folder mode (files now properly updated when backups disabled)
        4. Replaced automatic linked axes with explicit comma-separated axis targeting (e.g., "volume,volume-prostate")
        5. Removed volume-stereostim file generation and related parameters
        6. Added validation warning for modulation frequencies >30 Hz (potential undersampling)
2.0.3 - custom events system improvements and critical bugfixes:
        1. Auto-create empty .events.yml template next to source .funscript files during processing
        2. Auto-load .events.yml file when opening Custom Event Builder after processing
        3. Fixed Custom Event Builder saving modified files to wrong directory in central folder mode
        4. Fixed .events.yml files to always stay in local/source directory (not moved to central folder)
        5. Fixed critical overwrite mode ramp bug: ramps now blend from/to current values instead of dropping to 0
        6. Added dirty flag tracking with "Save and Apply Effects" button text when changes are unsaved
        7. Fixed beta-prostate file not being generated/copied to output in tear-shaped and other prostate modes
2.0.4 - code cleanup:
        1. Removed legacy funscript_1d_to_2d.py file that was causing import confusion
        2. Fixed prostate_2d.py to use correct function parameters (removed invalid speed_at_edge_hz parameter)
2.0.5 - external config loading improvement:
        1. Fixed event definitions loading to check exe directory first before bundled resources
        2. Users can now edit config.event_definitions.yml next to the exe to add custom events without rebuilding
        3. Added get_resource_path() helper function for proper PyInstaller resource resolution
2.0.6 - UI window size improvements:
        1. Main window default height reduced from 1000px to 760px for better fit on smaller screens
        2. Custom Events Builder default height reduced from 950px to 900px
        3. Added dynamic scrollbars to Custom Events Builder (appears when resized below 1000x880)
        4. Fixed scrollbar positioning to cover full content area in Custom Events Builder
2.0.7 - phase-shifted funscript generation and pulse frequency workflow refactor:
        1. Added phase-shifted output generation (*-2.funscript files) with variable delay based on local stroke cycle
        2. New phase shift controls in Motion Axis tab (enable checkbox and delay percentage, default 10%)
        3. Phase shift supports both legacy (alpha/beta) and motion axis (e1-e4) modes
        4. Refactored pulse frequency generation to use alpha funscript instead of main funscript
        5. Moved pulse frequency min/max mapping to final output step for proper bounds guarantee
        6. Removed intermediate pulse_frequency-mainbased.funscript file
2.0.8 - Python 3.13 compatibility and drag-and-drop support:
        1. Added drag-and-drop support for .funscript files (drop files onto window instead of using Browse)
        2. Updated tkinter trace API for Python 3.13 compatibility (.trace('w') -> .trace_add('write'))
        3. Added tkinterdnd2 dependency for cross-platform drag-and-drop
2.0.9 - UI compactness improvements:
        1. Reduced main window default height from 760px to 735px
        2. Motion Axis tab: Combined mode label and radio buttons into single row
        3. Motion Axis tab: Removed redundant title, combined phase shift controls into single row with tooltip
        4. Basic tab: Arranged algorithm radio buttons in 2x2 grid instead of 4 rows
        5. General tab: Combined processing options into 2-column layout, removed redundant section title
        6. Fixed bottom margin to match left/right margins
2.1.0 - Motion Axis tab split and bugfixes:
        1. Split Motion Axis tab into Motion Axis (3P) and Motion Axis (4P) independent tabs
        2. Each tab has its own "Generate motion scripts" and "Generate phase-shifted versions" checkboxes
        3. 3P and 4P script generation can now be enabled/disabled independently
        4. Each tab has independent phase-shift delay settings
        5. Fixed matplotlib not being installed during Windows build (added to requirements.txt and PyInstaller hidden imports)
        6. Fixed E1-E4 files not being copied to output after generation (missing filename_base in generate_motion_axes call)
2.1.1 - Custom events bugfixes and new event definitions:
        1. Fixed normalization bug: negative values on axes with max > 1.0 (e.g. pulse_frequency) now correctly divided by max instead of passed through as-is
        2. Added step validation in event processor: clear errors for missing 'operation', 'axis', or 'start_value' fields (including hint to use apply_modulation)
        3. Improved error reporting in Custom Event Builder: full traceback shown for unexpected errors
        4. Added new event definitions: cum, stay, medium, fast, edge (General group)
        5. Updated config defaults: algorithm, interpolation interval, pulse_freq_min, overwrite behavior
2.2.0 - Tuned event definition defaults and config:
        1. Tuned default params for cum event: buzz_intensity 0.05→0.07, volume_boost 0.05→0.10
        2. Tuned default params for stay event: buzz_freq 10→15, buzz_intensity 0.02→0.03, volume_boost 0.01→0.05
        3. Tuned default params for medium event: buzz_freq 30→10, volume_boost 0.05→0.10, ramp_up_ms 250→500
        4. Tuned clutch_tantalize: volume_boost 0.05→0.03; fixed clutch_tranquil volume axis and start/end values
        5. Updated config default interpolation_interval 0.05→0.02 for higher resolution processing
2.2.1 - Central folder bugfixes and zip output feature:
        1. Fixed "Process Motion Files" ignoring central folder setting (files went to source folder instead)
        2. Fixed same central folder bug in 3P conversion path (_perform_2d_conversion)
        3. Added zip output option in central mode: packs all output funscripts into a single .zip file
        4. Zip output cleans up old .zip on re-process (when backups disabled)
        5. Fixed Custom Event Builder: fractional frequencies (e.g. buzz_freq: 1.5) now use float spinbox
        6. Further tuned event defaults: cum buzz_intensity 0.07→0.1, volume_boost 0.1→0.2; stay buzz_intensity 0.03→0.05, volume_boost 0.05→0.1; edge buzz_intensity 0.1→0.07, volume_boost 0.1→0.15
        7. Fixed slow event: separated alpha linear offset from modulation (was using max_level_offset for offset bias)
        8. Changed medium and fast stroke_offset default 0.1→0 (center-aligned strokes)
"""

__version__ = "2.2.1"
__app_name__ = "Restim Funscript Processor"
__description__ = "GUI application for processing funscript files for electrostimulation devices"
__author__ = "Funscript Tools Project"
__url__ = "https://github.com/edger477/funscript-tools"