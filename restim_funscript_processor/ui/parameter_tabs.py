import tkinter as tk
from tkinter import ttk
from typing import Dict, Any


class ParameterTabs(ttk.Notebook):
    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)

        self.config = config
        self.parameter_vars = {}

        self.setup_tabs()

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

    def setup_speed_tab(self):
        """Setup the Speed parameters tab."""
        frame = self.speed_frame
        self.parameter_vars['speed'] = {}
        self.parameter_vars['alpha_beta_generation'] = {}

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

        row += 2

        # Alpha/Beta Generation section
        ttk.Label(frame, text="Alpha/Beta Generation:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Auto Generate Alpha/Beta
        var = tk.BooleanVar(value=self.config['alpha_beta_generation']['auto_generate'])
        self.parameter_vars['alpha_beta_generation']['auto_generate'] = var
        ttk.Checkbutton(frame, text="Auto-generate alpha/beta files when missing", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Points Per Second
        ttk.Label(frame, text="Points Per Second:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['alpha_beta_generation']['points_per_second'])
        self.parameter_vars['alpha_beta_generation']['points_per_second'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-100) Interpolation density for alpha/beta generation").grid(row=row, column=2, sticky=tk.W, padx=5)

    def setup_frequency_tab(self):
        """Setup the Frequency parameters tab."""
        frame = self.frequency_frame
        self.parameter_vars['frequency'] = {}

        row = 0

        # Alpha Frequency Min
        ttk.Label(frame, text="Alpha Frequency Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['alpha_freq_min'])
        self.parameter_vars['frequency']['alpha_freq_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum mapping for alpha to pulse frequency").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Alpha Frequency Max
        ttk.Label(frame, text="Alpha Frequency Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['alpha_freq_max'])
        self.parameter_vars['frequency']['alpha_freq_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum mapping for alpha to pulse frequency").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Frequency Ramp Combine Ratio
        ttk.Label(frame, text="Frequency Ramp Combine Ratio:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['frequency']['frequency_ramp_combine_ratio'])
        self.parameter_vars['frequency']['frequency_ramp_combine_ratio'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-10) Ratio for combining frequency and ramp").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Pulse Frequency Combine Ratio
        ttk.Label(frame, text="Pulse Frequency Combine Ratio:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['frequency']['pulse_frequency_combine_ratio'])
        self.parameter_vars['frequency']['pulse_frequency_combine_ratio'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-10) Ratio for combining speed with alpha-based frequency").grid(row=row, column=2, sticky=tk.W, padx=5)

    def setup_volume_tab(self):
        """Setup the Volume parameters tab."""
        frame = self.volume_frame
        self.parameter_vars['volume'] = {}

        row = 0

        # Volume Ramp Combine Ratio
        ttk.Label(frame, text="Volume Ramp Combine Ratio:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['volume_ramp_combine_ratio'])
        self.parameter_vars['volume']['volume_ramp_combine_ratio'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1.0-10.0) Ratio for combining volume and ramp").grid(row=row, column=2, sticky=tk.W, padx=5)

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

        # Pulse Width Combine Ratio
        ttk.Label(frame, text="Pulse Width Combine Ratio:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['pulse']['pulse_width_combine_ratio'])
        self.parameter_vars['pulse']['pulse_width_combine_ratio'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-10) Ratio for combining pulse width components").grid(row=row, column=2, sticky=tk.W, padx=5)

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
        ttk.Label(frame, text="Pulse Rise Combine Ratio:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['pulse']['pulse_rise_combine_ratio'])
        self.parameter_vars['pulse']['pulse_rise_combine_ratio'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1-10) Ratio for pulse rise time combining").grid(row=row, column=2, sticky=tk.W, padx=5)

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
        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(Leave empty to use input file directory)").grid(row=row, column=2, sticky=tk.W, padx=5)

    def update_config(self, config: Dict[str, Any]):
        """Update configuration dictionary with current UI values."""
        for section, variables in self.parameter_vars.items():
            if section not in config:
                config[section] = {}
            for param, var in variables.items():
                config[section][param] = var.get()

    def update_display(self, config: Dict[str, Any]):
        """Update UI display with configuration values."""
        self.config = config
        for section, variables in self.parameter_vars.items():
            if section in config:
                for param, var in variables.items():
                    if param in config[section]:
                        var.set(config[section][param])