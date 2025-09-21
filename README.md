# Restim Funscript Processor

A Python GUI application for processing funscript files for electrostimulation devices. This application replaces the PowerShell-based workflow with a user-friendly interface and integrated processing pipeline.

## Features

- **Intuitive GUI**: Easy-to-use interface with organized parameter tabs
- **Comprehensive Processing**: Generates 10 different output funscripts for various stimulation parameters
- **Auto-generation**: Automatically creates alpha/beta files from main funscript when missing using 1D to 2D conversion
- **Configurable Parameters**: 30+ configurable parameters with improved ratio controls showing real-time percentages
- **File Management**: Automatic intermediary file management with optional cleanup
- **Progress Tracking**: Real-time progress updates during processing
- **Configuration Persistence**: Save and load parameter configurations

## Generated Output Files

The application processes a single input funscript and generates:

1. `alpha.funscript` - Alpha channel data
2. `alpha-prostate.funscript` - Inverted alpha for prostate stimulation
3. `beta.funscript` - Beta channel data
4. `frequency.funscript` - Combined ramp/speed frequency
5. `pulse_frequency.funscript` - Alpha-based pulse frequency
6. `pulse_rise_time.funscript` - Composite timing signal
7. `pulse_width.funscript` - Limited alpha-based width
8. `volume.funscript` - Standard volume control
9. `volume-prostate.funscript` - Enhanced volume for prostate
10. `volume-stereostim.funscript` - Mapped volume range

## Requirements

- Python 3.7 or later
- NumPy (automatically installed)
- Tkinter (included with Python)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Select your input `.funscript` file using the Browse button

3. **Optional**: Configure 1D to 2D conversion:
   - Choose algorithm (Circular, Top-Left-Right, or Top-Right-Left)
   - Adjust speed-responsive radius controls
   - Click "Convert to 2D" for alpha/beta generation only

4. Configure parameters in the tabbed interface:
   - **General**: Basic processing parameters
   - **Speed**: Speed calculation settings
   - **Frequency**: Frequency mapping with improved ratio sliders showing real-time percentages
   - **Volume**: Volume processing with percentage-based ramp generation and clear combination ratio controls
   - **Pulse**: Pulse parameters with intuitive ratio displays
   - **Advanced**: Optional features and inversions

5. Choose processing options:
   - ☐ Normalize Volume: Apply volume normalization
   - ☐ Delete Intermediary Files When Done: Clean up temporary files

6. Click "Process Files" to start processing

7. Monitor progress in the status area

## Configuration

Parameters are automatically saved to `restim_config.json` when you click "Save Config". The application will remember your settings between sessions.

Use "Reset to Defaults" to restore factory settings.

## File Management

- **Input file**: Select any `.funscript` file
- **Intermediary files**: Created in `funscript-temp` subdirectory (automatically cleaned up if option selected)
- **Output files**: Placed in the same directory as the input file
- **Auxiliary files**: If `alpha.funscript`, `beta.funscript`, `speed.funscript`, or `ramp.funscript` exist alongside your input file, they will be used instead of generated
- **Ramp Generation**: Volume ramp uses percentage-based progression with configurable rate (0-40% per hour, default 15%)
- **Auto-generation**: Missing `alpha.funscript` and `beta.funscript` files are automatically created from the main funscript using multiple 1D to 2D conversion algorithms
- **1D to 2D Conversion**: Dedicated section with algorithm selection and speed-responsive radius control

## 1D to 2D Conversion

The application features a sophisticated 1D to 2D conversion system with multiple algorithms and speed-responsive motion control:

### Available Algorithms

- **Circular (0°-180°)**: Original semicircular motion algorithm
- **Top-Left-Right (0°-270°)**: Oscillating arc motion counter-clockwise from top
- **Top-Right-Left (0°-90°)**: Oscillating arc motion clockwise from top

### Speed-Responsive Radius Control

The conversion system includes dynamic radius control that responds to funscript movement speed:

- **Min Distance From Center** (0.1-0.9): Sets the minimum radius for slow movements
- **Speed at Edge (Hz)** (1-5 Hz): Defines the speed threshold where the dot reaches maximum radius
- **Dynamic Scaling**: Slow movements stay closer to center, fast movements reach the edge

### Usage

1. **Algorithm Selection**: Choose your preferred motion pattern using radio buttons
2. **Configure Parameters**: Adjust interpolation density and radius control settings
3. **Convert to 2D**: Click "Convert to 2D" to generate only alpha/beta files
4. **Full Processing**: Use "Process Files" for complete workflow including 2D conversion

### Technical Details

- **Position Mapping**: Angular position directly corresponds to funscript position values
- **Speed Calculation**: `current_speed = position_change / time_duration`
- **Radius Scaling**: `radius = min_distance + (1.0 - min_distance) * (speed / max_speed)`
- **Quality Control**: Configurable points per second (1-100) for interpolation density

## Enhanced Ratio Controls

The application features improved combination ratio controls and ramp generation:

- **Interactive Sliders**: Adjust ratios with real-time visual feedback (automatically rounded to 0.1 precision)
- **Percentage Display**: See exact mixing percentages (e.g., "Ramp 83.3% | Speed 16.7%")
- **Clear Labeling**: Each control shows which files are being combined
- **Dual Input**: Use sliders for quick adjustment or text entry for precise values
- **Clean Values**: All ratio values automatically round to one decimal place for clarity
- **Smart Ramp Generation**: Percentage-based progression with real-time value display and per-minute calculation

### Example Ratio Meanings:
- **Ratio 2**: 50% File1 + 50% File2 (equal mix)
- **Ratio 3**: 66.7% File1 + 33.3% File2 (File1 dominant)
- **Ratio 6**: 83.3% File1 + 16.7% File2 (heavily weighted toward File1)

## Technical Details

- **Processing Pipeline**: Integrated Python workflow replacing separate script calls
- **Performance**: Utilizes caching and optimized numpy operations
- **Thread Safety**: Processing runs in background thread to maintain UI responsiveness
- **Error Handling**: Comprehensive validation and user-friendly error messages

## Troubleshooting

1. **"Module not found" errors**: Ensure you've installed requirements with `pip install -r requirements.txt`
2. **Permission errors**: Ensure write access to the input file directory
3. **Processing errors**: Check that input file is a valid funscript JSON format
4. **Configuration errors**: Use "Reset to Defaults" if parameter validation fails

## Building Windows Executable

To create a standalone Windows executable that doesn't require Python installation:

### Prerequisites

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### Build Process

1. **Quick Build**: Run the automated build script:
   ```bash
   python build_windows.py
   ```

2. **Manual Build** (alternative): Use PyInstaller directly:
   ```bash
   pyinstaller --onefile --windowed --name RestimFunscriptProcessor main.py
   ```

### Build Output

The build script creates:
- **Executable**: `dist/windows/RestimFunscriptProcessor-v{version}.exe`
- **Release Package**: `dist/RestimFunscriptProcessor-v{version}-Windows.zip`

The release package includes:
- Standalone executable (no Python required)
- Complete documentation (README.md, specifications)
- Installation guide (INSTALLATION.txt)

### Build Features

- **Single File**: All dependencies bundled into one executable
- **No Console**: GUI-only application (no command prompt window)
- **Auto-Versioning**: Version number automatically included in filename
- **Documentation**: Complete docs package included
- **Cross-Platform**: Can build on any platform (best results on Windows)

### Distribution

The generated ZIP file in the `dist/` folder contains everything needed for distribution. Users simply:
1. Extract the ZIP file
2. Run `RestimFunscriptProcessor.exe`
3. No Python installation required!

## Development

The application is structured as follows:

- `main.py` - Entry point
- `processor.py` - Core processing workflow
- `config.py` - Configuration management
- `funscript/` - Funscript file handling
- `processing/` - Individual processing functions
- `ui/` - GUI components
- `build_windows.py` - Windows executable build script