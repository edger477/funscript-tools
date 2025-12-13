import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, Any


def calculate_combine_percentages(ratio):
    """Calculate the percentages for combine ratio."""
    left_pct = (ratio - 1) / ratio * 100
    right_pct = 1 / ratio * 100
    return left_pct, right_pct


def format_percentage_label(file1_name, file2_name, ratio):
    """Format a percentage label for combine ratios."""
    left_pct, right_pct = calculate_combine_percentages(ratio)
    return f"{file1_name} {left_pct:.1f}% | {file2_name} {right_pct:.1f}%"


class CombineRatioControl:
    """A control that shows both slider and text entry for combine ratios with percentage display."""

    def __init__(self, parent, label_text, file1_name, file2_name, initial_value, min_val=1, max_val=10, row=0):
        self.file1_name = file1_name
        self.file2_name = file2_name
        self.var = tk.DoubleVar(value=initial_value)

        # Label
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Slider - we'll handle rounding in the callback
        self.slider = ttk.Scale(parent, from_=min_val, to=max_val, variable=self.var,
                               orient=tk.HORIZONTAL, length=200, command=self._on_change)
        self.slider.grid(row=row, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Text entry with better formatting
        self.entry = ttk.Entry(parent, textvariable=self.var, width=8)
        self.entry.grid(row=row, column=2, padx=5, pady=5)
        self.entry.bind('<Return>', self._on_entry_change)
        self.entry.bind('<FocusOut>', self._on_entry_change)

        # Set initial value with proper formatting
        self.var.set(round(initial_value, 1))

        # Percentage display
        self.percentage_label = ttk.Label(parent, text="", foreground="blue")
        self.percentage_label.grid(row=row, column=3, sticky=tk.W, padx=5, pady=5)

        # Initial update
        self._update_percentage_display()

    def _on_change(self, value=None):
        """Called when slider moves."""
        # Ensure value is rounded to one decimal place
        try:
            current_value = float(self.var.get())
            rounded_value = round(current_value, 1)
            # Only update if significantly different to avoid infinite loops
            if abs(current_value - rounded_value) > 0.01:
                self.var.set(rounded_value)
            self._update_percentage_display()
        except (ValueError, tk.TclError):
            pass

    def _on_entry_change(self, event=None):
        """Called when text entry changes."""
        try:
            value = float(self.var.get())
            if value >= 1:  # Minimum ratio of 1
                # Round to one decimal place for consistency
                rounded_value = round(value, 1)
                if abs(value - rounded_value) > 0.01:
                    self.var.set(rounded_value)
                self._update_percentage_display()
        except (ValueError, tk.TclError):
            pass

    def _update_percentage_display(self):
        """Update the percentage display label."""
        try:
            ratio = float(self.var.get())
            if ratio >= 1:
                percentage_text = format_percentage_label(self.file1_name, self.file2_name, ratio)
                self.percentage_label.config(text=percentage_text)
        except ValueError:
            self.percentage_label.config(text="Invalid ratio")


class ParameterTabs(ttk.Notebook):
    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)

        self.config = config
        self.parameter_vars = {}
        self.combine_ratio_controls = {}  # Store custom ratio controls

        # Store reference to root window for dialogs
        self.root = parent
        while hasattr(self.root, 'master') and self.root.master:
            self.root = self.root.master

        self.setup_tabs()

    def set_mode_change_callback(self, callback):
        """Set callback function to be called when mode changes."""
        self.mode_change_callback = callback
        
        # Add trace to mode variable if it exists
        if hasattr(self, 'parameter_vars') and 'positional_axes' in self.parameter_vars:
            mode_var = self.parameter_vars['positional_axes']['mode']
            mode_var.trace('w', lambda *args: self._on_mode_change())
    
    def _on_mode_change(self):
        """Internal method called when mode changes."""
        if hasattr(self, 'mode_change_callback'):
            try:
                mode = self.parameter_vars['positional_axes']['mode'].get()
                self.mode_change_callback(mode)
            except Exception:
                pass  # Ignore errors during callback

    def setup_tabs(self):
        """Setup all parameter tabs."""
        # General tab
        self.general_frame = ttk.Frame(self)
        self.add(self.general_frame, text="General")
        self.setup_general_tab()

        # Speed tab
        self.speed_frame = ttk.Frame(self)
        self.add(self.speed_frame, text="Speed")
        self.setup_speed_tab()

        # Frequency tab
        self.frequency_frame = ttk.Frame(self)
        self.add(self.frequency_frame, text="Frequency")
        self.setup_frequency_tab()

        # Volume tab
        self.volume_frame = ttk.Frame(self)
        self.add(self.volume_frame, text="Volume")
        self.setup_volume_tab()

        # Pulse tab
        self.pulse_frame = ttk.Frame(self)
        self.add(self.pulse_frame, text="Pulse")
        self.setup_pulse_tab()

        # Motion Axis tab
        self.motion_axis_frame = ttk.Frame(self)
        self.add(self.motion_axis_frame, text="Motion Axis")
        self.setup_motion_axis_tab()

        # Advanced tab
        self.advanced_frame = ttk.Frame(self)
        self.add(self.advanced_frame, text="Advanced")
        self.setup_advanced_tab()

    def setup_general_tab(self):
        """Setup the General parameters tab."""
        frame = self.general_frame
        self.parameter_vars['general'] = {}

        row = 0

        # Rest Level
        ttk.Label(frame, text="Rest Level:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['general']['rest_level'])
        self.parameter_vars['general']['rest_level'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Signal level when volume ramp or speed is 0").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Speed Window Size
        ttk.Label(frame, text="Speed Window (sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['general']['speed_window_size'])
        self.parameter_vars['general']['speed_window_size'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-30) Window size for speed calculation").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Acceleration Window Size
        ttk.Label(frame, text="Accel Window (sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['general']['accel_window_size'])
        self.parameter_vars['general']['accel_window_size'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-10) Window size for acceleration calculation").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 2

        # Processing Options section
        ttk.Label(frame, text="Processing Options:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Initialize options parameter vars
        self.parameter_vars['options'] = {}

        # Normalize Volume
        var = tk.BooleanVar(value=self.config['options']['normalize_volume'])
        self.parameter_vars['options']['normalize_volume'] = var
        ttk.Checkbutton(frame, text="Normalize Volume", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Delete Intermediary Files
        var = tk.BooleanVar(value=self.config['options']['delete_intermediary_files'])
        self.parameter_vars['options']['delete_intermediary_files'] = var
        ttk.Checkbutton(frame, text="Delete Intermediary Files When Done", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 2

        # Auto-generation section
        ttk.Label(frame, text="Auto-generation:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Auto Generate Alpha/Beta
        self.parameter_vars['alpha_beta_generation'] = {}
        var = tk.BooleanVar(value=self.config['alpha_beta_generation']['auto_generate'])
        self.parameter_vars['alpha_beta_generation']['auto_generate'] = var
        ttk.Checkbutton(frame, text="Auto-generate alpha/beta files when missing", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

    def setup_speed_tab(self):
        """Setup the Speed parameters tab."""
        frame = self.speed_frame
        self.parameter_vars['speed'] = {}

        row = 0

        # Speed Processing section
        ttk.Label(frame, text="Speed Processing:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        row += 1

        # Interpolation Interval
        ttk.Label(frame, text="Interpolation Interval:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['speed']['interpolation_interval'])
        self.parameter_vars['speed']['interpolation_interval'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.01-1.0) Seconds between interpolated points").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Normalization Method
        ttk.Label(frame, text="Normalization Method:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar(value=self.config['speed']['normalization_method'])
        self.parameter_vars['speed']['normalization_method'] = var
        combo = ttk.Combobox(frame, textvariable=var, values=["max", "rms"], state="readonly", width=15)
        combo.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="Method for normalizing speed values").grid(row=row, column=2, sticky=tk.W, padx=5)

    def setup_frequency_tab(self):
        """Setup the Frequency parameters tab."""
        frame = self.frequency_frame
        self.parameter_vars['frequency'] = {}

        row = 0

        # Pulse Frequency Min
        ttk.Label(frame, text="Pulse Frequency Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['pulse_freq_min'])
        self.parameter_vars['frequency']['pulse_freq_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum mapping for main funscript to pulse frequency").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Frequency Max
        ttk.Label(frame, text="Pulse Frequency Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['pulse_freq_max'])
        self.parameter_vars['frequency']['pulse_freq_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum mapping for main funscript to pulse frequency").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Frequency Ramp Combine Ratio
        freq_ramp_control = CombineRatioControl(
            frame, "Frequency Combine:",
            "Ramp", "Speed",
            self.config['frequency']['frequency_ramp_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['frequency']['frequency_ramp_combine_ratio'] = freq_ramp_control.var
        self.combine_ratio_controls['frequency_ramp_combine_ratio'] = freq_ramp_control

        row += 1

        # Pulse Frequency Combine Ratio
        pulse_freq_control = CombineRatioControl(
            frame, "Pulse Frequency Combine:",
            "Speed", "Alpha-Frequency",
            self.config['frequency']['pulse_frequency_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['frequency']['pulse_frequency_combine_ratio'] = pulse_freq_control.var
        self.combine_ratio_controls['pulse_frequency_combine_ratio'] = pulse_freq_control

    def setup_volume_tab(self):
        """Setup the Volume parameters tab."""
        frame = self.volume_frame
        self.parameter_vars['volume'] = {}

        row = 0

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Volume Ramp Combine Ratio
        volume_ramp_control = CombineRatioControl(
            frame, "Volume Combine Ratio (Ramp | Speed):",
            "Ramp", "Speed",
            self.config['volume']['volume_ramp_combine_ratio'],
            min_val=10.0, max_val=40.0, row=row
        )
        self.parameter_vars['volume']['volume_ramp_combine_ratio'] = volume_ramp_control.var
        self.combine_ratio_controls['volume_ramp_combine_ratio'] = volume_ramp_control

        row += 1

        # Prostate Volume Multiplier
        ttk.Label(frame, text="Prostate Volume Multiplier:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['prostate_volume_multiplier'])
        self.parameter_vars['volume']['prostate_volume_multiplier'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1.0-3.0) Multiplier for prostate volume ratio").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Prostate Volume Rest Level
        ttk.Label(frame, text="Prostate Volume Rest Level:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['prostate_rest_level'])
        self.parameter_vars['volume']['prostate_rest_level'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Rest level for prostate volume").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Stereostim Volume Min
        ttk.Label(frame, text="Stereostim Volume Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['stereostim_volume_min'])
        self.parameter_vars['volume']['stereostim_volume_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum mapping for stereostim volume").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Stereostim Volume Max
        ttk.Label(frame, text="Stereostim Volume Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['stereostim_volume_max'])
        self.parameter_vars['volume']['stereostim_volume_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum mapping for stereostim volume").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Ramp Percent Per Hour
        ttk.Label(frame, text="Ramp (% per hour):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['volume']['ramp_percent_per_hour'])
        self.parameter_vars['volume']['ramp_percent_per_hour'] = var
        ramp_scale = ttk.Scale(frame, from_=0, to=40, variable=var, orient=tk.HORIZONTAL, length=150, command=self._update_ramp_display)
        ramp_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Create label for current value and per-minute calculation
        self.ramp_value_label = ttk.Label(frame, text="", foreground="blue")
        self.ramp_value_label.grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)

        # Initial update
        self._update_ramp_display()

    def setup_pulse_tab(self):
        """Setup the Pulse parameters tab."""
        frame = self.pulse_frame
        self.parameter_vars['pulse'] = {}

        row = 0

        # Pulse Width Min
        ttk.Label(frame, text="Pulse Width Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_width_min'])
        self.parameter_vars['pulse']['pulse_width_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum limit for pulse width").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Width Max
        ttk.Label(frame, text="Pulse Width Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_width_max'])
        self.parameter_vars['pulse']['pulse_width_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum limit for pulse width").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Pulse Width Combine Ratio
        pulse_width_control = CombineRatioControl(
            frame, "Pulse Width Combine:",
            "Speed", "Alpha-Limited",
            self.config['pulse']['pulse_width_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['pulse']['pulse_width_combine_ratio'] = pulse_width_control.var
        self.combine_ratio_controls['pulse_width_combine_ratio'] = pulse_width_control

        row += 1

        # Beta Mirror Threshold
        ttk.Label(frame, text="Beta Mirror Threshold:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['beta_mirror_threshold'])
        self.parameter_vars['pulse']['beta_mirror_threshold'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-0.5) Threshold for beta mirroring").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Rise Time Min
        ttk.Label(frame, text="Pulse Rise Time Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_rise_min'])
        self.parameter_vars['pulse']['pulse_rise_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum mapping for pulse rise time").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Rise Time Max
        ttk.Label(frame, text="Pulse Rise Time Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_rise_max'])
        self.parameter_vars['pulse']['pulse_rise_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum mapping for pulse rise time").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Rise Combine Ratio
        pulse_rise_control = CombineRatioControl(
            frame, "Pulse Rise Combine:",
            "Beta-Mirrored", "Speed-Inverted",
            self.config['pulse']['pulse_rise_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['pulse']['pulse_rise_combine_ratio'] = pulse_rise_control.var
        self.combine_ratio_controls['pulse_rise_combine_ratio'] = pulse_rise_control

    def setup_motion_axis_tab(self):
        """Setup the Motion Axis parameters tab."""
        frame = self.motion_axis_frame
        self.parameter_vars['positional_axes'] = {}

        row = 0

        # Mode Selection
        ttk.Label(frame, text="Positional Axis Mode:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        row += 1

        # Mode selection radio buttons
        mode_var = tk.StringVar(value=self.config['positional_axes']['mode'])
        self.parameter_vars['positional_axes']['mode'] = mode_var

        ttk.Radiobutton(frame, text="Legacy (Alpha/Beta)", variable=mode_var, value="legacy").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(frame, text="Motion Axis (E1-E4)", variable=mode_var, value="motion_axis").grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Configure grid
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(row, weight=1)

        # Create container for mode-specific content
        self.content_container = ttk.Frame(frame)
        self.content_container.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        # Setup both sections
        self.setup_legacy_section()
        self.setup_motion_axis_section_internal()

        # Setup mode change callback
        mode_var.trace('w', lambda *args: self._on_motion_axis_mode_change())
        
        # Initialize display
        self._update_motion_axis_display()

    def setup_legacy_section(self):
        """Setup the legacy 1D to 2D conversion section within Motion Axis tab."""
        self.legacy_frame = ttk.LabelFrame(self.content_container, text="1D to 2D Conversion", padding="10")
        self.legacy_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.legacy_frame.columnconfigure(0, weight=1)
        self.legacy_frame.rowconfigure(0, weight=1)

        # Import ConversionTabs here to avoid circular import
        from ui.conversion_tabs import ConversionTabs
        
        # Create conversion tabs within the legacy section
        self.embedded_conversion_tabs = ConversionTabs(self.legacy_frame, self.config)
        
        # Initially hide
        self.legacy_frame.grid_remove()

    def setup_motion_axis_section_internal(self):
        """Setup the Motion Axis configuration section within Motion Axis tab."""
        self.motion_config_frame = ttk.LabelFrame(self.content_container, text="Motion Axis Configuration", padding="10")
        self.motion_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.motion_config_frame.columnconfigure(0, weight=1)

        row = 0

        # Import matplotlib for curve visualization
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import numpy as np
            self.matplotlib_available = True
        except ImportError:
            self.matplotlib_available = False
            # Show error message
            error_label = ttk.Label(self.motion_config_frame, 
                                  text="Matplotlib not available - install with: pip install matplotlib",
                                  foreground="red")
            error_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            row += 1

        # Axis enable/disable and curve visualization
        for axis_name in ['e1', 'e2', 'e3', 'e4']:
            axis_config = self.config['positional_axes'][axis_name]
            
            # Create frame for this axis
            axis_frame = ttk.LabelFrame(self.motion_config_frame, text=f"Axis {axis_name.upper()}", padding="5")
            axis_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            axis_frame.columnconfigure(1, weight=1)

            # Initialize axis variables
            self.parameter_vars['positional_axes'][axis_name] = {}

            # Enable checkbox
            enabled_var = tk.BooleanVar(value=axis_config['enabled'])
            self.parameter_vars['positional_axes'][axis_name]['enabled'] = enabled_var
            ttk.Checkbutton(axis_frame, text="Enabled", variable=enabled_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

            # Curve name display
            curve_name = axis_config['curve']['name']
            curve_label = ttk.Label(axis_frame, text=f"Curve: {curve_name}")
            curve_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)

            # Edit curve button
            edit_button = ttk.Button(axis_frame, text="Edit Curve", 
                                   command=lambda a=axis_name: self._open_curve_editor(a))
            edit_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)

            # Curve visualization
            if self.matplotlib_available:
                curve_frame = ttk.Frame(axis_frame)
                curve_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
                
                # Create matplotlib figure for this curve
                fig = Figure(figsize=(5, 1), dpi=80)  # 5x wider than tall for 5:1 ratio
                fig.patch.set_facecolor('white')
                ax = fig.add_subplot(111)
                
                # Generate curve data
                control_points = axis_config['curve']['control_points']
                x_vals, y_vals = self._generate_curve_data(control_points)
                
                # Plot the curve
                ax.plot(x_vals, y_vals, 'b-', linewidth=2)
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 100)
                ax.set_xlabel('Input Position', fontsize=8)
                ax.set_ylabel('Output', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                
                # Remove extra margins
                fig.tight_layout(pad=0.5)
                
                # Embed in tkinter
                canvas = FigureCanvasTkAgg(fig, curve_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                
                # Store reference for potential updates
                setattr(self, f'{axis_name}_curve_canvas', canvas)
                setattr(self, f'{axis_name}_curve_ax', ax)

            row += 1

        row += 1

        # Information section
        ttk.Label(self.motion_config_frame, text="Information:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        info_text = """Motion Axis Generation creates E1-E4 files using configurable response curves.
Each curve transforms the input position (0-100) to output position (0-100) based on the curve shape.
Enable/disable individual axes and edit curves to customize the motion pattern."""

        info_label = ttk.Label(self.motion_config_frame, text=info_text, wraplength=500, justify=tk.LEFT)
        info_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Initially hide
        self.motion_config_frame.grid_remove()

    def _generate_curve_data(self, control_points):
        """Generate curve data from control points for visualization."""
        try:
            import numpy as np
            from processing.linear_mapping import apply_linear_response_curve
            
            # Generate input values from 0 to 100
            x_vals = np.linspace(0, 100, 101)  # 101 points for smooth curve
            y_vals = np.zeros_like(x_vals)
            
            # Apply linear interpolation using the same logic as the processing module
            for i, x in enumerate(x_vals):
                normalized_input = x / 100.0  # Convert to 0-1 range
                normalized_output = apply_linear_response_curve(normalized_input, control_points)
                y_vals[i] = normalized_output * 100.0  # Convert back to 0-100 range
            
            return x_vals, y_vals
            
        except Exception as e:
            # Fallback to simple linear curve if there's any error
            x_vals = np.array([0, 100])
            y_vals = np.array([0, 100])
            return x_vals, y_vals

    def _update_curve_visualizations(self):
        """Update all curve visualizations with current config data."""
        if not self.matplotlib_available:
            return
            
        try:
            for axis_name in ['e1', 'e2', 'e3', 'e4']:
                canvas_attr = f'{axis_name}_curve_canvas'
                ax_attr = f'{axis_name}_curve_ax'
                
                if hasattr(self, canvas_attr) and hasattr(self, ax_attr):
                    canvas = getattr(self, canvas_attr)
                    ax = getattr(self, ax_attr)
                    
                    # Get current curve config
                    axis_config = self.config['positional_axes'][axis_name]
                    control_points = axis_config['curve']['control_points']
                    
                    # Clear and redraw
                    ax.clear()
                    
                    # Generate new curve data
                    x_vals, y_vals = self._generate_curve_data(control_points)
                    
                    # Plot the curve
                    ax.plot(x_vals, y_vals, 'b-', linewidth=2)
                    ax.set_xlim(0, 100)
                    ax.set_ylim(0, 100)
                    ax.set_xlabel('Input Position', fontsize=8)
                    ax.set_ylabel('Output', fontsize=8)
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(labelsize=7)
                    
                    # Redraw canvas
                    canvas.draw()
                    
        except Exception as e:
            # Ignore visualization errors
            print(f"Warning: Could not update curve visualization: {e}")

    def _on_motion_axis_mode_change(self):
        """Handle mode changes within the Motion Axis tab."""
        self._update_motion_axis_display()
        
        # Also call the main window callback if it exists
        if hasattr(self, 'mode_change_callback'):
            try:
                mode = self.parameter_vars['positional_axes']['mode'].get()
                self.mode_change_callback(mode)
            except Exception:
                pass

    def _update_motion_axis_display(self):
        """Update the display within Motion Axis tab based on current mode."""
        try:
            current_mode = self.parameter_vars['positional_axes']['mode'].get()
            
            if current_mode == 'motion_axis':
                # Show Motion Axis configuration, hide legacy
                self.legacy_frame.grid_remove()
                self.motion_config_frame.grid()
            else:
                # Show legacy conversion, hide Motion Axis configuration
                self.motion_config_frame.grid_remove()
                self.legacy_frame.grid()
        except Exception:
            # Default to legacy if there's any error
            if hasattr(self, 'legacy_frame'):
                self.motion_config_frame.grid_remove()
                self.legacy_frame.grid()

    def _open_curve_editor(self, axis_name):
        """Open curve editor modal dialog."""
        try:
            from .curve_editor_dialog import edit_curve

            # Get current curve configuration
            current_curve = self.config['positional_axes'][axis_name]['curve']

            # Open the curve editor dialog
            result = edit_curve(self.root, axis_name, current_curve)

            if result is not None:
                # User saved changes - update configuration
                self.config['positional_axes'][axis_name]['curve'] = result

                # Update the curve visualization
                self._update_curve_visualizations()

                # Update the curve name display
                self._update_curve_name_display(axis_name)

        except ImportError as e:
            # Fallback if curve editor is not available
            import tkinter.messagebox as msgbox
            msgbox.showerror("Curve Editor Error", f"Curve editor is not available: {str(e)}")
        except Exception as e:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open curve editor: {str(e)}")

    def _update_curve_name_display(self, axis_name):
        """Update the curve name display for a specific axis."""
        try:
            # Find and update the curve name label for this axis
            curve_name = self.config['positional_axes'][axis_name]['curve']['name']

            # The curve name label was created in setup_motion_axis_section_internal
            # We need to find it and update its text
            for child in self.motion_config_frame.winfo_children():
                if isinstance(child, ttk.LabelFrame) and axis_name.upper() in child.cget('text'):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.Label) and 'Curve:' in subchild.cget('text'):
                            subchild.config(text=f"Curve: {curve_name}")
                            break
                    break
        except Exception as e:
            print(f"Error updating curve name display: {e}")

    def _browse_output_directory(self):
        """Open file dialog to browse for output directory."""
        # Get current directory if set
        current_dir = self.parameter_vars['advanced']['custom_output_directory'].get()
        initial_dir = current_dir if current_dir else None
        
        # Open directory selection dialog
        selected_dir = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial_dir
        )
        
        # Update the variable if a directory was selected
        if selected_dir:
            self.parameter_vars['advanced']['custom_output_directory'].set(selected_dir)

    def setup_advanced_tab(self):
        """Setup the Advanced parameters tab."""
        frame = self.advanced_frame
        self.parameter_vars['advanced'] = {}

        row = 0

        # Enable optional inversion files
        ttk.Label(frame, text="Optional Inversion Files:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        row += 1

        # Pulse Frequency Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_pulse_frequency_inversion'])
        self.parameter_vars['advanced']['enable_pulse_frequency_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Pulse Frequency Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Volume Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_volume_inversion'])
        self.parameter_vars['advanced']['enable_volume_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Volume Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Frequency Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_frequency_inversion'])
        self.parameter_vars['advanced']['enable_frequency_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Frequency Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 2

        # Custom Output Directory
        ttk.Label(frame, text="Custom Output Directory:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        ttk.Label(frame, text="Output Directory:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar(value=self.config['advanced']['custom_output_directory'])
        self.parameter_vars['advanced']['custom_output_directory'] = var

        # Create frame for entry and browse button
        dir_frame = ttk.Frame(frame)
        dir_frame.grid(row=row, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        entry = ttk.Entry(dir_frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, padx=(0, 5))

        browse_button = ttk.Button(dir_frame, text="Browse", command=self._browse_output_directory)
        browse_button.pack(side=tk.LEFT)

        ttk.Label(frame, text="(Leave empty to use input file directory)").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 2

        # Output Packaging Options
        ttk.Label(frame, text="Output Packaging:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Pack Output Files to Zip
        var = tk.BooleanVar(value=self.config['advanced'].get('pack_output_to_zip', False))
        self.parameter_vars['advanced']['pack_output_to_zip'] = var
        ttk.Checkbutton(frame, text="Pack Output Files to Zip Archive", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

    def update_config(self, config: Dict[str, Any]):
        """Update configuration dictionary with current UI values."""
        for section, variables in self.parameter_vars.items():
            if section not in config:
                config[section] = {}
            
            if section == 'positional_axes':
                # Handle nested positional_axes structure
                for param, var in variables.items():
                    if param == 'mode':
                        config[section][param] = var.get()
                    elif param in ['e1', 'e2', 'e3', 'e4']:
                        # Handle axis-specific parameters (only enabled now, no amplitude)
                        if param not in config[section]:
                            config[section][param] = {}
                        for axis_param, axis_var in var.items():
                            if axis_param == 'enabled':
                                config[section][param][axis_param] = axis_var.get()
            else:
                # Handle regular flat structure
                for param, var in variables.items():
                    config[section][param] = var.get()

        # Update custom combine ratio controls
        for control_name, control in self.combine_ratio_controls.items():
            control._update_percentage_display()

        # Update embedded conversion tabs if they exist
        if hasattr(self, 'embedded_conversion_tabs'):
            try:
                # Update 1D to 2D conversion settings from embedded conversion tabs
                basic_config = self.embedded_conversion_tabs.get_basic_config()
                config['alpha_beta_generation']['algorithm'] = basic_config['algorithm']
                config['alpha_beta_generation']['points_per_second'] = basic_config['points_per_second']
                config['alpha_beta_generation']['min_distance_from_center'] = round(basic_config['min_distance_from_center'], 1)
                config['alpha_beta_generation']['speed_at_edge_hz'] = round(basic_config['speed_at_edge_hz'], 1)

                # Update prostate conversion settings
                prostate_config = self.embedded_conversion_tabs.get_prostate_config()
                if 'prostate_generation' not in config:
                    config['prostate_generation'] = {}
                config['prostate_generation']['generate_prostate_files'] = prostate_config['generate_prostate_files']
                config['prostate_generation']['generate_from_inverted'] = prostate_config['generate_from_inverted']
                config['prostate_generation']['algorithm'] = prostate_config['algorithm']
                config['prostate_generation']['points_per_second'] = prostate_config['points_per_second']
                config['prostate_generation']['min_distance_from_center'] = round(prostate_config['min_distance_from_center'], 1)
            except Exception:
                # Ignore errors if conversion tabs not properly initialized
                pass

    def update_display(self, config: Dict[str, Any]):
        """Update UI display with configuration values."""
        self.config = config
        for section, variables in self.parameter_vars.items():
            if section in config:
                if section == 'positional_axes':
                    # Handle nested positional_axes structure
                    for param, var in variables.items():
                        if param == 'mode' and param in config[section]:
                            var.set(config[section][param])
                        elif param in ['e1', 'e2', 'e3', 'e4'] and param in config[section]:
                            # Handle axis-specific parameters (only enabled now, no amplitude)
                            axis_config = config[section][param]
                            for axis_param, axis_var in var.items():
                                if axis_param == 'enabled' and axis_param in axis_config:
                                    axis_var.set(axis_config[axis_param])
                else:
                    # Handle regular flat structure
                    for param, var in variables.items():
                        if param in config[section]:
                            var.set(config[section][param])

        # Update custom combine ratio controls display
        for control_name, control in self.combine_ratio_controls.items():
            control._update_percentage_display()

        # Update ramp display if it exists
        if hasattr(self, 'ramp_value_label'):
            self._update_ramp_display()

        # Update embedded conversion tabs if they exist
        if hasattr(self, 'embedded_conversion_tabs'):
            try:
                # The conversion tabs will update themselves based on the config
                # when they access the config values
                pass
            except Exception:
                # Ignore errors if conversion tabs not properly initialized
                pass

        # Update Motion Axis display after config changes
        if hasattr(self, '_update_motion_axis_display'):
            self._update_motion_axis_display()

        # Update curve visualizations if they exist
        self._update_curve_visualizations()

    def _update_ramp_display(self, value=None):
        """Update the ramp value display with current value and per-minute calculation."""
        try:
            # Get current ramp value
            ramp_per_hour = int(self.parameter_vars['volume']['ramp_percent_per_hour'].get())

            # Calculate per-minute value
            ramp_per_minute = round(ramp_per_hour / 60.0, 2)

            # Update label text
            display_text = f"{ramp_per_hour}% per hour ({ramp_per_minute}% per minute)"
            self.ramp_value_label.config(text=display_text)
        except (KeyError, ValueError, AttributeError):
            # Handle case where variables aren't initialized yet
            pass