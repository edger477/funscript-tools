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
"""

__version__ = "2.0.9"
__app_name__ = "Restim Funscript Processor"
__description__ = "GUI application for processing funscript files for electrostimulation devices"
__author__ = "Funscript Tools Project"
__url__ = "https://github.com/edger477/funscript-tools"