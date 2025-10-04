import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))
from config import ConfigManager
from processor import RestimProcessor
from ui.parameter_tabs import ParameterTabs
from ui.conversion_tabs import ConversionTabs


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Restim Funscript Processor")
        self.root.geometry("850x1000")
        self.root.resizable(True, True)

        # Configuration
        self.config_manager = ConfigManager()
        self.current_config = self.config_manager.get_config()

        # Variables
        self.input_file_var = tk.StringVar()

        # Progress tracking
        self.progress_var = tk.IntVar()
        self.status_var = tk.StringVar(value="Ready to process...")

        self.setup_ui()
        self.update_config_display()

    def setup_ui(self):
        """Setup the main user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Input file selection
        ttk.Label(main_frame, text="Input File:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_input_file).grid(row=row, column=2, padx=(0, 5), pady=5)

        row += 1

        # Parameters frame (1D to 2D conversion is now in Motion Axis tab)
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        params_frame.columnconfigure(0, weight=1)
        params_frame.rowconfigure(0, weight=1)

        # Parameter tabs
        self.parameter_tabs = ParameterTabs(params_frame, self.current_config)
        self.parameter_tabs.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Set callback for mode changes (for future extensibility)
        self.parameter_tabs.set_mode_change_callback(self.on_mode_change)

        row += 1

        # Progress and status frame
        status_frame = ttk.LabelFrame(main_frame, text="Output Status", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        status_frame.columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Status label
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W, pady=5)

        # Buttons frame
        buttons_frame = ttk.Frame(status_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.process_button = ttk.Button(buttons_frame, text="Process All Files", command=self.start_processing)
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))

        self.process_motion_button = ttk.Button(buttons_frame, text="Process Motion Files", command=self.start_motion_processing)
        self.process_motion_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(buttons_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_config).pack(side=tk.LEFT)

        # Configure main_frame row weights
        main_frame.rowconfigure(row-1, weight=1)  # Parameters frame gets extra space  # Parameters frame gets extra space  # Parameters frame gets extra space



    def on_mode_change(self, mode):
        """Called when positional axis mode changes."""
        # Mode changes are now handled within the Motion Axis tab
        pass




    def browse_input_file(self):
        """Open file dialog to select input funscript file."""
        file_path = filedialog.askopenfilename(
            title="Select Funscript File",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file_var.set(file_path)

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
        self.conversion_tabs.set_button_state('disabled')

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

            # Determine which conversion_tabs to use (main window or embedded in parameter tabs)
            mode = self.current_config['positional_axes']['mode']
            if mode == 'legacy' and hasattr(self.parameter_tabs, 'embedded_conversion_tabs'):
                conversion_tabs = self.parameter_tabs.embedded_conversion_tabs
            else:
                conversion_tabs = self.conversion_tabs

            if conversion_type == 'basic':
                from processing.funscript_1d_to_2d import generate_alpha_beta_from_main

                # Get basic conversion parameters
                config = conversion_tabs.get_basic_config()

                # Generate alpha and beta files
                alpha_funscript, beta_funscript = generate_alpha_beta_from_main(
                    main_funscript, config['points_per_second'], config['algorithm'],
                    config['min_distance_from_center'], config['speed_at_edge_hz']
                )

                # Save files
                filename_only = input_path.stem
                alpha_path = input_path.parent / f"{filename_only}.alpha.funscript"
                beta_path = input_path.parent / f"{filename_only}.beta.funscript"

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
                alpha_prostate_path = input_path.parent / f"{filename_only}.alpha-prostate.funscript"
                beta_prostate_path = input_path.parent / f"{filename_only}.beta-prostate.funscript"

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
            mode = self.current_config['positional_axes']['mode']
            if mode == 'legacy' and hasattr(self.parameter_tabs, 'embedded_conversion_tabs'):
                self.root.after(100, lambda: self.parameter_tabs.embedded_conversion_tabs.set_button_state('normal'))
            else:
                self.root.after(100, lambda: self.conversion_tabs.set_button_state('normal'))

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

            # Generate motion axis files
            generated_files = generate_motion_axes(
                main_funscript,
                motion_config,
                input_path.parent,
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

    def reset_config(self):
        """Reset configuration to defaults."""
        if messagebox.askyesno("Reset Configuration", "Reset all parameters to default values?"):
            self.config_manager.reset_to_defaults()
            self.current_config = self.config_manager.get_config()
            self.update_config_display()

    def validate_inputs(self) -> bool:
        """Validate user inputs before processing."""
        input_file = self.input_file_var.get().strip()

        if not input_file:
            messagebox.showerror("Error", "Please select an input file.")
            return False

        if not Path(input_file).exists():
            messagebox.showerror("Error", "Input file does not exist.")
            return False

        if not input_file.lower().endswith('.funscript'):
            messagebox.showerror("Error", "Input file must be a .funscript file.")
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
            input_file = self.input_file_var.get().strip()

            # Create processor with current configuration
            processor = RestimProcessor(self.current_config)

            # Process with progress callback
            success = processor.process(input_file, self.update_progress)

            if success:
                self.update_progress(100, "Processing completed successfully!")
                # Show completion message in main thread
                self.root.after(100, lambda: messagebox.showinfo("Success", "Processing completed successfully!"))
            else:
                # Error message already shown in update_progress
                pass

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
            input_file = self.input_file_var.get().strip()
            input_path = Path(input_file)

            # Get current positional axis mode
            mode = self.current_config['positional_axes']['mode']

            self.update_progress(10, f"Processing in {mode} mode...")

            if mode == 'legacy':
                # Use existing 2D conversion logic (default to basic)
                self.update_progress(20, "Converting to 2D (Legacy mode)...")
                self._perform_2d_conversion('basic')

            elif mode == 'motion_axis':
                # Generate motion axis files
                self.update_progress(20, "Generating motion axis files...")
                self._generate_motion_axis_files(input_path)

            else:
                raise ValueError(f"Unknown positional axis mode: {mode}")

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
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()