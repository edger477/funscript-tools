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


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Restim Funscript Processor")
        self.root.geometry("800x950")
        self.root.resizable(True, True)

        # Configuration
        self.config_manager = ConfigManager()
        self.current_config = self.config_manager.get_config()

        # Variables
        self.input_file_var = tk.StringVar()
        self.normalize_volume_var = tk.BooleanVar(value=self.current_config['options']['normalize_volume'])
        self.delete_intermediary_var = tk.BooleanVar(value=self.current_config['options']['delete_intermediary_files'])

        # 1D to 2D conversion variables
        algorithm_value = self.current_config['alpha_beta_generation'].get('algorithm', 'circular')
        self.conversion_algorithm_var = tk.StringVar(value=algorithm_value)
        points_per_second = self.current_config['alpha_beta_generation'].get('points_per_second', 25)
        self.conversion_points_var = tk.IntVar(value=points_per_second)
        min_distance = self.current_config['alpha_beta_generation'].get('min_distance_from_center', 0.1)
        self.conversion_min_distance_var = tk.DoubleVar(value=min_distance)
        speed_at_edge = self.current_config['alpha_beta_generation'].get('speed_at_edge_hz', 2.0)
        self.conversion_speed_edge_var = tk.DoubleVar(value=speed_at_edge)

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

        # 1D to 2D Conversion frame
        conversion_frame = ttk.LabelFrame(main_frame, text="1D to 2D Conversion", padding="10")
        conversion_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        conversion_frame.columnconfigure(1, weight=1)

        # Algorithm selection
        ttk.Label(conversion_frame, text="Algorithm:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # Create frame for radio buttons arranged vertically for better space usage
        algo_frame = ttk.Frame(conversion_frame)
        algo_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Radiobutton(algo_frame, text="Circular (0°-180°)",
                       variable=self.conversion_algorithm_var, value="circular").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(algo_frame, text="Top-Left-Right (0°-270°)",
                       variable=self.conversion_algorithm_var, value="top-left-right").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(algo_frame, text="Top-Right-Left (0°-90°)",
                       variable=self.conversion_algorithm_var, value="top-right-left").pack(anchor=tk.W, pady=1)

        # Points per second
        ttk.Label(conversion_frame, text="Points Per Second:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        points_entry = ttk.Entry(conversion_frame, textvariable=self.conversion_points_var, width=10)
        points_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(conversion_frame, text="(1-100) Interpolation density").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # Min Distance From Center
        ttk.Label(conversion_frame, text="Min Distance From Center:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        min_distance_scale = ttk.Scale(conversion_frame, from_=0.1, to=0.9, variable=self.conversion_min_distance_var,
                                      orient=tk.HORIZONTAL, length=150)
        min_distance_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(conversion_frame, text="(0.1-0.9) Minimum radius from center").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # Speed at Edge (Hz)
        ttk.Label(conversion_frame, text="Speed at Edge (Hz):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        speed_edge_scale = ttk.Scale(conversion_frame, from_=1.0, to=5.0, variable=self.conversion_speed_edge_var,
                                    orient=tk.HORIZONTAL, length=150)
        speed_edge_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(conversion_frame, text="(1-5 Hz) Speed for maximum radius").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # Convert to 2D button
        self.convert_2d_button = ttk.Button(conversion_frame, text="Convert to 2D", command=self.convert_to_2d)
        self.convert_2d_button.grid(row=4, column=0, columnspan=3, pady=10)

        row += 1

        # Processing options frame
        options_frame = ttk.LabelFrame(main_frame, text="Processing Options", padding="10")
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        options_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(options_frame, text="Normalize Volume", variable=self.normalize_volume_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Delete Intermediary Files When Done", variable=self.delete_intermediary_var).grid(row=1, column=0, sticky=tk.W)

        row += 1

        # Parameters frame
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        params_frame.columnconfigure(0, weight=1)
        params_frame.rowconfigure(0, weight=1)

        # Parameter tabs
        self.parameter_tabs = ParameterTabs(params_frame, self.current_config)
        self.parameter_tabs.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

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

        self.process_button = ttk.Button(buttons_frame, text="Process Files", command=self.start_processing)
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(buttons_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_config).pack(side=tk.LEFT)

        # Configure main_frame row weights
        main_frame.rowconfigure(row-1, weight=1)  # Parameters frame gets extra space

    def browse_input_file(self):
        """Open file dialog to select input funscript file."""
        file_path = filedialog.askopenfilename(
            title="Select Funscript File",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file_var.set(file_path)

    def convert_to_2d(self):
        """Convert 1D funscript to 2D alpha/beta files only."""
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

        # Disable the convert button during processing
        self.convert_2d_button.config(state='disabled')

        # Start conversion in background thread
        conversion_thread = threading.Thread(target=self._perform_2d_conversion, daemon=True)
        conversion_thread.start()

    def _perform_2d_conversion(self):
        """Perform 2D conversion in background thread."""
        try:
            input_file = self.input_file_var.get().strip()
            input_path = Path(input_file)

            self.update_progress(10, "Loading input file...")

            # Import necessary modules
            from funscript import Funscript
            from processing.funscript_1d_to_2d import generate_alpha_beta_from_main

            # Load main funscript
            main_funscript = Funscript.from_file(input_path)

            self.update_progress(30, "Converting to 2D...")

            # Get conversion parameters
            algorithm = self.conversion_algorithm_var.get()
            points_per_second = self.conversion_points_var.get()
            min_distance = self.conversion_min_distance_var.get()
            speed_at_edge_hz = self.conversion_speed_edge_var.get()

            # Generate alpha and beta
            alpha_funscript, beta_funscript = generate_alpha_beta_from_main(
                main_funscript, points_per_second, algorithm, min_distance, speed_at_edge_hz
            )

            self.update_progress(70, "Saving alpha and beta files...")

            # Save files
            alpha_path = input_path.parent / f"{input_path.stem}.alpha.funscript"
            beta_path = input_path.parent / f"{input_path.stem}.beta.funscript"

            alpha_funscript.save_to_path(alpha_path)
            beta_funscript.save_to_path(beta_path)

            self.update_progress(100, f"2D conversion complete! Created {alpha_path.name} and {beta_path.name}")

            # Show success message
            self.root.after(100, lambda: messagebox.showinfo("Success",
                f"2D conversion completed successfully!\n\nCreated files:\n• {alpha_path.name}\n• {beta_path.name}"))

        except Exception as e:
            error_msg = f"2D conversion failed: {str(e)}"
            self.update_progress(-1, error_msg)
            self.root.after(100, lambda: messagebox.showerror("Error", error_msg))

        finally:
            # Re-enable the convert button
            self.root.after(100, lambda: self.convert_2d_button.config(state='normal'))

    def update_config_from_ui(self):
        """Update configuration with current UI values."""
        # Update options
        self.current_config['options']['normalize_volume'] = self.normalize_volume_var.get()
        self.current_config['options']['delete_intermediary_files'] = self.delete_intermediary_var.get()

        # Update 1D to 2D conversion settings
        self.current_config['alpha_beta_generation']['algorithm'] = self.conversion_algorithm_var.get()
        self.current_config['alpha_beta_generation']['points_per_second'] = self.conversion_points_var.get()
        self.current_config['alpha_beta_generation']['min_distance_from_center'] = round(self.conversion_min_distance_var.get(), 1)
        self.current_config['alpha_beta_generation']['speed_at_edge_hz'] = round(self.conversion_speed_edge_var.get(), 1)

        # Update parameters from tabs
        self.parameter_tabs.update_config(self.current_config)

    def update_config_display(self):
        """Update UI display with current configuration values."""
        self.normalize_volume_var.set(self.current_config['options']['normalize_volume'])
        self.delete_intermediary_var.set(self.current_config['options']['delete_intermediary_files'])

        # Update 1D to 2D conversion display
        algorithm_value = self.current_config['alpha_beta_generation'].get('algorithm', 'circular')
        self.conversion_algorithm_var.set(algorithm_value)
        points_value = self.current_config['alpha_beta_generation'].get('points_per_second', 25)
        self.conversion_points_var.set(points_value)
        min_distance_value = self.current_config['alpha_beta_generation'].get('min_distance_from_center', 0.1)
        self.conversion_min_distance_var.set(min_distance_value)
        speed_edge_value = self.current_config['alpha_beta_generation'].get('speed_at_edge_hz', 2.0)
        self.conversion_speed_edge_var.set(speed_edge_value)

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

        # Disable the process button during processing
        self.process_button.config(state='disabled')
        self.progress_var.set(0)

        # Start processing thread
        processing_thread = threading.Thread(target=self.process_files, daemon=True)
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
            # Re-enable the process button
            self.root.after(100, lambda: self.process_button.config(state='normal'))

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