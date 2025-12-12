import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import zipfile
from pathlib import Path

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from processing.event_processor import process_events, _parse_and_validate_user_events, _load_event_definitions, EventProcessorError


# Path to the event definitions YAML file
EVENT_DEFINITIONS_PATH = Path(__file__).parent.parent / "config.event_definitions.yml"


class CustomEventsDialog(tk.Toplevel):
    """
    A dialog window for applying custom events from a YAML file to funscripts.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Custom Event Processor")
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # Variables
        self.event_file_var = tk.StringVar()
        self.backup_var = tk.BooleanVar(value=True)
        self.headroom_var = tk.IntVar(value=10)  # Default 10 units of headroom
        self.apply_to_linked_var = tk.BooleanVar(value=True)  # Default enabled for backward compatibility
        self.validated_user_events = []
        self.event_definitions = {} # To store loaded event definitions
        self.backup_path = None  # Store the backup path after processing

        # Load event definitions on init
        try:
            self.event_definitions, _ = _load_event_definitions(EVENT_DEFINITIONS_PATH)
        except EventProcessorError as e:
            messagebox.showerror("Error Loading Definitions", str(e), parent=self)
            self.destroy() # Close if definitions cannot be loaded
            return

        self.setup_ui()

    def browse_event_file(self):
        """Browse for an event file, then parse and validate it."""
        file_path = filedialog.askopenfilename(
            title="Select Event File",
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")]
        )
        if not file_path:
            return

        self.event_file_var.set(file_path)
        self.status_label.config(text=f"Validating {Path(file_path).name}...")
        self.apply_button.config(state="disabled")
        self.update_preview("")
        self.validated_user_events = []

        try:
            self.validated_user_events = _parse_and_validate_user_events(Path(file_path), self.event_definitions)
            preview_content = []
            for event in self.validated_user_events:
                preview_content.append(f"--- Event: {event['name']} at {event['time']}ms ---")
                for step in event['processed_steps']:
                    op = step['operation']
                    axis = step['axis']
                    offset = step.get('start_offset', 0)
                    params_str = ", ".join([f"{k}={v}" for k, v in step['params'].items()])
                    preview_content.append(f"  + {op} on {axis} (offset: {offset}ms) with [{params_str}]")
            
            self.update_preview("\n".join(preview_content))
            self.status_label.config(text=f"Ready to apply {len(self.validated_user_events)} user events.")
            self.apply_button.config(state="normal")

        except EventProcessorError as e:
            self.status_label.config(text=f"Error: {e}")
            messagebox.showerror("Validation Error", str(e), parent=self)
        except Exception as e:
            self.status_label.config(text=f"An unexpected error occurred: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self)

    def start_processing_thread(self):
        """Start the event processing in a background thread to keep the UI responsive."""
        self.apply_button.config(state="disabled")
        self.close_button.config(state="disabled")
        self.status_label.config(text="Processing... Please wait.")
        
        processing_thread = threading.Thread(
            target=self.apply_effects_worker,
            daemon=True
        )
        processing_thread.start()

    def apply_effects_worker(self):
        """The worker function that calls the backend processing logic."""
        try:
            event_file = self.event_file_var.get()
            do_backup = self.backup_var.get()
            headroom = self.headroom_var.get()
            apply_to_linked = self.apply_to_linked_var.get()

            success_message, _, backup_path = process_events(event_file, do_backup, EVENT_DEFINITIONS_PATH, headroom, apply_to_linked)

            self.after(0, self.on_processing_success, success_message, backup_path)

        except EventProcessorError as e:
            self.after(0, self.on_processing_error, str(e))
        except Exception as e:
            self.after(0, self.on_processing_error, f"An unexpected error occurred during processing: {e}")
        finally:
            self.after(10, self.on_processing_complete)

    def on_processing_success(self, message: str, backup_path):
        """Callback on successful processing."""
        self.backup_path = backup_path
        messagebox.showinfo("Success", message, parent=self)

        # If backup was created, enable the restore button and don't close the dialog
        if backup_path:
            self.restore_button.config(state="normal", text=f"Restore Backup ({backup_path.name})")
            self.apply_button.config(state="disabled")
            self.status_label.config(text="Processing complete. You can restore the backup if needed.")
        else:
            self.destroy()

    def on_processing_error(self, error_message: str):
        """Callback on failed processing."""
        messagebox.showerror("Processing Error", error_message, parent=self)
        self.status_label.config(text="Failed. Please check the files and try again.")
    
    def on_processing_complete(self):
        """Re-enables UI elements after processing finishes or fails."""
        if self.winfo_exists(): # Check if window was not already destroyed
            self.apply_button.config(state="normal")
            self.close_button.config(state="normal")

    def restore_backup(self):
        """Restore files from the backup archive."""
        if not self.backup_path or not self.backup_path.exists():
            messagebox.showerror("Error", "Backup file not found.", parent=self)
            return

        # Confirm restoration
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"This will restore all files from the backup:\n{self.backup_path.name}\n\n"
            "Current files will be overwritten. Continue?",
            parent=self
        )

        if not confirm:
            return

        try:
            # Extract all files from the backup to the same directory
            target_dir = self.backup_path.parent

            with zipfile.ZipFile(self.backup_path, 'r') as zipf:
                file_list = zipf.namelist()
                zipf.extractall(target_dir)

            messagebox.showinfo(
                "Restore Complete",
                f"Successfully restored {len(file_list)} files from backup.",
                parent=self
            )

            # Disable restore button after successful restore
            self.restore_button.config(state="disabled")
            self.status_label.config(text="Backup restored successfully.")

        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore backup: {e}", parent=self)

    def update_preview(self, content: str):
        """Updates the text in the preview box."""
        self.event_preview_text.config(state='normal')
        self.event_preview_text.delete(1.0, tk.END)
        self.event_preview_text.insert(tk.END, content)
        self.event_preview_text.config(state='disabled')

    def setup_ui(self):
        """Setup the user interface for the dialog."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        row = 0

        # --- File Selection Frame ---
        file_frame = ttk.LabelFrame(main_frame, text="Event File", padding="10")
        file_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)

        ttk.Entry(file_frame, textvariable=self.event_file_var, width=50, state='readonly').grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(file_frame, text="Select Event File...", command=self.browse_event_file).grid(row=0, column=1)

        row += 1

        # --- Event Preview Frame ---
        preview_frame = ttk.LabelFrame(main_frame, text="Event Preview", padding="10")
        preview_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1) # Allow this frame to expand

        self.event_preview_text = tk.Text(preview_frame, height=10, width=60, state='disabled', wrap='word')
        self.event_preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.event_preview_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.event_preview_text['yscrollcommand'] = scrollbar.set

        row += 1

        # --- Options Frame ---
        options_frame = ttk.Frame(main_frame, padding="5 0")
        options_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(0, weight=1)

        # Backup option
        self.backup_checkbox = ttk.Checkbutton(options_frame, text="Backup existing funscripts before applying changes", variable=self.backup_var)
        self.backup_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Apply to linked axes option
        self.linked_checkbox = ttk.Checkbutton(options_frame, text="Apply main axis events to linked axes (e.g., volume → volume-prostate)", variable=self.apply_to_linked_var)
        self.linked_checkbox.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Headroom option
        headroom_frame = ttk.Frame(options_frame)
        headroom_frame.grid(row=2, column=0, sticky=tk.W)

        ttk.Label(headroom_frame, text="Create amount of headroom above highest point (volume axis):").pack(side=tk.LEFT, padx=(0, 5))

        headroom_spinbox = ttk.Spinbox(headroom_frame, from_=0, to=20, textvariable=self.headroom_var, width=5)
        headroom_spinbox.pack(side=tk.LEFT)

        row += 1

        # --- Action & Status Frame ---
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=row, column=0, sticky=(tk.W, tk.E))
        action_frame.columnconfigure(1, weight=1)

        # Buttons sub-frame
        buttons_subframe = ttk.Frame(action_frame)
        buttons_subframe.grid(row=0, column=0, sticky=tk.W)

        self.apply_button = ttk.Button(buttons_subframe, text="Apply Effects", state="disabled", command=self.start_processing_thread)
        self.apply_button.pack(side=tk.LEFT, padx=(0, 10))

        self.restore_button = ttk.Button(buttons_subframe, text="Restore Backup", state="disabled", command=self.restore_backup)
        self.restore_button.pack(side=tk.LEFT, padx=(0, 10))

        self.close_button = ttk.Button(buttons_subframe, text="Close", command=self.destroy)
        self.close_button.pack(side=tk.LEFT)

        # Status Label sub-frame
        status_subframe = ttk.Frame(action_frame, padding="5 0")
        status_subframe.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        status_subframe.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_subframe, text="Please select an event file.")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

if __name__ == '__main__':
    # A simple way to test the dialog for development
    root = tk.Tk()
    root.title("Main App")
    root.geometry("300x100")
    
    def open_dialog():
        dialog = CustomEventsDialog(root)
        root.wait_window(dialog)

    ttk.Button(root, text="Open Custom Events Dialog", command=open_dialog).pack(padx=20, pady=20)
    root.mainloop()