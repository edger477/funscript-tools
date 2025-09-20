# Restim Funscript Processing Requirements Specification

## Overview
This document specifies the requirements and behavior of the `create restim scripts-posfreq.ps1` PowerShell script when processing funscript files for electrostimulation (restim) devices. The script transforms a single input funscript into multiple specialized output funscripts for different stimulation parameters.

## Input Requirements

### Primary Input
- **Main Funscript**: The primary input file (e.g., `video.funscript`)
  - JSON format with `actions` array containing `at` (timestamp in ms) and `pos` (position 0-100) values
  - Used as the base for generating all derivative scripts

### Optional Auxiliary Inputs
The script checks for and utilizes the following auxiliary files if they exist:
- **Ramp file**: `{filename}.ramp.funscript` - Volume ramp data
- **Speed file**: `{filename}.speed.funscript` - Pre-calculated speed data
- **Alpha file**: `{filename}.alpha.funscript` - Alpha channel data for frequency mapping
- **Beta file**: `{filename}.beta.funscript` - Beta channel data for pulse timing

### Script Parameters
- `$rest_level` (default: 0.4) - Signal level when volume ramp or speed is 0
- `$FreqMapMin` (default: 0.30) - Minimum mapping value for alpha to pulse frequency
- `$FreqMapMax` (default: 0.95) - Maximum mapping value for alpha to pulse frequency
- `$WidthLimitMin` (default: 0.1) - Minimum limit for pulse width
- `$WidthLimitMax` (default: 0.75) - Maximum limit for pulse width
- `$SpeedWindowSizeInSeconds` (default: 5) - Window size for speed calculation
- `$AccelWindowSizeInSeconds` (default: 3) - Window size for acceleration calculation
- `$VolumeRampCombineRatio` (default: 6) - Ratio for combining volume and ramp
- `$FrequencyRampCombineRatio` (default: 2) - Ratio for combining frequency and ramp

## Processing Workflow

### Phase 1: Auxiliary File Preparation
1. **Copy existing auxiliary files** to working directory with standardized names
2. **Generate missing speed file** if not provided:
   - Convert main funscript to speed using windowed calculation
   - Invert the speed values (100 - pos for all positions)
3. **Generate acceleration file** from speed data using smaller time window
4. **Generate volume ramp** from main funscript if not provided

### Phase 2: Frequency Processing
1. **Alpha-based frequency generation**:
   - Map alpha channel values to pulse frequency range (FreqMapMin to FreqMapMax)
   - Combine with speed data using ratio 3:1
   - Generate inverted version
2. **Primary frequency generation**:
   - Combine ramp and speed with FrequencyRampCombineRatio
   - Generate inverted version

### Phase 3: Volume Processing
1. **Standard volume**:
   - Combine ramp and speed with VolumeRampCombineRatio and rest_level
2. **Prostate volume**:
   - Combine ramp and speed with (VolumeRampCombineRatio * 1.5) and rest_level=0.7
3. **Volume normalization**:
   - Find maximum value and shift all values to utilize full 0-100 range
   - Generate inverted version
4. **Stereostim volume**:
   - Map standard volume to 0.50-1.00 range

### Phase 4: Pulse Parameter Processing
1. **Alpha processing**:
   - Generate inverted alpha for prostate stimulation
2. **Beta processing**:
   - Mirror-up beta values above 0.5 threshold
3. **Pulse width generation**:
   - Limit inverted alpha to WidthLimitMin-WidthLimitMax range
   - Combine with speed using 3:1 ratio
4. **Pulse rise time**:
   - Combine mirrored beta, inverted speed, and inverted ramp
   - Map to 0.00-0.80 range

### Phase 5: Output Generation
The following files are copied to `./funscript-output/` directory as **FINAL OUTPUTS**:
- `{filename}.alpha.funscript`
- `{filename}.alpha-prostate.funscript`
- `{filename}.beta.funscript`
- `{filename}.frequency.funscript`
- `{filename}.pulse_frequency.funscript`
- `{filename}.pulse_rise_time.funscript`
- `{filename}.pulse_width.funscript`
- `{filename}.volume.funscript`
- `{filename}.volume-prostate.funscript`
- `{filename}.volume-stereostim.funscript`

## File Classification

### Final Outputs (10 files)
These are the essential output files copied to `funscript-output/` for use with electrostimulation devices.

### Intermediary Files (11 files)
These files are generated during processing and used by subsequent steps:
- `{filename}.speed.funscript` - Used by accel, volume, frequency, pulse_frequency, pulse_width generation
- `{filename}.accel.funscript` - Used by pulse_rise_time generation
- `{filename}.ramp.funscript` - Used by volume, frequency, pulse_rise_time generation
- `{filename}.pulse_frequency-alphabased.funscript` - Used to create pulse_frequency
- `{filename}.alpha_inverted.funscript` - Used to create alpha-prostate and pulse_width-alpha
- `{filename}.speed_inverted.funscript` - Used by pulse_rise_time generation
- `{filename}.ramp_inverted.funscript` - Used by pulse_rise_time generation
- `{filename}.beta-mirror-up.funscript` - Used by pulse_rise_time generation
- `{filename}.pulse_width-alpha.funscript` - Used to create pulse_width
- `{filename}.volume_normalized.funscript` - Replaces volume during normalization process
- `{filename}.volume_not_normalized.funscript` - Backup of original volume before normalization

### Alternative Files (4 files - NOT NECESSARY)
These files are generated but never used by other processes and could be eliminated:
- `{filename}.pulse_frequency_inverted.funscript` - **Alternative** (created but never referenced)
- `{filename}.volume_inverted.funscript` - **Alternative** (created but never referenced)
- `{filename}.frequency_inverted.funscript` - **Alternative** (created but never referenced)
- `{filename}.volume_not_normalized.funscript` - **Alternative** (backup file, never used)

## Python Processing Modules

### Core Funscript Module (`funscript/funscript.py`)
- **Caching**: SHA1-based file caching for performance
- **Loading**: Converts JSON format (ms, 0-100) to internal format (seconds, 0.0-1.0)
- **Saving**: Converts back to JSON format with proper scaling

### Processing Scripts

#### `invert.py`
- **Function**: Inverts position values (pos = 100 - pos)
- **Output**: Creates `{filename}_inverted.funscript`

#### `convert-to-speed.py`
- **Function**: Calculates rolling average speed over time window
- **Process**:
  - Interpolates to 0.1-second intervals
  - Calculates absolute position change per time unit
  - Normalizes to 0-1.0 range
- **Windowing**: Configurable time window for speed averaging

#### `map-funscript.py`
- **Function**: Linear mapping of values to new range
- **Formula**: `y_new = (y - current_min) / (current_max - current_min) * (new_max - new_min) + new_min`

#### `combine-funscripts.py`
- **Function**: Weighted average of two funscripts
- **Formula**: `y = (y_left * (ratio - 1) + y_right) / ratio`
- **Rest Level**: Applied when either input is 0

#### `limit-funscript.py`
- **Function**: Clamps values to specified range
- **Formula**: `y_new = min(max(y, new_min), new_max)`

#### `normalize-funscript.py`
- **Function**: Shifts all values up to maximize range usage
- **Process**: Finds maximum value and adds (100 - max) to all values

#### `make-volume-ramp.py`
- **Function**: Creates volume ramp with 4 key points
- **Pattern**: Start (0) → Rise (80) → Peak (100) → End (0)

#### `mirror-up.py`
- **Function**: Mirrors values below threshold above it
- **Formula**: `y_new = (y < threshold) ? 2 * threshold - y : y`

## File Format Specifications

### Input Funscript Format
```json
{
  "actions": [
    {"at": 1000, "pos": 50},
    {"at": 2000, "pos": 75}
  ]
}
```

### Internal Processing Format
- Time: Floating-point seconds
- Position: Floating-point 0.0-1.0 range

### Output Requirements
- All outputs maintain original JSON structure
- Timestamps preserved from input
- Position values scaled appropriately for each parameter type

## Performance Considerations
- **Caching**: Input files are cached using SHA1 hashing
- **Interpolation**: High-resolution interpolation (0.1s intervals) for accurate processing
- **Conditional Processing**: Existing output files are not regenerated

## Error Handling
- **Missing Files**: Script continues with generated alternatives
- **Invalid Data**: Python scripts validate input format
- **Insufficient Data**: Minimum 4 actions required for volume ramp generation

## Dependencies
- **PowerShell**: Windows PowerShell environment
- **Python**: Python 3.x with numpy for mathematical operations
- **File System**: Write access to working directory and `./funscript-output/`