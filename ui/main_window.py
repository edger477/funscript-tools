import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import traceback
import sys
from pathlib import Path
from typing import Optional

try:
    from tkinterdnd2 import TkinterDnD, DND_ALL
    HAS_DND = True
except ImportError:
    HAS_DND = False

sys.path.append(str(Path(__file__).parent.parent))
from config import ConfigManager
from processor import RestimProcessor
from ui.parameter_tabs import ParameterTabs
from ui.conversion_tabs import ConversionTabs
from ui.custom_events_builder import CustomEventsBuilderDialog
import ui.theme as _theme


class MainWindow:
    def __init__(self):
        # Use TkinterDnD for drag-and-drop support if available
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
        self.root.title("Restim Funscript Processor")
        self.root.geometry("850x735")
        self.root.resizable(True, True)

        # Configuration
        self.config_manager = ConfigManager()
        self.current_config = self.config_manager.get_config()

        # Variables
        self.input_file_var = tk.StringVar()
        self.input_files = []  # Store list of selected files for batch processing
        self.last_processed_filename = None  # Track last processed filename for auto-loading events
        self.last_processed_directory = None  # Track directory of last processed file

        # Progress tracking
        self.progress_var = tk.IntVar()
        self.status_var = tk.StringVar(value="Ready to process...")

        self.setup_ui()
        self.update_config_display()
        dark = self.current_config.get('ui', {}).get('dark_mode', False)
        _theme.apply(dark)
        if dark:
            self._dark_btn.config(text='\u2600 Light')
            self.drop_zone.config(bg='#2d2d3f')

    def setup_ui(self):
        """Setup the main user interface."""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help Contents", command=self._open_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._open_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Input file selection with drop zone
        input_frame = ttk.LabelFrame(main_frame, text="Input File (drop .funscript files here)", padding="5")
        input_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(1, weight=1)

        # Create a visible drop zone using tk.Frame (not ttk) for better DnD support
        self.drop_zone = tk.Frame(input_frame, bg='#f0f0f0', relief='sunken', bd=1)
        self.drop_zone.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=2, pady=2)
        self.drop_zone.columnconfigure(1, weight=1)

        ttk.Label(self.drop_zone, text="File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.input_entry = ttk.Entry(self.drop_zone, textvariable=self.input_file_var, width=50)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Button(self.drop_zone, text="Browse...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)

        row += 1

        # Variants bar: A/B/C/D snapshots of the whole config. Switching
        # slots auto-saves the current UI state into the slot you're
        # leaving, then loads the new slot and refreshes all tabs.
        self._build_variants_bar(main_frame, row)
        row += 1

        # Parameters frame (1D to 2D conversion is now in Motion Axis tab)
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        params_frame.columnconfigure(0, weight=1)
        params_frame.rowconfigure(0, weight=1)

        # Parameter tabs
        self.parameter_tabs = ParameterTabs(params_frame, self.current_config)
        self.parameter_tabs.main_window = self
        self.parameter_tabs.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Set callback for mode changes (for future extensibility)
        self.parameter_tabs.set_mode_change_callback(self.on_mode_change)

        # Set conversion callbacks for embedded conversion tabs
        self.parameter_tabs.set_conversion_callbacks(self.convert_basic_2d, self.convert_prostate_2d)

        row += 1

        # Progress and status frame
        status_frame = ttk.LabelFrame(main_frame, text="Output Status", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Status label
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W, pady=5)

        # Scrollable buttons frame
        buttons_outer = ttk.Frame(status_frame)
        buttons_outer.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        buttons_outer.columnconfigure(0, weight=1)

        buttons_canvas = tk.Canvas(buttons_outer, height=40, highlightthickness=0)
        buttons_scrollbar = ttk.Scrollbar(buttons_outer, orient=tk.HORIZONTAL, command=buttons_canvas.xview)
        buttons_frame = ttk.Frame(buttons_canvas)

        buttons_frame.bind("<Configure>", lambda e: buttons_canvas.configure(scrollregion=buttons_canvas.bbox("all")))
        buttons_canvas.create_window((0, 0), window=buttons_frame, anchor="nw")
        buttons_canvas.configure(xscrollcommand=buttons_scrollbar.set)

        buttons_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        buttons_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.process_button = ttk.Button(buttons_frame, text="Process All Files", command=self.start_processing)
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))

        self.process_motion_button = ttk.Button(buttons_frame, text="Process Motion Files", command=self.start_motion_processing)
        self.process_motion_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(buttons_frame, text="Custom Event Builder", command=self.open_custom_events_builder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Animation Viewer", command=self._open_animation_viewer).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Signal Analyzer", command=self._open_signal_analyzer).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Compare Funscripts", command=self._open_compare_viewer).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Shaft Viewer", command=self._open_shaft_viewer).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Trochoid Viewer", command=self._open_trochoid_viewer).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(buttons_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Save Preset", command=self.save_config_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Load Preset", command=self.load_config_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_config).pack(side=tk.LEFT, padx=(0, 10))

        self._dark_btn = ttk.Button(buttons_frame, text='\u263d Dark', width=8, command=self._toggle_dark_mode)
        self._dark_btn.pack(side=tk.LEFT)

        # Configure main_frame row weights
        main_frame.rowconfigure(row-1, weight=1)  # Parameters frame gets extra space

        # Enable drag-and-drop if available
        if HAS_DND:
            try:
                # Register drop target on the drop zone frame and entry widget
                for widget in (self.drop_zone, self.input_entry):
                    widget.drop_target_register(DND_ALL)
                    widget.dnd_bind('<<Drop>>', self.handle_drop)
                    widget.dnd_bind('<<DragEnter>>', self.on_drag_enter)
                    widget.dnd_bind('<<DragLeave>>', self.on_drag_leave)
            except Exception as e:
                pass  # Silently fail if drag-and-drop setup fails



    def open_custom_events_builder(self):
        """Open the new visual custom events builder."""
        import datetime
        log_path = Path(sys.executable).parent / 'custom_events.log'
        def log(msg):
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
            except Exception:
                pass
        try:
            log("Opening Custom Event Builder")
            log(f"  last_processed_filename={self.last_processed_filename}")
            log(f"  last_processed_directory={self.last_processed_directory}")
            dialog = CustomEventsBuilderDialog(
                self.root,
                self.current_config,
                self.last_processed_filename,
                self.last_processed_directory
            )
            log("Dialog created successfully")
            self.root.wait_window(dialog)
            log("Dialog closed")
        except Exception:
            tb = traceback.format_exc()
            log(f"EXCEPTION:\n{tb}")
            messagebox.showerror(
                "Custom Event Builder Error",
                f"Failed to open Custom Event Builder:\n\n{tb}",
                parent=self.root
            )

    def _open_animation_viewer(self):
        """Open the animated 2D trajectory + electrode intensity viewer."""
        # Update config from current UI state before opening
        self.parameter_tabs.update_config(self.current_config)
        from ui.animation_viewer import AnimationViewer
        AnimationViewer(self.root, self)

    def _open_signal_analyzer(self):
        """Open the signal analyzer to examine the loaded funscript."""
        self.parameter_tabs.update_config(self.current_config)
        from ui.signal_analyzer import SignalAnalyzer
        SignalAnalyzer(self.root, self)

    def _open_compare_viewer(self):
        """Open the dual-timeline comparison viewer.

        Pre-fills slot A with the currently selected input file (if any)
        so the common case (compare original vs processed output) is one
        click away. Slot B is left empty for the user to browse.
        """
        from ui.compare_viewer import CompareViewer
        first_file = None
        if hasattr(self, 'input_files') and self.input_files:
            first_file = self.input_files[0]
        CompareViewer(self.root, file_a=first_file)

    def _open_shaft_viewer(self):
        """Open the Shaft Viewer (cylinder with E1-E4 along the length).

        Syncs current UI settings into current_config first so the viewer's
        'auto' mode and 'Apply trochoid quantization' default reflect
        whatever is actively selected in the tabs.
        """
        self.parameter_tabs.update_config(self.current_config)
        from ui.shaft_viewer import ShaftViewer
        ShaftViewer(self.root, self)

    def _open_trochoid_viewer(self):
        """Open the Trochoid Viewer — 2D trochoid curve on the left,
        its shadow projected onto the shaft on the right. The pen on
        the curve is driven by the funscript y value; the shadow is
        the normalized x/y/radius projection of that point.
        """
        self.parameter_tabs.update_config(self.current_config)
        from ui.trochoid_viewer import TrochoidViewer
        TrochoidViewer(self.root, self)

    def _open_help(self):
        """Open the built-in help viewer."""
        from ui.help_viewer import HelpViewer
        HelpViewer(self.root)

    def _open_about(self):
        """Show about dialog."""
        from version import __version__, __app_name__, __url__
        from tkinter import messagebox
        messagebox.showinfo(
            "About",
            f"{__app_name__} v{__version__}\n\n"
            f"Converts .funscript files into e-stim control signals\n"
            f"for use with restim.\n\n"
            f"{__url__}",
            parent=self.root)

    def _toggle_dark_mode(self):
        _theme.toggle()
        dark = _theme.is_dark()
        self._dark_btn.config(text='\u2600 Light' if dark else '\u263d Dark')
        self.drop_zone.config(bg='#2d2d3f' if dark else '#f0f0f0')
        # Persist preference
        self.current_config.setdefault('ui', {})['dark_mode'] = dark
        self.save_config()

    def on_mode_change(self, mode):
        """Called when positional axis mode changes."""
        # Mode changes are now handled within the Motion Axis tab
        pass




    def browse_input_file(self):
        """Open file dialog to select input funscript file(s)."""
        file_paths = filedialog.askopenfilenames(
            title="Select Funscript File(s)",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")]
        )
        if file_paths:
            self.input_files = list(file_paths)
            # Update display with count of selected files
            if len(self.input_files) == 1:
                self.input_file_var.set(self.input_files[0])
            else:
                self.input_file_var.set(f"{len(self.input_files)} files selected")

    def on_drag_enter(self, event):
        """Visual feedback when dragging over drop zone."""
        self.drop_zone.config(bg='#d4edda')  # Light green
        return event.action

    def on_drag_leave(self, event):
        """Reset visual feedback when leaving drop zone."""
        self.drop_zone.config(bg='#f0f0f0')  # Original color
        return event.action

    def handle_drop(self, event):
        """Handle files dropped onto the window. Only accepts .funscript files."""
        # Reset drop zone color
        self.drop_zone.config(bg='#f0f0f0')
        # Parse dropped file paths - tkinterdnd2 returns space-separated paths
        # with curly braces around paths containing spaces
        dropped_data = event.data

        # Parse the dropped data - handles paths with spaces (wrapped in {})
        file_paths = []
        current_path = ""
        in_braces = False

        for char in dropped_data:
            if char == '{':
                in_braces = True
            elif char == '}':
                in_braces = False
                if current_path:
                    file_paths.append(current_path)
                    current_path = ""
            elif char == ' ' and not in_braces:
                if current_path:
                    file_paths.append(current_path)
                    current_path = ""
            else:
                current_path += char

        # Don't forget the last path if not in braces
        if current_path:
            file_paths.append(current_path)

        # Filter to only .funscript files
        funscript_files = [
            path for path in file_paths
            if path.lower().endswith('.funscript') and Path(path).exists()
        ]

        if funscript_files:
            self.input_files = funscript_files
            # Update display with count of selected files
            if len(self.input_files) == 1:
                self.input_file_var.set(self.input_files[0])
            else:
                self.input_file_var.set(f"{len(self.input_files)} files selected")
        elif file_paths:
            # Files were dropped but none were .funscript
            messagebox.showwarning(
                "Invalid Files",
                "Only .funscript files are accepted. Please drop .funscript files."
            )

    def convert_basic_2d(self):
        """Convert 1D funscript to 2D alpha/beta files using basic algorithms."""
        self._convert_2d('basic')

    def convert_prostate_2d(self):
        """Convert 1D funscript to 2D alpha-prostate/beta-prostate files."""
        self._convert_2d('prostate')

    def _convert_2d(self, conversion_type):
        """Common 2D conversion logic."""
        input_file = self.input_file_var.get().strip()

        if not input_file:
            messagebox.showerror("Error", "Please select an input file first.")
            return

        if not Path(input_file).exists():
            messagebox.showerror("Error", "Input file does not exist.")
            return

        if not input_file.lower().endswith('.funscript'):
            messagebox.showerror("Error", "Input file must be a .funscript file.")
            return

        # Disable the convert buttons during processing
        if hasattr(self.parameter_tabs, 'embedded_conversion_tabs'):
            self.parameter_tabs.embedded_conversion_tabs.set_button_state('disabled')

        # Start conversion in background thread
        conversion_thread = threading.Thread(target=self._perform_2d_conversion, args=(conversion_type,), daemon=True)
        conversion_thread.start()


    def _perform_2d_conversion(self, conversion_type):
        """Perform 2D conversion in background thread."""
        try:
            input_file = self.input_file_var.get().strip()
            input_path = Path(input_file)

            self.update_progress(10, "Loading input file...")

            # Import necessary modules
            from funscript import Funscript

            # Load main funscript
            main_funscript = Funscript.from_file(input_path)

            self.update_progress(30, "Converting to 2D...")

            # Determine which conversion_tabs to use (always use embedded 3P tab)
            if hasattr(self.parameter_tabs, 'embedded_conversion_tabs'):
                conversion_tabs = self.parameter_tabs.embedded_conversion_tabs
            else:
                conversion_tabs = self.conversion_tabs

            # Determine output directory - respect file_management mode (central vs local)
            file_mgmt = self.current_config.get('file_management', {})
            if file_mgmt.get('mode') == 'central':
                central_path = file_mgmt.get('central_folder_path', '').strip()
                if central_path:
                    output_dir = Path(central_path)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = input_path.parent  # fallback if central path not set
            else:
                output_dir = input_path.parent

            if conversion_type == 'basic':
                from processing.funscript_1d_to_2d import generate_alpha_beta_from_main

                # Get basic conversion parameters
                config = conversion_tabs.get_basic_config()

                # Generate speed funscript (required for radius scaling)
                from processing.speed_processing import convert_to_speed
                speed_funscript = convert_to_speed(
                    main_funscript,
                    self.current_config['general']['speed_window_size'],
                    self.current_config['speed']['interpolation_interval']
                )

                # Generate alpha and beta files
                alpha_funscript, beta_funscript = generate_alpha_beta_from_main(
                    main_funscript, speed_funscript, config['points_per_second'], config['algorithm'],
                    config['min_distance_from_center'], config['speed_threshold_percent'],
                    config['direction_change_probability']
                )

                # Save files
                filename_only = input_path.stem
                alpha_path = output_dir / f"{filename_only}.alpha.funscript"
                beta_path = output_dir / f"{filename_only}.beta.funscript"

                alpha_funscript.save_to_path(alpha_path)
                beta_funscript.save_to_path(beta_path)

                success_message = f"Basic conversion complete! Created {alpha_path.name} and {beta_path.name}"
                files_created = [alpha_path.name, beta_path.name]

            elif conversion_type == 'prostate':
                from processing.funscript_prostate_2d import generate_alpha_beta_prostate_from_main

                # Get prostate conversion parameters
                config = conversion_tabs.get_prostate_config()

                # Generate alpha-prostate and beta-prostate files
                alpha_prostate_funscript, beta_prostate_funscript = generate_alpha_beta_prostate_from_main(
                    main_funscript, config['points_per_second'], config['algorithm'],
                    config['min_distance_from_center'], config['generate_from_inverted']
                )

                # Save files
                filename_only = input_path.stem
                alpha_prostate_path = output_dir / f"{filename_only}.alpha-prostate.funscript"
                beta_prostate_path = output_dir / f"{filename_only}.beta-prostate.funscript"

                alpha_prostate_funscript.save_to_path(alpha_prostate_path)
                beta_prostate_funscript.save_to_path(beta_prostate_path)

                success_message = f"Prostate conversion complete! Created {alpha_prostate_path.name} and {beta_prostate_path.name}"
                files_created = [alpha_prostate_path.name, beta_prostate_path.name]

            self.update_progress(70, "Saving output files...")
            self.update_progress(100, success_message)

            # Show success message
            files_list = "\n".join([f"• {filename}" for filename in files_created])
            self.root.after(100, lambda: messagebox.showinfo("Success",
                f"2D conversion completed successfully!\n\nCreated files:\n{files_list}"))

        except Exception as e:
            error_msg = f"2D conversion failed: {str(e)}"
            self.update_progress(-1, error_msg)
            self.root.after(100, lambda: messagebox.showerror("Error", error_msg))

        finally:
            # Re-enable the convert buttons
            if hasattr(self.parameter_tabs, 'embedded_conversion_tabs'):
                self.root.after(100, lambda: self.parameter_tabs.embedded_conversion_tabs.set_button_state('normal'))

    def _generate_motion_axis_files(self, input_path: Path):
        """Generate motion axis files (E1-E4) based on current configuration."""
        try:
            self.update_progress(30, "Loading input file...")

            # Import necessary modules
            from funscript import Funscript
            from processing.motion_axis_generation import generate_motion_axes

            # Load main funscript
            main_funscript = Funscript.from_file(input_path)

            self.update_progress(50, "Generating motion axis files...")

            # Get motion axis configuration
            motion_config = self.current_config['positional_axes']

            # Determine output directory - respect file_management mode (central vs local)
            file_mgmt = self.current_config.get('file_management', {})
            if file_mgmt.get('mode') == 'central':
                central_path = file_mgmt.get('central_folder_path', '').strip()
                if central_path:
                    output_dir = Path(central_path)
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = input_path.parent  # fallback if central path not set
            else:
                output_dir = input_path.parent

            # Generate motion axis files
            generated_files = generate_motion_axes(
                main_funscript,
                motion_config,
                output_dir,
                input_path.stem  # Use input filename without extension
            )

            self.update_progress(80, "Saving motion axis files...")

            if generated_files:
                # Create success message with list of generated files
                files_list = "\n".join([f"• {path.name}" for path in generated_files.values()])
                success_message = f"Motion axis generation complete! Created {len(generated_files)} files."

                self.update_progress(100, success_message)

                # Show success message
                self.root.after(100, lambda: messagebox.showinfo("Success",
                    f"Motion axis files generated successfully!\n\nCreated files:\n{files_list}"))

            else:
                # No files were generated (all axes disabled)
                warning_message = "No motion axis files generated - all axes are disabled."
                self.update_progress(100, warning_message)
                self.root.after(100, lambda: messagebox.showwarning("No Files Generated",
                    "No motion axis files were generated because all axes (E1-E4) are disabled.\n\n"
                    "Enable at least one axis in the Motion Axis tab to generate files."))

        except Exception as e:
            error_msg = f"Motion axis generation failed: {str(e)}"
            self.update_progress(-1, error_msg)
            self.root.after(100, lambda: messagebox.showerror("Error", error_msg))
            raise  # Re-raise to be caught by the calling method

    def update_config_from_ui(self):
        """Update configuration with current UI values."""
        # Update all parameters from parameter tabs (which now includes embedded conversion tabs)
        self.parameter_tabs.update_config(self.current_config)

    def update_config_display(self):
        """Update UI display with current configuration values."""
        # The conversion tabs will handle their own display updates
        # since they manage their own variables internally

        # Parameter tabs now handle all parameters including processing options
        self.parameter_tabs.update_display(self.current_config)

    def save_config(self):
        """Save current configuration to file."""
        self.update_config_from_ui()
        if self.config_manager.update_config(self.current_config):
            if self.config_manager.save_config():
                messagebox.showinfo("Configuration", "Configuration saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save configuration file.")
        else:
            messagebox.showerror("Error", "Invalid configuration values.")

    def save_config_preset(self):
        """Save current configuration to a named preset file."""
        import json
        self.update_config_from_ui()
        path = filedialog.asksaveasfilename(
            title="Save Configuration Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.home() / "Documents"),
            initialfile="restim_preset.json"
        )
        if not path:
            return
        try:
            with open(path, 'w') as f:
                json.dump(self.current_config, f, indent=2)
            messagebox.showinfo("Preset Saved", f"Configuration preset saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset:\n{e}")

    def load_config_preset(self):
        """Load configuration from a preset file."""
        import json
        path = filedialog.askopenfilename(
            title="Load Configuration Preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.home() / "Documents")
        )
        if not path:
            return
        try:
            with open(path, 'r') as f:
                loaded = json.load(f)
            if self.config_manager.update_config(loaded):
                self.current_config = self.config_manager.get_config()
                self.update_config_display()
                messagebox.showinfo("Preset Loaded", f"Configuration loaded from:\n{Path(path).name}")
            else:
                messagebox.showerror("Error", "Preset file contains invalid configuration values.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON file.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset:\n{e}")

    def reset_config(self):
        """Reset configuration to defaults."""
        if messagebox.askyesno("Reset Configuration", "Reset all parameters to default values?"):
            self.config_manager.reset_to_defaults()
            self.current_config = self.config_manager.get_config()
            self.update_config_display()
            if hasattr(self, '_variant_active_var'):
                self._refresh_variants_bar()

    # ─────────────────────────────────────────────────────────────
    # Variants: 4-slot (A/B/C/D) whole-config snapshots for A/B test.
    # ─────────────────────────────────────────────────────────────

    _VARIANT_SLOTS = ('A', 'B', 'C', 'D')

    def _build_variants_bar(self, parent, row):
        """Compact top-bar widget: active-slot radio group, enabled
        checkboxes, save-to-slot button, and process-all action."""
        bar = ttk.LabelFrame(
            parent,
            text="Variants — A/B test whole-config snapshots",
            padding=(8, 4))
        bar.grid(row=row, column=0, columnspan=3,
                 sticky=(tk.W, tk.E), pady=(0, 4))

        self._variants_ensure_slots()
        v_cfg = self.current_config['variants']
        self._variant_active_var = tk.StringVar(value=str(v_cfg.get('active', 'A')))
        self._variant_enabled_vars = {}

        # Everything lives in a single inner frame anchored LEFT so the
        # A/B/C/D groups stay clustered together regardless of the
        # window width.
        inner = ttk.Frame(bar)
        inner.pack(side=tk.LEFT, fill=tk.X, expand=False)

        ttk.Label(inner, text="Active:").pack(side=tk.LEFT, padx=(0, 6))

        self._variant_radios = {}
        for slot in self._VARIANT_SLOTS:
            rb = ttk.Radiobutton(
                inner, text=slot,
                variable=self._variant_active_var, value=slot,
                command=lambda s=slot: self._variant_switch_to(s))
            rb.pack(side=tk.LEFT, padx=(0, 4))
            self._variant_radios[slot] = rb

        ttk.Separator(inner, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(inner, text="Enabled:").pack(side=tk.LEFT, padx=(0, 4))
        for slot in self._VARIANT_SLOTS:
            slot_cfg = v_cfg['slots'][slot]
            var = tk.BooleanVar(value=bool(slot_cfg.get('enabled', False)))
            self._variant_enabled_vars[slot] = var
            ttk.Checkbutton(
                inner, text=slot, variable=var,
                command=lambda s=slot: self._variant_set_enabled(s)
            ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Separator(inner, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(inner, text="Save current to active slot",
                   command=self._variant_save_current).pack(
            side=tk.LEFT, padx=(0, 6))
        ttk.Button(inner, text="Process all enabled variants",
                   command=self.start_processing_all_variants).pack(
            side=tk.LEFT, padx=(0, 4))

    def _variants_ensure_slots(self):
        """Guarantee the variants block exists with all 4 slots."""
        v = self.current_config.setdefault('variants', {})
        v.setdefault('active', 'A')
        slots = v.setdefault('slots', {})
        for s in self._VARIANT_SLOTS:
            slot = slots.setdefault(s, {})
            slot.setdefault('label', s)
            slot.setdefault('enabled', s == 'A')
            slot.setdefault('config', {})

    def _refresh_variants_bar(self):
        """Resync the bar's widgets with self.current_config after a
        config swap or reset."""
        self._variants_ensure_slots()
        v = self.current_config['variants']
        try:
            self._variant_active_var.set(str(v.get('active', 'A')))
        except tk.TclError:
            pass
        for s in self._VARIANT_SLOTS:
            try:
                self._variant_enabled_vars[s].set(
                    bool(v['slots'][s].get('enabled', False)))
            except (tk.TclError, KeyError):
                pass

    def _variant_snapshot_current(self) -> dict:
        """Take a copy of current_config minus the variants block
        itself, so slot-configs don't recursively nest variants."""
        import copy
        self.update_config_from_ui()  # capture any pending UI edits
        snap = copy.deepcopy(self.current_config)
        snap.pop('variants', None)
        return snap

    def _variant_save_current(self):
        """Manual save: push current UI state into the active slot."""
        self._variants_ensure_slots()
        active = str(self._variant_active_var.get())
        snap = self._variant_snapshot_current()
        self.current_config['variants']['slots'][active]['config'] = snap
        self.current_config['variants']['active'] = active
        self.status_var.set(f"Variant {active} saved.")

    def _variant_set_enabled(self, slot: str):
        self._variants_ensure_slots()
        try:
            val = bool(self._variant_enabled_vars[slot].get())
        except tk.TclError:
            val = False
        self.current_config['variants']['slots'][slot]['enabled'] = val

    def _variant_switch_to(self, new_slot: str):
        """Auto-save the leaving slot, then load `new_slot`'s config.

        If the target slot has an empty config (never populated), we
        treat the current UI as its starting point — the first time
        you switch to an empty slot it inherits whatever you had.
        """
        import copy
        self._variants_ensure_slots()
        v = self.current_config['variants']
        leaving = str(v.get('active', 'A'))

        # 1. Snapshot current UI into the leaving slot.
        leaving_snap = self._variant_snapshot_current()
        v['slots'][leaving]['config'] = leaving_snap

        # 2. Load target slot. Empty slot -> inherit current.
        target = v['slots'].get(new_slot, {})
        target_cfg = target.get('config') or {}
        if not target_cfg:
            target_cfg = copy.deepcopy(leaving_snap)
            target['config'] = target_cfg
            target['enabled'] = True
            try:
                self._variant_enabled_vars[new_slot].set(True)
            except tk.TclError:
                pass

        # 3. Swap current_config. Preserve the variants block itself.
        new_config = copy.deepcopy(target_cfg)
        new_config['variants'] = v
        v['active'] = new_slot
        self.current_config = new_config
        self.config_manager.config = new_config

        # 4. Push into tabs + conversion tabs.
        self.update_config_display()
        self.status_var.set(f"Active variant: {new_slot}")

    # ─── Processing all enabled variants ─────────────────────────

    def start_processing_all_variants(self):
        """Run the full pipeline for every enabled variant, writing
        each one's outputs into its own subfolder next to the input
        file (<input_dir>/<basename>_variants/<slot>/). The currently
        active variant is restored at the end."""
        if not self.validate_inputs():
            return
        self._variants_ensure_slots()
        enabled = [s for s in self._VARIANT_SLOTS
                   if self.current_config['variants']['slots'][s].get(
                       'enabled', False)]
        if not enabled:
            messagebox.showinfo(
                "Variants",
                "No variants are enabled. Check at least one slot "
                "under 'Enabled' first.")
            return
        # Make sure the current UI state is saved into the ACTIVE slot
        # first so it's included if that slot is enabled.
        self._variant_save_current()

        self.process_button.config(state='disabled')
        self.process_motion_button.config(state='disabled')
        self.progress_var.set(0)

        t = threading.Thread(
            target=self._process_all_variants_worker,
            args=(enabled,), daemon=True)
        t.start()

    def _process_all_variants_worker(self, enabled_slots):
        """Thread body: iterate variants, run processor, collect
        successes and failures."""
        import copy
        saved_active = str(self.current_config['variants'].get('active'))
        total_variants = len(enabled_slots)
        total_files = len(self.input_files)
        all_successes = 0
        all_failures = 0
        try:
            for v_idx, slot in enumerate(enabled_slots, 1):
                slot_cfg = copy.deepcopy(
                    self.current_config['variants']['slots'][slot]
                    .get('config') or {})
                if not slot_cfg:
                    continue
                # Force per-variant subfolder as the central output path.
                fm = slot_cfg.setdefault('file_management', {})
                fm['mode'] = 'central'
                for file_idx, input_file in enumerate(self.input_files, 1):
                    base = Path(input_file).stem
                    parent = Path(input_file).parent
                    out_dir = parent / f"{base}_variants" / slot
                    out_dir.mkdir(parents=True, exist_ok=True)
                    fm['central_folder_path'] = str(out_dir)
                    processor = RestimProcessor(slot_cfg)

                    def prog(percent, message, s=slot, fi=file_idx,
                             vi=v_idx):
                        self.update_progress(
                            percent,
                            f"Variant {s} [{vi}/{total_variants}] — "
                            f"file {fi}/{total_files}: {message}")

                    ok = processor.process(input_file, prog)
                    if ok:
                        all_successes += 1
                        self.last_processed_filename = base
                        self.last_processed_directory = out_dir
                    else:
                        all_failures += 1
            self.update_progress(
                100,
                f"Processed {total_variants} variant(s): "
                f"{all_successes} ok, {all_failures} failed.")
            if all_failures == 0:
                self.root.after(
                    100, lambda: messagebox.showinfo(
                        "Variants",
                        f"Processed all {total_variants} enabled "
                        f"variants.\nOutputs under:\n"
                        f"{Path(self.input_files[0]).parent}/"
                        f"{Path(self.input_files[0]).stem}_variants/"))
            else:
                self.root.after(
                    100, lambda: messagebox.showwarning(
                        "Variants",
                        f"{all_failures} variant runs failed. "
                        f"See console for details."))
        except Exception as e:
            self.root.after(
                100, lambda msg=str(e): messagebox.showerror(
                    "Variants", f"Unexpected error:\n{msg}"))
        finally:
            # Restore the active slot's state (we may have nudged
            # file_management inside slot_cfg copies above; the
            # authoritative slot config in current_config is unchanged
            # because we deep-copied).
            self.current_config['variants']['active'] = saved_active
            self.root.after(0, lambda: (
                self.process_button.config(state='normal'),
                self.process_motion_button.config(state='normal')))

    def validate_inputs(self) -> bool:
        """Validate user inputs before processing."""
        # Check if files are selected
        if not self.input_files:
            messagebox.showerror("Error", "Please select at least one input file.")
            return False

        # Validate all selected files
        for input_file in self.input_files:
            if not Path(input_file).exists():
                messagebox.showerror("Error", f"Input file does not exist:\n{input_file}")
                return False

            if not input_file.lower().endswith('.funscript'):
                messagebox.showerror("Error", f"File must be a .funscript file:\n{input_file}")
                return False

        # Update and validate configuration
        self.update_config_from_ui()
        try:
            self.config_manager.validate_config()
        except ValueError as e:
            messagebox.showerror("Configuration Error", str(e))
            return False

        return True

    def start_processing(self):
        """Start the processing in a separate thread."""
        if not self.validate_inputs():
            return

        # Disable both process buttons during processing
        self.process_button.config(state='disabled')
        self.process_motion_button.config(state='disabled')
        self.progress_var.set(0)

        # Start processing thread
        processing_thread = threading.Thread(target=self.process_files, daemon=True)
        processing_thread.start()

    def start_motion_processing(self):
        """Start motion file processing in a separate thread."""
        if not self.validate_inputs():
            return

        # Disable both process buttons during processing
        self.process_button.config(state='disabled')
        self.process_motion_button.config(state='disabled')
        self.progress_var.set(0)

        # Start motion processing thread
        processing_thread = threading.Thread(target=self.process_motion_files, daemon=True)
        processing_thread.start()

    def process_files(self):
        """Process files in background thread."""
        try:
            total_files = len(self.input_files)
            successful = 0
            failed = 0
            
            for index, input_file in enumerate(self.input_files, 1):
                # Update status for current file
                file_name = Path(input_file).name
                self.update_progress(0, f"Processing file {index}/{total_files}: {file_name}")
                
                # Create processor with current configuration
                processor = RestimProcessor(self.current_config)

                # Process with progress callback that includes file index
                def file_progress_callback(percent, message):
                    status_msg = f"[{index}/{total_files}] {file_name}: {message}"
                    self.update_progress(percent, status_msg)

                success = processor.process(input_file, file_progress_callback)

                if success:
                    successful += 1
                    # Track the last successfully processed file
                    input_path = Path(input_file)
                    self.last_processed_filename = input_path.stem
                    self.last_processed_directory = input_path.parent
                else:
                    failed += 1

            # Show final summary
            if total_files == 1:
                if successful:
                    self.update_progress(100, "Processing completed successfully!")
                    self.root.after(100, lambda: messagebox.showinfo("Success", "Processing completed successfully!"))
            else:
                # Batch processing summary
                summary = f"Batch processing complete!\n\nSuccessful: {successful}\nFailed: {failed}\nTotal: {total_files}"
                self.update_progress(100, f"Batch complete: {successful}/{total_files} successful")
                self.root.after(100, lambda: messagebox.showinfo("Batch Complete", summary))

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.update_progress(-1, error_msg)
            self.root.after(100, lambda: messagebox.showerror("Error", error_msg))

        finally:
            # Re-enable both process buttons
            self.root.after(100, lambda: self.process_button.config(state='normal'))
            self.root.after(100, lambda: self.process_motion_button.config(state='normal'))

    def process_motion_files(self):
        """Process motion files in background thread based on current mode."""
        try:
            total_files = len(self.input_files)
            successful = 0
            failed = 0
            
            axes_config = self.current_config['positional_axes']
            generate_legacy = axes_config.get('generate_legacy', False)
            generate_motion_axis = axes_config.get('generate_motion_axis', False)
            modes = ([" 3P"] if generate_legacy else []) + (["4P"] if generate_motion_axis else [])
            mode_str = "+".join(modes) if modes else "none"

            for index, input_file in enumerate(self.input_files, 1):
                file_name = Path(input_file).name
                self.update_progress(0, f"[{index}/{total_files}] Processing {file_name} ({mode_str})...")

                try:
                    input_path = Path(input_file)

                    if generate_legacy:
                        # Use existing 2D conversion logic
                        self.update_progress(20, f"[{index}/{total_files}] Converting to 2D (3P)...")
                        original_value = self.input_file_var.get()
                        self.input_file_var.set(input_file)
                        self._perform_2d_conversion('basic')
                        self.input_file_var.set(original_value)

                    if generate_motion_axis:
                        # Generate motion axis files
                        self.update_progress(20, f"[{index}/{total_files}] Generating motion axis files (4P)...")
                        self._generate_motion_axis_files(input_path)

                    if not generate_legacy and not generate_motion_axis:
                        raise ValueError("No motion scripts enabled — enable 'Generate motion scripts' in the Motion Axis (3P) or (4P) tab")

                    successful += 1
                    # Track the last successfully processed file
                    self.last_processed_filename = input_path.stem
                    self.last_processed_directory = input_path.parent

                except Exception as file_error:
                    failed += 1
                    error_msg = f"Failed to process {file_name}: {str(file_error)}"
                    self.update_progress(-1, error_msg)

            # Show final summary
            if total_files == 1:
                if successful:
                    self.update_progress(100, "Motion processing completed successfully!")
                    self.root.after(100, lambda: messagebox.showinfo("Success", "Motion processing completed successfully!"))
            else:
                # Batch processing summary
                summary = f"Batch motion processing complete!\n\nSuccessful: {successful}\nFailed: {failed}\nTotal: {total_files}"
                self.update_progress(100, f"Batch complete: {successful}/{total_files} successful")
                self.root.after(100, lambda: messagebox.showinfo("Batch Complete", summary))

        except Exception as e:
            error_msg = f"Motion processing failed: {str(e)}"
            self.update_progress(-1, error_msg)
            self.root.after(100, lambda: messagebox.showerror("Error", error_msg))

        finally:
            # Re-enable both process buttons
            self.root.after(100, lambda: self.process_button.config(state='normal'))
            self.root.after(100, lambda: self.process_motion_button.config(state='normal'))

    def update_progress(self, percent: int, message: str):
        """Update progress bar and status message. Thread-safe."""
        def update_ui():
            if percent >= 0:
                self.progress_var.set(percent)
            else:
                # Error indicated by negative percent
                self.progress_var.set(0)
                messagebox.showerror("Processing Error", message)

            self.status_var.set(message)

        # Schedule UI update in main thread
        self.root.after(0, update_ui)

    def run(self):
        """Start the main application loop."""
        self.root.mainloop()


def main():
    """Entry point for the application."""
    import traceback
    from datetime import datetime

    def log_exception(exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions to a file."""
        with open("restimfunscriptprocessor.log", "a") as f:
            f.write(f"--- {datetime.now()} ---\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("\n")
        
        # Also show a user-friendly error message
        # Make sure this runs in the main thread if called from a background thread
        def show_error():
            messagebox.showerror("Unhandled Exception",
                                 "An unexpected error occurred. Please check restimfunscriptprocessor.log for details.")
        
        # This check is crude. A better way would involve a cross-thread communication queue.
        # But for this application, it's a reasonable starting point.
        if isinstance(threading.current_thread(), threading._MainThread):
            show_error()
        else:
            # If we are not in the main thread, we can't directly show a messagebox.
            # The logging is the most important part.
            print("ERROR: Unhandled exception in background thread. See log file.")


    app = MainWindow()
    
    # Set the global exception handlers
    app.root.report_callback_exception = log_exception
    threading.excepthook = log_exception

    app.run()


if __name__ == "__main__":
    main()