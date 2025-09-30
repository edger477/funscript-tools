# Python GUI Application Specification for Restim Funscript Processing

## Overview
This specification describes a Python GUI application that replaces the PowerShell-based funscript processing workflow with a user-friendly interface for generating electrostimulation device scripts. The application includes both traditional alpha/beta generation and the new Motion Axis Generation system for positional control.

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
│   ├── funscript_1d_to_2d.py  # Alpha/beta auto-generation
│   ├── motion_axis_generation.py  # Motion axis (E1-E4) generation
│   └── linear_mapping.py      # Linear interpolation for motion axes
├── ui/                        # UI components
│   ├── __init__.py
│   ├── main_window.py
│   ├── parameter_tabs.py
│   ├── positional_axes_tab.py     # Motion axis and legacy alpha/beta controls
│   ├── curve_widgets.py           # Matplotlib chart components
│   ├── curve_editor_dialog.py     # Modal curve editor for motion axes
│   └── progress_dialog.py
└── config.json               # Default parameters
```

## User Interface Specification

### Main Window Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Restim Funscript Processor                       (800x950)  │
├─────────────────────────────────────────────────────────────┤
│ Input File: [________________________] [Browse...]         │
│                                                             │
│ ┌─── Parameters ─────────────────────────────────────────┐ │
│ │ [General] [Speed] [Frequency] [Volume] [Pulse] [Motion Axis] [Advanced] │
│ │ ┌─ General ─────────────────────────────────────────────┐ │
│ │ │ Rest Level: [0.4    ] (0.0-1.0)                      │ │
│ │ │ Speed Window Size: [5] (1-30 seconds)               │ │
│ │ │ Acceleration Window Size: [3] (1-10 seconds)        │ │
│ │ │ ── Processing Options ──                             │ │
│ │ │ ☑ Normalize Volume                                   │ │
│ │ │ ☑ Delete Intermediary Files When Done               │ │
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
- **Processing Options**:
  - **Normalize Volume**: Checkbox (default: checked) - Apply volume normalization
  - **Delete Intermediary Files**: Checkbox (default: checked) - Remove temp files when processing complete

#### Motion Axis Tab
**Generation Mode Selection**: Radio buttons for choosing positional axis generation method

##### Legacy (Alpha/Beta) Mode
When Legacy mode is selected, the tab displays embedded 1D to 2D conversion controls:
- **Basic Tab**: Standard conversion algorithms
  - Algorithm: Circular, Top-Left-Right, Top-Right-Left
  - Points Per Second: Integer (1-100, default: 25)
  - Min Distance From Center: Float (0.1-0.9, default: 0.1)
  - Speed at Edge (Hz): Float (1.0-5.0, default: 2.0)
- **Prostate Tab**: Specialized prostate conversion
  - Generate from inverted: Checkbox (default: checked)
  - Algorithm: Standard, Tear-shaped
  - Min Distance From Center: Float (0.3-0.9, default: 0.5)

##### Motion Axis Mode
When Motion Axis mode is selected, the tab displays axis configuration controls:
- **Axis Configuration Panels**: Four panels for E1-E4 axes, each containing:
  - **Enable Checkbox**: Individual axis on/off control
  - **Curve Name Display**: Shows current curve type (Linear, Ease In, etc.)
  - **Matplotlib Preview Chart**: Visual representation of the response curve (500x100 pixels)
  - **Edit Curve Button**: Opens modal dialog for curve editing (future implementation)
- **Real-time Curve Visualization**: Each chart shows actual input→output mapping (0-100 coordinate system)
- **Mathematical Accuracy**: Charts use the same linear interpolation function as the processing pipeline

#### Speed Tab
- **Speed Interpolation Interval**: Float (0.01-1.0 seconds, default: 0.1) - Interpolation granularity
- **Speed Normalization Method**: Dropdown ["Max normalization", "RMS normalization"] (default: Max)

#### Frequency Tab
- **Pulse Frequency Min**: Float (0.0-1.0, default: 0.40) - Minimum mapping for main funscript to pulse frequency
- **Pulse Frequency Max**: Float (0.0-1.0, default: 0.95) - Maximum mapping for main funscript to pulse frequency
- **Frequency Ramp Combine Ratio**: Integer (1-10, default: 2) - Ratio for combining frequency and ramp
- **Pulse Frequency Combine Ratio**: Integer (1-10, default: 3) - Ratio for combining speed with main-based frequency

#### Volume Tab
- **Volume Ramp Combine Ratio**: Float (1.0-10.0, default: 6.0) - Ratio for combining volume and ramp
- **Prostate Volume Multiplier**: Float (1.0-3.0, default: 1.5) - Multiplier for prostate volume ratio
- **Prostate Volume Rest Level**: Float (0.0-1.0, default: 0.7) - Rest level for prostate volume
- **Stereostim Volume Min**: Float (0.0-1.0, default: 0.50) - Minimum mapping for stereostim volume
- **Stereostim Volume Max**: Float (0.0-1.0, default: 1.00) - Maximum mapping for stereostim volume
- **Ramp (% per hour)**: Integer (0-40%, default: 15%) - Volume ramp progression rate with real-time current value and per-minute display

#### Pulse Tab
- **Pulse Width Limit Min**: Float (0.0-1.0, default: 0.1) - Minimum limit for pulse width
- **Pulse Width Limit Max**: Float (0.0-1.0, default: 0.45) - Maximum limit for pulse width
- **Pulse Width Combine Ratio**: Integer (1-10, default: 3) - Ratio for combining pulse width components
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
   - Create 4-point ramp pattern using percentage-based progression
   - Second point fixed at 10 seconds with calculated value based on ramp percentage
   - Formula: `ramp_value = 1.0 - (duration_seconds * ramp_per_second)`

#### Phase 3: Frequency Processing
1. **Pulse frequency generation**:
   - Map main funscript to frequency range
   - Parameters: `pulse_freq_min`, `pulse_freq_max`
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
1. **Alpha-prostate generation**:
   - Generate inverted main funscript for prostate output
2. **Pulse width**:
   - Limit inverted main funscript to range
   - Parameters: `pulse_width_min`, `pulse_width_max`, `pulse_width_combine_ratio`
3. **Pulse rise time**:
   - Combine ramp_inverted and speed_inverted directly
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
├── video.speed_inverted.funscript
├── video.accel.funscript
├── video.ramp.funscript
├── video.ramp_inverted.funscript
├── video.pulse_frequency-mainbased.funscript
├── video.pulse_width-main.funscript
├── video.volume_normalized.funscript (if normalization enabled)
└── video.volume_not_normalized.funscript (if normalization enabled)

# Legacy Mode Outputs (8 core files + optional alpha/beta)
/path/to/video.frequency.funscript
/path/to/video.pulse_frequency.funscript
/path/to/video.pulse_rise_time.funscript
/path/to/video.pulse_width.funscript
/path/to/video.volume.funscript
/path/to/video.volume-prostate.funscript
/path/to/video.volume-stereostim.funscript
/path/to/video.alpha-prostate.funscript
# Optional if alpha/beta files exist or auto-generated:
/path/to/video.alpha.funscript
/path/to/video.beta.funscript

# Motion Axis Mode Outputs (8 core files + E-axes)
/path/to/video.frequency.funscript
/path/to/video.pulse_frequency.funscript
/path/to/video.pulse_rise_time.funscript
/path/to/video.pulse_width.funscript
/path/to/video.volume.funscript
/path/to/video.volume-prostate.funscript
/path/to/video.volume-stereostim.funscript
/path/to/video.alpha-prostate.funscript
/path/to/video.e1.funscript
/path/to/video.e2.funscript
/path/to/video.e3.funscript
/path/to/video.e4.funscript (if enabled)
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
  "positional_axes": {
    "mode": "legacy",
    "legacy_config": {
      "auto_generate": true,
      "points_per_second": 25,
      "algorithm": "circular",
      "min_distance_from_center": 0.1,
      "speed_at_edge_hz": 2.0
    },
    "prostate_generation": {
      "generate_from_inverted": true,
      "algorithm": "standard",
      "points_per_second": 25,
      "min_distance_from_center": 0.5
    },
    "motion_axis_config": {
      "algorithm": "linear_mapping",
      "axis_configs": [
        {
          "name": "E1",
          "enabled": true,
          "control_points": [[0, 0], [100, 100]]
        },
        {
          "name": "E2",
          "enabled": true,
          "control_points": [[0, 0], [50, 100], [100, 0]]
        },
        {
          "name": "E3",
          "enabled": true,
          "control_points": [[0, 100], [100, 0]]
        },
        {
          "name": "E4",
          "enabled": false,
          "control_points": [[0, 75], [100, 50]]
        }
      ]
    }
  },
  "frequency": {
    "pulse_freq_min": 0.40,
    "pulse_freq_max": 0.95,
    "frequency_ramp_combine_ratio": 2,
    "pulse_frequency_combine_ratio": 3
  },
  "volume": {
    "volume_ramp_combine_ratio": 6.0,
    "prostate_volume_multiplier": 1.5,
    "prostate_rest_level": 0.7,
    "stereostim_volume_min": 0.50,
    "stereostim_volume_max": 1.00,
    "ramp_percent_per_hour": 15
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

## Motion Axis Generation System

### Overview
The Motion Axis Generation system provides an alternative to traditional alpha/beta generation through configurable response curves. When enabled, it replaces alpha/beta processing with a system that generates 3-4 independent motion axes (E1-E4) using linear interpolation mapping.

### Core Concept
- **Input**: Original funscript values (0-100)
- **Processing**: Linear interpolation through user-defined control points
- **Output**: Transformed motion axes as `filename.e1.funscript` through `filename.e4.funscript`

### Mathematical Foundation

#### Linear Mapping Algorithm
```python
def linear_interpolate(input_value, control_points):
    """
    Apply linear interpolation mapping to transform input values.

    Args:
        input_value: 0-100 from original funscript
        control_points: [(input, output), ...] sorted by input value

    Returns:
        0-100 output value for motion axis
    """
    # Find bracketing control points
    for i in range(len(control_points) - 1):
        x1, y1 = control_points[i]
        x2, y2 = control_points[i + 1]

        if x1 <= input_value <= x2:
            # Linear interpolation between points
            ratio = (input_value - x1) / (x2 - x1)
            return y1 + ratio * (y2 - y1)

    return control_points[-1][1]  # Edge case handling
```

#### Response Curve Configuration
Each motion axis (E1-E4) is defined by a set of control points that create a response curve:
- **Control Points**: Array of (input, output) coordinates
- **Mandatory Endpoints**: First point must have input=0, last point must have input=100
- **Interpolation**: Linear interpolation between consecutive points
- **Validation**: Points sorted by input value, no duplicate inputs, values within 0-100 range

### Default Axis Configurations

#### E1 - Linear Response
- **Control Points**: `[(0.0, 0.0), (1.0, 1.0)]`
- **Behavior**: Direct 1:1 mapping (identity function)
- **Use Case**: Baseline motion, direct position mapping

#### E2 - Ease In Response
- **Control Points**: `[(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)]`
- **Behavior**: Gradual start, strong finish
- **Use Case**: Smooth acceleration patterns

#### E3 - Ease Out Response
- **Control Points**: `[(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)]`
- **Behavior**: Strong start, gradual finish
- **Use Case**: Smooth deceleration patterns

#### E4 - Bell Curve Response
- **Control Points**: `[(0.0, 0.0), (0.25, 0.3), (0.5, 1.0), (0.75, 0.3), (1.0, 0.0)]`
- **Behavior**: Emphasis on middle range, returns to zero at edges
- **Use Case**: Mid-range emphasis patterns

### User Interface Components

#### Motion Axis Tab Integration
- **Mode Selection**: Radio buttons for "Legacy (Alpha/Beta)" vs "Motion Axis (E1-E4)"
- **Dynamic Content**: Tab content switches based on selected mode
  - **Legacy Mode**: Shows embedded 1D to 2D conversion tabs (Basic + Prostate)
  - **Motion Axis Mode**: Shows axis configuration panels with matplotlib charts
- **Embedded Conversion Controls**: Full ConversionTabs functionality within Motion Axis tab
- **Real-time Mode Switching**: Immediate UI updates when mode selection changes

#### Current Implementation Status
- **Matplotlib Integration**: ✅ Working curve visualization with 5:1 aspect ratio
- **Real-time Updates**: ✅ Charts update when configuration changes
- **Mathematical Accuracy**: ✅ Uses actual processing pipeline functions
- **Modal Curve Editor**: 🚧 Planned for future implementation
- **Interactive Point Editing**: 🚧 Planned for future implementation

#### Curve Presets
```python
CURVE_PRESETS = {
    "linear": [(0,0), (100,100)],
    "inverted": [(0,100), (100,0)],
    "triangle": [(0,0), (50,100), (100,0)],
    "bell": [(0,0), (25,50), (50,100), (75,50), (100,0)],
    "flat_low": [(0,0), (100,0)],
    "flat_high": [(0,100), (100,100)],
    "step_up": [(0,0), (49,0), (51,100), (100,100)],
    "s_curve": [(0,0), (25,10), (75,90), (100,100)]
}
```

### Processing Integration

#### Pipeline Routing
```python
def _execute_pipeline(self, main_funscript, progress_callback):
    # Check positional axis mode
    if self.params['positional_axes']['mode'] == 'motion_axis':
        self._generate_motion_axes(main_funscript, progress_callback)
    else:
        self._generate_legacy_axes(main_funscript, progress_callback)
```

#### Motion Axis Generation
1. **Configuration Reading**: Load axis configs from positional_axes.motion_axis_config
2. **Mapping Application**: Apply linear interpolation to each enabled axis
3. **File Generation**: Create e1.funscript through e4.funscript (based on enabled axes)
4. **Integration**: Motion axes replace alpha/beta in downstream processing

### Configuration Schema
```python
"positional_axes": {
    "mode": "legacy",  # "legacy" | "motion_axis"
    "e1": {
        "enabled": True,
        "curve": {
            "name": "Linear",
            "description": "Direct 1:1 mapping",
            "control_points": [(0.0, 0.0), (1.0, 1.0)]
        }
    },
    "e2": {
        "enabled": True,
        "curve": {
            "name": "Ease In",
            "description": "Gradual start, strong finish",
            "control_points": [(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)]
        }
    },
    "e3": {
        "enabled": True,
        "curve": {
            "name": "Ease Out",
            "description": "Strong start, gradual finish",
            "control_points": [(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)]
        }
    },
    "e4": {
        "enabled": True,
        "curve": {
            "name": "Bell Curve",
            "description": "Emphasis on middle range",
            "control_points": [(0.0, 0.0), (0.25, 0.3), (0.5, 1.0), (0.75, 0.3), (1.0, 0.0)]
        }
    }
}
```

### Benefits and Use Cases
- **Customizable Motion Patterns**: Users can create exactly the motion characteristics they need
- **Non-Destructive**: Completely separate from legacy alpha/beta system
- **Extensible**: Easy to add new algorithms or axis types in the future
- **Intuitive**: Visual curve editing makes configuration accessible
- **Performance**: Simple linear interpolation is computationally efficient

## 1D to 2D Conversion Algorithm (Legacy)

### Tabbed Conversion Interface
The application includes a comprehensive 1D to 2D conversion system with dedicated tabs for different conversion purposes:

#### Basic Tab - Standard Conversion
1. **Circular (0°-180°)**: Original semicircular motion algorithm
2. **Top-Left-Right (0°-270°)**: Oscillating arc motion counter-clockwise from top
3. **Top-Right-Left (0°-90°)**: Oscillating arc motion clockwise from top

#### Prostate Tab - Specialized Prostate Conversion
1. **Generate from inverted funscript**: Checkbox (default: checked) - Apply inversion before conversion
2. **Standard (0°-180°)**: Basic semicircular motion with fixed radius for prostate stimulation
3. **Tear-shaped (0°-180°)**: Variable-radius semicircular motion with configurable distance pattern
   - Distance = 1.0 at 0° (outer edge)
   - Distance = min_distance_from_center at 120°-180° (configurable constant zone)
   - Linear interpolation from 0° to 120°
4. **Min Distance From Center**: Slider (0.3-0.9, default: 0.5) - Controls distance for tear-shaped constant zone

### Algorithm-Specific Features

#### Basic Tab - Speed-Responsive Radius Control
Basic algorithms include dynamic radius control based on movement speed:

```python
def convert_with_speed_control(funscript, algorithm, min_distance_from_center=0.1, speed_at_edge_hz=2.0):
    """
    Convert 1D funscript to 2D using speed-responsive radius.

    Speed Calculation:
    - current_speed = position_change / time_duration
    - max_speed_threshold = 1.0 / (1.0 / speed_at_edge_hz)
    - radius_scale = min_distance + (1.0 - min_distance) * (speed / max_speed)

    Algorithm-Specific Behavior:
    - Circular: θ = 0° to 180°, radius varies with speed
    - Top-Left-Right: funscript_pos maps to 0°-270°, radius varies with speed
    - Top-Right-Left: funscript_pos maps to 0°-90°, radius varies with speed
    """

#### Prostate Tab - Fixed Radius Control
Prostate algorithms use simplified, fixed radius patterns optimized for prostate stimulation:

- **Standard**: Fixed radius of 1.0 for consistent semicircular motion
- **Tear-shaped**: Variable radius based on angle position, using configurable min_distance_from_center
  - No speed-responsive scaling for more predictable stimulation patterns
```

### Configuration Parameters
- **Algorithm Selection**: Radio buttons for choosing conversion method
- **Points Per Second**: Interpolation density (1-100, default: 25)
- **Min Distance From Center**: Minimum radius (0.1-0.9, default: 0.1)
- **Speed at Edge (Hz)**: Speed threshold for maximum radius (1-5 Hz, default: 2.0)

### Benefits
- **Multiple Motion Patterns**: Three distinct movement algorithms
- **Speed-Responsive Motion**: Radius adapts to funscript speed intensity
- **Position-Accurate Mapping**: Angular position corresponds to funscript values
- **Configurable Behavior**: User control over movement characteristics
- **Complete Processing**: Ensures all 10 output files are generated even with minimal input
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