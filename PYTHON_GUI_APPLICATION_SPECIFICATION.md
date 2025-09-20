# Python GUI Application Specification for Restim Funscript Processing

## Overview
This specification describes a Python GUI application that replaces the PowerShell-based funscript processing workflow with a user-friendly interface for generating electrostimulation device scripts. The application includes automatic 1D to 2D funscript conversion to ensure complete processing without requiring auxiliary files.

## Application Architecture

### Technology Stack
- **GUI Framework**: Tkinter (built-in) or PyQt5/PySide2 for more advanced UI
- **File Processing**: Existing funscript module + integrated processing functions
- **File Management**: pathlib for cross-platform path handling
- **Configuration**: JSON-based parameter persistence
- **1D to 2D Conversion**: Radial conversion algorithm for alpha/beta generation

### Main Application Structure
```
restim_funscript_processor/
├── main.py                    # Main GUI application
├── processor.py               # Core processing workflow
├── funscript/                 # Existing funscript module
│   └── funscript.py
├── processing/                # Individual processing functions
│   ├── __init__.py
│   ├── speed_processing.py
│   ├── basic_transforms.py    # Invert, map, limit, normalize, mirror
│   ├── combining.py
│   ├── special_generators.py  # Volume ramp generation
│   └── funscript_1d_to_2d.py  # Alpha/beta auto-generation
├── ui/                        # UI components
│   ├── __init__.py
│   ├── main_window.py
│   ├── parameter_tabs.py
│   └── progress_dialog.py
└── config.json               # Default parameters
```

## User Interface Specification

### Main Window Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Restim Funscript Processor                                  │
├─────────────────────────────────────────────────────────────┤
│ Input File: [________________________] [Browse...]         │
│                                                             │
│ ┌─── Processing Options ─────────────────────────────────┐ │
│ │ ☐ Normalize Volume                                     │ │
│ │ ☐ Delete Intermediary Files When Done                 │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─── Parameters ─────────────────────────────────────────┐ │
│ │ [General] [Speed] [Frequency] [Volume] [Pulse] [Advanced] │
│ │ ┌─ General ─────────────────────────────────────────────┐ │
│ │ │ Rest Level: [0.4    ] (0.0-1.0)                     │ │
│ │ │ Speed Window (sec): [5     ] (1-30)                 │ │
│ │ │ Accel Window (sec): [3     ] (1-10)                 │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─── Output Status ──────────────────────────────────────┐ │
│ │ Ready to process...                                    │ │
│ │ [Process Files]                    [Save Config]       │ │
│ └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Parameter Tabs

#### General Tab
- **Rest Level**: Float (0.0-1.0, default: 0.4) - Signal level when volume ramp or speed is 0
- **Speed Window Size**: Integer (1-30 seconds, default: 5) - Window for speed calculation
- **Acceleration Window Size**: Integer (1-10 seconds, default: 3) - Window for acceleration calculation

#### Speed Tab
- **Speed Interpolation Interval**: Float (0.01-1.0 seconds, default: 0.1) - Interpolation granularity
- **Speed Normalization Method**: Dropdown ["Max normalization", "RMS normalization"] (default: Max)
- **Auto-generate Alpha/Beta**: Checkbox (default: checked) - Automatically create alpha/beta files when missing
- **Alpha/Beta Points Per Second**: Integer (1-100, default: 25) - Interpolation density for 1D to 2D conversion

#### Frequency Tab
- **Alpha Frequency Min**: Float (0.0-1.0, default: 0.30) - Minimum mapping for alpha to pulse frequency
- **Alpha Frequency Max**: Float (0.0-1.0, default: 0.95) - Maximum mapping for alpha to pulse frequency
- **Frequency Ramp Combine Ratio**: Integer (1-10, default: 2) - Ratio for combining frequency and ramp
- **Pulse Frequency Combine Ratio**: Integer (1-10, default: 3) - Ratio for combining speed with alpha-based frequency

#### Volume Tab
- **Volume Ramp Combine Ratio**: Float (1.0-10.0, default: 6.0) - Ratio for combining volume and ramp
- **Prostate Volume Multiplier**: Float (1.0-3.0, default: 1.5) - Multiplier for prostate volume ratio
- **Prostate Volume Rest Level**: Float (0.0-1.0, default: 0.7) - Rest level for prostate volume
- **Stereostim Volume Min**: Float (0.0-1.0, default: 0.50) - Minimum mapping for stereostim volume
- **Stereostim Volume Max**: Float (0.0-1.0, default: 1.00) - Maximum mapping for stereostim volume

#### Pulse Tab
- **Pulse Width Limit Min**: Float (0.0-1.0, default: 0.1) - Minimum limit for pulse width
- **Pulse Width Limit Max**: Float (0.0-1.0, default: 0.45) - Maximum limit for pulse width
- **Pulse Width Combine Ratio**: Integer (1-10, default: 3) - Ratio for combining pulse width components
- **Beta Mirror Threshold**: Float (0.0-0.5, default: 0.5) - Threshold for beta mirroring
- **Pulse Rise Time Min**: Float (0.0-1.0, default: 0.00) - Minimum mapping for pulse rise time
- **Pulse Rise Time Max**: Float (0.0-1.0, default: 0.80) - Maximum mapping for pulse rise time
- **Pulse Rise Combine Ratio**: Integer (1-10, default: 2) - Ratio for pulse rise time combining

#### Advanced Tab
- **Enable Pulse Frequency Inversion**: Checkbox (default: unchecked) - Generate inverted pulse frequency
- **Enable Volume Inversion**: Checkbox (default: unchecked) - Generate inverted volume
- **Enable Frequency Inversion**: Checkbox (default: unchecked) - Generate inverted frequency
- **Custom Output Directory**: Text field + Browse button (optional override)

## Processing Workflow

### Core Processing Class
```python
class RestimProcessor:
    def __init__(self, parameters):
        self.params = parameters
        self.temp_dir = None
        self.input_path = None

    def process(self, input_file_path, progress_callback=None):
        # Setup directories
        # Execute processing pipeline
        # Cleanup if requested

    def setup_directories(self):
        # Create funscript-temp subdirectory

    def execute_pipeline(self, progress_callback):
        # Run all processing steps with progress updates

    def cleanup_intermediary_files(self):
        # Remove temp directory if option selected
```

### Processing Pipeline Steps

#### Phase 1: File Preparation
1. **Validate input file** - Check JSON format and structure
2. **Setup directories** - Create `funscript-temp` subdirectory
3. **Copy auxiliary files** (if they exist):
   - `{filename}.ramp.funscript`
   - `{filename}.speed.funscript`
   - `{filename}.alpha.funscript`
   - `{filename}.beta.funscript`
4. **Auto-generate missing alpha/beta files** (if enabled):
   - Convert main funscript to 2D using radial conversion algorithm
   - Parameters: `points_per_second` for interpolation density
   - Creates smooth semicircular motions between consecutive points

#### Phase 2: Core File Generation
1. **Generate speed file** (if not provided):
   - Convert main funscript to speed using windowed calculation
   - Parameters: `speed_window_size`
   - Invert speed values
2. **Generate acceleration file**:
   - Convert speed to acceleration
   - Parameters: `accel_window_size`
3. **Generate volume ramp** (if not provided):
   - Create 4-point ramp pattern

#### Phase 3: Frequency Processing
1. **Alpha-based frequency**:
   - Map alpha to frequency range
   - Parameters: `alpha_freq_min`, `alpha_freq_max`
   - Combine with speed using `pulse_frequency_combine_ratio`
2. **Primary frequency**:
   - Combine ramp and speed
   - Parameters: `frequency_ramp_combine_ratio`

#### Phase 4: Volume Processing
1. **Standard volume**:
   - Combine ramp and speed
   - Parameters: `volume_ramp_combine_ratio`, `rest_level`
2. **Prostate volume**:
   - Enhanced ratio calculation
   - Parameters: `prostate_volume_multiplier`, `prostate_rest_level`
3. **Volume normalization** (if enabled):
   - Apply normalization to maximize range
4. **Stereostim volume**:
   - Map to specified range
   - Parameters: `stereostim_volume_min`, `stereostim_volume_max`

#### Phase 5: Pulse Parameters
1. **Alpha processing**:
   - Generate inverted alpha for prostate
2. **Beta processing**:
   - Apply mirror-up transformation
   - Parameters: `beta_mirror_threshold`
3. **Pulse width**:
   - Limit inverted alpha to range
   - Parameters: `pulse_width_min`, `pulse_width_max`, `pulse_width_combine_ratio`
4. **Pulse rise time**:
   - Complex combination of multiple signals
   - Parameters: `pulse_rise_min`, `pulse_rise_max`, `pulse_rise_combine_ratio`

#### Phase 6: Optional Inversions
Generate additional inverted files if enabled in Advanced tab:
- Pulse frequency inverted
- Volume inverted
- Frequency inverted

## File Management

### Directory Structure
```
/path/to/video.funscript              # Input file
/path/to/funscript-temp/              # Intermediary files directory
├── video.speed.funscript
├── video.accel.funscript
├── video.ramp.funscript
├── video.pulse_frequency-alphabased.funscript
├── video.alpha_inverted.funscript
├── video.speed_inverted.funscript
├── video.ramp_inverted.funscript
├── video.beta-mirror-up.funscript
├── video.pulse_width-alpha.funscript
├── video.volume_normalized.funscript
└── video.volume_not_normalized.funscript

/path/to/video.alpha.funscript         # Final outputs (10 files)
/path/to/video.alpha-prostate.funscript
/path/to/video.beta.funscript
/path/to/video.frequency.funscript
/path/to/video.pulse_frequency.funscript
/path/to/video.pulse_rise_time.funscript
/path/to/video.pulse_width.funscript
/path/to/video.volume.funscript
/path/to/video.volume-prostate.funscript
/path/to/video.volume-stereostim.funscript
```

### File Operations
- **Intermediary files**: Generated in `funscript-temp` subdirectory
- **Final outputs**: Placed in same directory as input file
- **Cleanup option**: Remove `funscript-temp` directory when processing complete
- **Overwrite protection**: Prompt user before overwriting existing final output files

## Configuration Management

### Parameter Persistence
- **Default config**: `config.json` with factory defaults
- **User config**: Saved automatically when "Save Config" clicked
- **Config location**: Same directory as application executable
- **Parameter validation**: Range checking and type validation on load

### Default Configuration
```json
{
  "general": {
    "rest_level": 0.4,
    "speed_window_size": 5,
    "accel_window_size": 3
  },
  "speed": {
    "interpolation_interval": 0.1,
    "normalization_method": "max"
  },
  "alpha_beta_generation": {
    "auto_generate": true,
    "points_per_second": 25
  },
  "frequency": {
    "alpha_freq_min": 0.30,
    "alpha_freq_max": 0.95,
    "frequency_ramp_combine_ratio": 2,
    "pulse_frequency_combine_ratio": 3
  },
  "volume": {
    "volume_ramp_combine_ratio": 6.0,
    "prostate_volume_multiplier": 1.5,
    "prostate_rest_level": 0.7,
    "stereostim_volume_min": 0.50,
    "stereostim_volume_max": 1.00
  },
  "pulse": {
    "pulse_width_min": 0.1,
    "pulse_width_max": 0.45,
    "pulse_width_combine_ratio": 3,
    "beta_mirror_threshold": 0.5,
    "pulse_rise_min": 0.00,
    "pulse_rise_max": 0.80,
    "pulse_rise_combine_ratio": 2
  },
  "advanced": {
    "enable_pulse_frequency_inversion": false,
    "enable_volume_inversion": false,
    "enable_frequency_inversion": false,
    "custom_output_directory": ""
  },
  "options": {
    "normalize_volume": true,
    "delete_intermediary_files": true
  }
}
```

## Error Handling

### Validation
- **Input file validation**: JSON structure, required fields, data types
- **Parameter validation**: Range checking, type validation
- **File system validation**: Write permissions, disk space
- **Dependency validation**: Required auxiliary files if referenced

### User Feedback
- **Progress bar**: Real-time processing progress (0-100%)
- **Status messages**: Current operation being performed
- **Error dialogs**: Clear error messages with suggested solutions
- **Warnings**: Non-fatal issues (missing auxiliary files, etc.)

### Recovery
- **Partial completion**: Continue processing if non-critical steps fail
- **Rollback**: Clean up partial outputs on critical failure
- **Resume capability**: Skip already-completed files if reprocessing

## Performance Considerations

### Optimization
- **Caching**: Reuse existing funscript cache from original module
- **Parallel processing**: Process independent operations concurrently
- **Memory management**: Stream large files rather than loading entirely
- **Progress tracking**: Granular progress updates for user feedback

### Scalability
- **Large files**: Handle funscripts with 100K+ actions efficiently
- **Batch processing**: Future extension for multiple file processing
- **Threading**: UI responsiveness during long processing operations

## 1D to 2D Conversion Algorithm

### Radial Conversion Method
The application includes an automatic 1D to 2D conversion system that generates alpha (x-axis) and beta (y-axis) funscripts from a single main funscript:

```python
def convert_funscript_radial(funscript, points_per_second=25):
    """
    Convert 1D funscript to 2D using radial conversion.

    For each consecutive pair of points:
    1. Calculate time segment duration
    2. Generate interpolated points at specified density
    3. Create semicircular motion using parametric equations:
       - center = (start_pos + end_pos) / 2
       - radius = (start_pos - end_pos) / 2
       - x(θ) = center + radius * cos(θ)  # Alpha channel
       - y(θ) = radius * sin(θ) + 0.5     # Beta channel
       - θ ranges from 0 to π
    """
```

### Benefits
- **Complete Processing**: Ensures all 10 output files are generated even with minimal input
- **Smooth Motion**: Creates natural 2D movement patterns from 1D data
- **Configurable Quality**: User-adjustable interpolation density
- **Automatic Fallback**: Only generates when alpha/beta files are missing

## Implementation Priority

### Phase 1: Core Functionality ✅ COMPLETED
1. Basic GUI with file browser and process button
2. Core processing pipeline (single-threaded)
3. Essential parameter controls
4. Basic error handling
5. 1D to 2D conversion integration

### Phase 2: Enhanced UI ✅ COMPLETED
1. Tabbed parameter interface
2. Progress tracking and status updates
3. Configuration save/load
4. Input validation
5. Alpha/beta generation controls

### Phase 3: Advanced Features ✅ COMPLETED
1. Advanced parameter controls
2. Optional inversion files
3. Automatic file management
4. Performance optimizations

### Phase 4: Polish ✅ COMPLETED
1. Comprehensive error handling
2. User experience improvements
3. Documentation and help system
4. Complete test coverage