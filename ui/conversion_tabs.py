import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


class ConversionTabs:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config

        # Basic tab variables
        algorithm_value = config['alpha_beta_generation'].get('algorithm', 'circular')
        self.basic_algorithm_var = tk.StringVar(value=algorithm_value)
        points_per_second = config['alpha_beta_generation'].get('points_per_second', 25)
        self.basic_points_var = tk.IntVar(value=points_per_second)
        min_distance = config['alpha_beta_generation'].get('min_distance_from_center', 0.1)
        self.basic_min_distance_var = tk.DoubleVar(value=min_distance)
        speed_threshold = config['alpha_beta_generation'].get('speed_threshold_percent', 50)
        self.basic_speed_threshold_var = tk.IntVar(value=speed_threshold)
        direction_prob = config['alpha_beta_generation'].get('direction_change_probability', 0.1)
        self.basic_direction_prob_var = tk.DoubleVar(value=direction_prob)

        # Widget references for enabling/disabling
        self.basic_widgets = {}

        # Prostate tab variables
        prostate_config = config.get('prostate_generation', {})
        self.prostate_generate_var = tk.BooleanVar(value=prostate_config.get('generate_prostate_files', True))
        self.prostate_invert_var = tk.BooleanVar(value=prostate_config.get('generate_from_inverted', True))
        prostate_algorithm = prostate_config.get('algorithm', 'standard')
        self.prostate_algorithm_var = tk.StringVar(value=prostate_algorithm)
        prostate_points = prostate_config.get('points_per_second', 25)
        self.prostate_points_var = tk.IntVar(value=prostate_points)
        prostate_min_distance = prostate_config.get('min_distance_from_center', 0.5)
        self.prostate_min_distance_var = tk.DoubleVar(value=prostate_min_distance)

        self.setup_tabs()

    def setup_tabs(self):
        """Setup the tabbed interface for 1D to 2D conversion."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill='both', expand=True)

        # Basic conversion tab
        self.basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_frame, text="Basic")
        self.setup_basic_tab()

        # Prostate conversion tab
        self.prostate_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.prostate_frame, text="Prostate")
        self.setup_prostate_tab()

    def setup_basic_tab(self):
        """Setup the basic conversion tab."""
        # Algorithm selection
        ttk.Label(self.basic_frame, text="Algorithm:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # Create frame for radio buttons arranged in 2x2 grid
        algo_frame = ttk.Frame(self.basic_frame)
        algo_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Radiobutton(algo_frame, text="Top-Right-Bottom-Left (0°-270°)",
                       variable=self.basic_algorithm_var, value="top-right-left",
                       command=self._on_algorithm_change).grid(row=0, column=0, sticky=tk.W, padx=(0, 15), pady=1)
        ttk.Radiobutton(algo_frame, text="Circular (0°-180°)",
                       variable=self.basic_algorithm_var, value="circular",
                       command=self._on_algorithm_change).grid(row=0, column=1, sticky=tk.W, pady=1)
        ttk.Radiobutton(algo_frame, text="Top-Left-Bottom-Right (0°-90°)",
                       variable=self.basic_algorithm_var, value="top-left-right",
                       command=self._on_algorithm_change).grid(row=1, column=0, sticky=tk.W, padx=(0, 15), pady=1)
        ttk.Radiobutton(algo_frame, text="0-360 (restim original)",
                       variable=self.basic_algorithm_var, value="restim-original",
                       command=self._on_algorithm_change).grid(row=1, column=1, sticky=tk.W, pady=1)

        # Points per second
        self.basic_widgets['points_label'] = ttk.Label(self.basic_frame, text="Points Per Second:")
        self.basic_widgets['points_label'].grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.basic_widgets['points_entry'] = ttk.Entry(self.basic_frame, textvariable=self.basic_points_var, width=10)
        self.basic_widgets['points_entry'].grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.basic_widgets['points_desc'] = ttk.Label(self.basic_frame, text="(1-100) Interpolation density")
        self.basic_widgets['points_desc'].grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # Min Distance From Center
        self.basic_widgets['min_dist_label'] = ttk.Label(self.basic_frame, text="Min Distance From Center:")
        self.basic_widgets['min_dist_label'].grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.basic_widgets['min_dist_scale'] = ttk.Scale(self.basic_frame, from_=0.1, to=0.9,
                                                          variable=self.basic_min_distance_var,
                                                          orient=tk.HORIZONTAL, length=150)
        self.basic_widgets['min_dist_scale'].grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.basic_widgets['min_dist_desc'] = ttk.Label(self.basic_frame, text="(0.1-0.9) Minimum radius from center")
        self.basic_widgets['min_dist_desc'].grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # Speed Threshold (%)
        self.basic_widgets['speed_label'] = ttk.Label(self.basic_frame, text="Speed Threshold (%):")
        self.basic_widgets['speed_label'].grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.basic_widgets['speed_scale'] = ttk.Scale(self.basic_frame, from_=0, to=100,
                                                       variable=self.basic_speed_threshold_var,
                                                       orient=tk.HORIZONTAL, length=150)
        self.basic_widgets['speed_scale'].grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.basic_widgets['speed_desc'] = ttk.Label(self.basic_frame, text="(0-100%) Speed percentile for maximum radius")
        self.basic_widgets['speed_desc'].grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # Direction Change Probability (for restim-original only)
        self.basic_widgets['direction_label'] = ttk.Label(self.basic_frame, text="Direction Change Probability:")
        self.basic_widgets['direction_label'].grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)

        # Frame to hold slider and value display
        direction_frame = ttk.Frame(self.basic_frame)
        direction_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.basic_widgets['direction_scale'] = ttk.Scale(direction_frame, from_=0.0, to=1.0,
                                                            variable=self.basic_direction_prob_var,
                                                            orient=tk.HORIZONTAL, length=120)
        self.basic_widgets['direction_scale'].pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Value display label
        self.basic_widgets['direction_value'] = ttk.Label(direction_frame, text=f"{self.basic_direction_prob_var.get():.2f}", width=5)
        self.basic_widgets['direction_value'].pack(side=tk.LEFT, padx=(5, 0))

        self.basic_widgets['direction_desc'] = ttk.Label(self.basic_frame, text="(0.0-1.0) Probability of direction flip per segment")
        self.basic_widgets['direction_desc'].grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        # Add trace to update value display when slider changes
        self.basic_direction_prob_var.trace_add('write', self._update_direction_value_display)

        # Convert to 2D button
        self.basic_convert_button = ttk.Button(self.basic_frame, text="Convert to 2D", command=self.convert_basic_2d)
        self.basic_convert_button.grid(row=5, column=0, columnspan=3, pady=10)

        # Configure grid weights
        self.basic_frame.columnconfigure(1, weight=1)

        # Initialize widget states based on current algorithm
        self._on_algorithm_change()

    def setup_prostate_tab(self):
        """Setup the prostate conversion tab."""
        # Generate prostate files checkbox
        ttk.Checkbutton(self.prostate_frame, text="Generate prostate files",
                       variable=self.prostate_generate_var).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        # Generate from inverted checkbox
        ttk.Checkbutton(self.prostate_frame, text="Generate from inverted funscript",
                       variable=self.prostate_invert_var).grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # Algorithm selection
        ttk.Label(self.prostate_frame, text="Algorithm:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        # Create frame for radio buttons arranged vertically
        algo_frame = ttk.Frame(self.prostate_frame)
        algo_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Radiobutton(algo_frame, text="Standard (0°-180°)",
                       variable=self.prostate_algorithm_var, value="standard").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(algo_frame, text="Tear-shaped (0°-180°)",
                       variable=self.prostate_algorithm_var, value="tear-shaped").pack(anchor=tk.W, pady=1)

        # Points per second
        ttk.Label(self.prostate_frame, text="Points Per Second:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        points_entry = ttk.Entry(self.prostate_frame, textvariable=self.prostate_points_var, width=10)
        points_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self.prostate_frame, text="(1-100) Interpolation density").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # Min Distance From Center
        ttk.Label(self.prostate_frame, text="Min Distance From Center:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        min_distance_scale = ttk.Scale(self.prostate_frame, from_=0.3, to=0.9, variable=self.prostate_min_distance_var,
                                      orient=tk.HORIZONTAL, length=150)
        min_distance_scale.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(self.prostate_frame, text="(0.3-0.9) Distance for tear-shaped constant zone").grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        # Convert to 2D button
        self.prostate_convert_button = ttk.Button(self.prostate_frame, text="Convert to 2D", command=self.convert_prostate_2d)
        self.prostate_convert_button.grid(row=5, column=0, columnspan=3, pady=10)

        # Configure grid weights
        self.prostate_frame.columnconfigure(1, weight=1)

    def convert_basic_2d(self):
        """Trigger basic 2D conversion."""
        # This will be connected to the main window's conversion function
        if hasattr(self, 'basic_conversion_callback'):
            self.basic_conversion_callback()

    def convert_prostate_2d(self):
        """Trigger prostate 2D conversion."""
        # This will be connected to the main window's conversion function
        if hasattr(self, 'prostate_conversion_callback'):
            self.prostate_conversion_callback()

    def set_conversion_callbacks(self, basic_callback, prostate_callback):
        """Set callback functions for conversion buttons."""
        self.basic_conversion_callback = basic_callback
        self.prostate_conversion_callback = prostate_callback

    def set_button_state(self, state):
        """Set the state of both conversion buttons."""
        self.basic_convert_button.config(state=state)
        self.prostate_convert_button.config(state=state)

    def _update_direction_value_display(self, *args):
        """Update the direction change probability value display."""
        if 'direction_value' in self.basic_widgets:
            value = self.basic_direction_prob_var.get()
            self.basic_widgets['direction_value'].config(text=f"{value:.2f}")

    def _on_algorithm_change(self):
        """Update widget states based on selected algorithm."""
        algorithm = self.basic_algorithm_var.get()
        is_restim = (algorithm == "restim-original")

        # Widgets to disable for restim-original
        standard_widgets = [
            'points_label', 'points_entry', 'points_desc',
            'min_dist_label', 'min_dist_scale', 'min_dist_desc',
            'speed_label', 'speed_scale', 'speed_desc'
        ]

        # Widgets to enable only for restim-original
        restim_widgets = [
            'direction_label', 'direction_scale', 'direction_desc', 'direction_value'
        ]

        # Set state for standard algorithm widgets
        state = 'disabled' if is_restim else 'normal'
        for widget_name in standard_widgets:
            if widget_name in self.basic_widgets:
                widget = self.basic_widgets[widget_name]
                if isinstance(widget, (ttk.Entry, ttk.Scale)):
                    widget.config(state=state)
                # Labels don't need state change but could be grayed out
                # For now just disable interactive widgets

        # Set state for restim-specific widgets
        restim_state = 'normal' if is_restim else 'disabled'
        for widget_name in restim_widgets:
            if widget_name in self.basic_widgets:
                widget = self.basic_widgets[widget_name]
                if isinstance(widget, (ttk.Entry, ttk.Scale)):
                    widget.config(state=restim_state)

    def get_basic_config(self):
        """Get current basic conversion configuration."""
        return {
            'algorithm': self.basic_algorithm_var.get(),
            'points_per_second': self.basic_points_var.get(),
            'min_distance_from_center': self.basic_min_distance_var.get(),
            'speed_threshold_percent': self.basic_speed_threshold_var.get(),
            'direction_change_probability': self.basic_direction_prob_var.get()
        }

    def get_prostate_config(self):
        """Get current prostate conversion configuration."""
        return {
            'generate_prostate_files': self.prostate_generate_var.get(),
            'generate_from_inverted': self.prostate_invert_var.get(),
            'algorithm': self.prostate_algorithm_var.get(),
            'points_per_second': self.prostate_points_var.get(),
            'min_distance_from_center': self.prostate_min_distance_var.get()
        }