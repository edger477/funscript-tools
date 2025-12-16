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
"""

__version__ = "2.0.1"
__app_name__ = "Restim Funscript Processor"
__description__ = "GUI application for processing funscript files for electrostimulation devices"
__author__ = "Funscript Tools Project"
__url__ = "https://github.com/edger477/funscript-tools"