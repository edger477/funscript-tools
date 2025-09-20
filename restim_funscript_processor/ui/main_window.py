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
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Configuration
        self.config_manager = ConfigManager()
        self.current_config = self.config_manager.get_config()

        # Variables
        self.input_file_var = tk.StringVar()
        self.normalize_volume_var = tk.BooleanVar(value=self.current_config['options']['normalize_volume'])
        self.delete_intermediary_var = tk.BooleanVar(value=self.current_config['options']['delete_intermediary_files'])

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

    def update_config_from_ui(self):
        """Update configuration with current UI values."""
        # Update options
        self.current_config['options']['normalize_volume'] = self.normalize_volume_var.get()
        self.current_config['options']['delete_intermediary_files'] = self.delete_intermediary_var.get()

        # Update parameters from tabs
        self.parameter_tabs.update_config(self.current_config)

    def update_config_display(self):
        """Update UI display with current configuration values."""
        self.normalize_volume_var.set(self.current_config['options']['normalize_volume'])
        self.delete_intermediary_var.set(self.current_config['options']['delete_intermediary_files'])
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