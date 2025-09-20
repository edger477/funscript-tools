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

3. Configure parameters in the tabbed interface:
   - **General**: Basic processing parameters
   - **Speed**: Speed calculation settings + Alpha/Beta auto-generation controls
   - **Frequency**: Frequency mapping with improved ratio sliders showing real-time percentages
   - **Volume**: Volume processing with clear combination ratio controls
   - **Pulse**: Pulse parameters with intuitive ratio displays
   - **Advanced**: Optional features and inversions

4. Choose processing options:
   - ☐ Normalize Volume: Apply volume normalization
   - ☐ Delete Intermediary Files When Done: Clean up temporary files

5. Click "Process Files" to start processing

6. Monitor progress in the status area

## Configuration

Parameters are automatically saved to `restim_config.json` when you click "Save Config". The application will remember your settings between sessions.

Use "Reset to Defaults" to restore factory settings.

## File Management

- **Input file**: Select any `.funscript` file
- **Intermediary files**: Created in `funscript-temp` subdirectory (automatically cleaned up if option selected)
- **Output files**: Placed in the same directory as the input file
- **Auxiliary files**: If `alpha.funscript`, `beta.funscript`, `speed.funscript`, or `ramp.funscript` exist alongside your input file, they will be used instead of generated
- **Auto-generation**: Missing `alpha.funscript` and `beta.funscript` files are automatically created from the main funscript using 1D to 2D radial conversion

## Enhanced Ratio Controls

The application features improved combination ratio controls that clearly show how files are mixed:

- **Interactive Sliders**: Adjust ratios with real-time visual feedback (automatically rounded to 0.1 precision)
- **Percentage Display**: See exact mixing percentages (e.g., "Ramp 83.3% | Speed 16.7%")
- **Clear Labeling**: Each control shows which files are being combined
- **Dual Input**: Use sliders for quick adjustment or text entry for precise values
- **Clean Values**: All ratio values automatically round to one decimal place for clarity

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

## Development

The application is structured as follows:

- `main.py` - Entry point
- `processor.py` - Core processing workflow
- `config.py` - Configuration management
- `funscript/` - Funscript file handling
- `processing/` - Individual processing functions
- `ui/` - GUI components