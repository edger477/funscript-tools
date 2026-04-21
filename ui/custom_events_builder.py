"""
Custom Events Builder Dialog - Visual Event Timeline Editor

This module provides a user-friendly visual interface for creating and editing
custom event timelines without requiring manual YAML editing.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import logging
import threading
import traceback
import zipfile
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from processing.event_processor import process_events, EventProcessorError
import ui.theme as _theme


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and PyInstaller.

    When running as a bundled exe, checks the exe directory first for external config files,
    then falls back to the bundled resource in the temporary extraction directory.

    Args:
        relative_path: Path relative to the application root (e.g., "config.event_definitions.yml")

    Returns:
        Path: Absolute path to the resource file
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - check exe directory first
        exe_dir = Path(sys.executable).parent
        external_file = exe_dir / relative_path
        if external_file.exists():
            return external_file

        # Fall back to bundled resource in temp directory
        base_path = Path(sys._MEIPASS)
        return base_path / relative_path
    else:
        # Running from source - use standard path resolution
        return Path(__file__).parent.parent / relative_path


# Path to the event definitions YAML file
EVENT_DEFINITIONS_PATH = get_resource_path("config.event_definitions.yml")


class EventLibraryPanel(ttk.Frame):
    """Panel for browsing and selecting event definitions"""

    def __init__(self, parent, event_definitions: Dict[str, Any], groups: List[Dict[str, str]], on_select_callback):
        super().__init__(parent)
        self.event_definitions = event_definitions
        self.groups = groups
        self.on_select_callback = on_select_callback

        self.setup_ui()
        self.populate_events()

    def setup_ui(self):
        """Create the UI components"""
        # Title
        title_label = ttk.Label(self, text="Event Library", font=('TkDefaultFont', 10, 'bold'))
        title_label.pack(pady=(0, 5))

        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Event list with categories
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview for hierarchical display
        self.event_tree = ttk.Treeview(list_frame, yscrollcommand=scrollbar.set,
                                       selectmode='browse', show='tree')
        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.event_tree.yview)

        # Bind selection event
        self.event_tree.bind('<<TreeviewSelect>>', self.on_event_selected)
        self.event_tree.bind('<Double-Button-1>', self.on_event_double_click)

        # Add to timeline button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_to_timeline_btn = ttk.Button(btn_frame, text="Add to Timeline",
                                              command=self.on_add_to_timeline, state='disabled')
        self.add_to_timeline_btn.pack(fill=tk.X)

    def categorize_events(self) -> List[Dict[str, Any]]:
        """Group events by category based on groups configuration"""
        categorized = []

        for group in self.groups:
            group_name = group['name']
            prefix = group['prefix']
            description = group['description']
            events = []

            for event_name in sorted(self.event_definitions.keys()):
                # Match events by prefix
                if prefix == "":
                    # General category - events without known prefixes
                    if not any(event_name.startswith(g['prefix']) for g in self.groups if g['prefix'] != ""):
                        events.append(event_name)
                else:
                    # Specific category - events with matching prefix
                    if event_name.startswith(prefix):
                        events.append(event_name)

            if events:  # Only include groups with events
                categorized.append({
                    'name': group_name,
                    'description': description,
                    'events': events
                })

        return categorized

    def populate_events(self):
        """Populate the event tree with categorized events"""
        categories = self.categorize_events()
        self.category_tooltips = {}  # Store category descriptions for tooltips

        for category_info in categories:
            # Add category as parent
            category_id = self.event_tree.insert('', 'end', text=category_info['name'], open=True)
            self.category_tooltips[category_id] = category_info['description']

            # Add events as children
            for event_name in category_info['events']:
                # Create display name (remove prefix, replace _ with space, title case)
                display_name = event_name.replace('mcb_', '').replace('clutch_', '').replace('_', ' ').title()
                self.event_tree.insert(category_id, 'end', text=display_name,
                                       values=(event_name,), tags=('event',))

        # Add tooltip support
        self.create_tooltip_support()

    def create_tooltip_support(self):
        """Add tooltip support for category items"""
        self.tooltip_label = None

        def on_motion(event):
            # Get item under mouse
            item = self.event_tree.identify_row(event.y)
            if item and item in self.category_tooltips:
                # Show tooltip for category
                if self.tooltip_label is None:
                    self.tooltip_label = tk.Toplevel(self)
                    self.tooltip_label.wm_overrideredirect(True)
                    label = tk.Label(self.tooltip_label, text=self.category_tooltips[item],
                                   background="lightyellow", relief=tk.SOLID, borderwidth=1,
                                   font=('TkDefaultFont', 9), wraplength=300, justify=tk.LEFT,
                                   padx=5, pady=3)
                    label.pack()

                # Position tooltip near mouse
                x = event.x_root + 15
                y = event.y_root + 10
                self.tooltip_label.wm_geometry(f"+{x}+{y}")
            else:
                # Hide tooltip
                self.hide_tooltip()

        def on_leave(event):
            self.hide_tooltip()

        self.event_tree.bind('<Motion>', on_motion)
        self.event_tree.bind('<Leave>', on_leave)

    def hide_tooltip(self):
        """Hide the tooltip if it exists"""
        if self.tooltip_label:
            self.tooltip_label.destroy()
            self.tooltip_label = None

    def on_search_changed(self, *args):
        """Filter events based on search text"""
        search_text = self.search_var.get().lower()

        # Clear current display
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)

        if not search_text:
            # No search, show all categories
            self.populate_events()
            return

        # Search and display matching events
        matches = []
        for event_name in self.event_definitions.keys():
            if search_text in event_name.lower():
                matches.append(event_name)

        if matches:
            search_category = self.event_tree.insert('', 'end', text='Search Results', open=True)
            for event_name in sorted(matches):
                display_name = event_name.replace('mcb_', '').replace('clutch_', '').replace('_', ' ').title()
                self.event_tree.insert(search_category, 'end', text=display_name,
                                       values=(event_name,), tags=('event',))

    def on_event_selected(self, event):
        """Handle event selection in tree"""
        selection = self.event_tree.selection()
        if selection:
            item = selection[0]
            # Check if it's an event (not a category)
            if self.event_tree.item(item, 'tags'):
                event_name = self.event_tree.item(item, 'values')[0]
                self.add_to_timeline_btn.config(state='normal')
                if self.on_select_callback:
                    self.on_select_callback(event_name)
            else:
                self.add_to_timeline_btn.config(state='disabled')

    def on_event_double_click(self, event):
        """Handle double-click on event"""
        self.on_add_to_timeline()

    def on_add_to_timeline(self):
        """Add selected event to timeline"""
        selection = self.event_tree.selection()
        if selection and self.event_tree.item(selection[0], 'tags'):
            # This will be handled by the parent dialog
            pass

    def get_selected_event(self) -> Optional[str]:
        """Get currently selected event name"""
        selection = self.event_tree.selection()
        if selection and self.event_tree.item(selection[0], 'tags'):
            return self.event_tree.item(selection[0], 'values')[0]
        return None


class ParameterPanel(ttk.Frame):
    """Panel for editing event parameters with dynamic form generation"""

    def __init__(self, parent, apply_callback=None, reset_callback=None):
        super().__init__(parent)
        self.current_event_name = None
        self.current_event_definition = None
        self.current_params = {}
        self.param_widgets = {}
        self.param_vars = {}  # Store variable objects
        self.current_time_ms = 0
        self.time_var = tk.IntVar(value=0)

        # Callbacks to parent dialog
        self.apply_callback = apply_callback
        self.reset_callback = reset_callback
        self.save_default_callback = None

        self.setup_ui()
        _theme.register(self._on_theme_change)
        self._apply_text_theme(_theme.is_dark())
        self.bind('<Destroy>', lambda e: _theme.unregister(self._on_theme_change) if e.widget is self else None)

    def _apply_text_theme(self, dark: bool):
        bg = '#1e1e2e' if dark else '#f5f5f5'
        fg = '#cdd6f4' if dark else '#000000'
        self.steps_text.config(bg=bg, fg=fg, insertbackground=fg)
        self.canvas.config(bg='#1e1e2e' if dark else 'white')

    def _on_theme_change(self, dark: bool):
        self._apply_text_theme(dark)

    def setup_ui(self):
        """Create the UI components"""
        # Title
        self.title_label = ttk.Label(self, text="Parameters", font=('TkDefaultFont', 10, 'bold'))
        self.title_label.pack(pady=(0, 5))

        # Editing event number label
        self.editing_label = ttk.Label(self, text="", foreground='blue', font=('TkDefaultFont', 9))
        self.editing_label.pack(pady=(0, 5))

        # Scrollable frame for parameters
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)

        self.params_frame = ttk.Frame(self.canvas)
        self.params_frame.bind('<Configure>',
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        self.canvas.create_window((0, 0), window=self.params_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons frame — packed before preview so it's always visible
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5, side=tk.BOTTOM)

        ttk.Button(btn_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Apply Parameters", command=self.apply_parameters).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Save as Default", command=self._on_save_default).pack(side=tk.LEFT, padx=2)

        # Event steps preview section
        preview_frame = ttk.LabelFrame(self, text="Event Steps Preview", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=False, pady=(5, 0), side=tk.BOTTOM)

        self.steps_text = tk.Text(preview_frame, height=8, wrap=tk.WORD,
                                  font=('Courier', 9),
                                  relief=tk.FLAT, state=tk.DISABLED)
        steps_scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.steps_text.yview)
        self.steps_text.configure(yscrollcommand=steps_scrollbar.set)

        self.steps_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        steps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.show_placeholder()

    def show_placeholder(self):
        """Show placeholder when no event is selected"""
        for widget in self.params_frame.winfo_children():
            widget.destroy()

        label = ttk.Label(self.params_frame, text="Select an event to edit parameters",
                         foreground='gray')
        label.pack(pady=20)

        # Clear steps preview
        self.steps_text.config(state=tk.NORMAL)
        self.steps_text.delete('1.0', tk.END)
        self.steps_text.insert('1.0', "Select an event to see what it does...")
        self.steps_text.config(state=tk.DISABLED)

    @staticmethod
    def format_event_display_name(event_name: str) -> str:
        """Format event name with category prefix for display"""
        if event_name.startswith('mcb_'):
            # MCB - Edge
            name = event_name.replace('mcb_', '').replace('_', ' ').title()
            return f"MCB - {name}"
        elif event_name.startswith('clutch_'):
            # Clutch - Good Slave
            name = event_name.replace('clutch_', '').replace('_', ' ').title()
            return f"Clutch - {name}"
        else:
            # General - Edge
            name = event_name.replace('_', ' ').title()
            return f"General - {name}"

    def load_event_parameters(self, event_name: str, event_definition: Dict[str, Any],
                             current_params: Optional[Dict[str, Any]] = None, event_time_ms: int = 0,
                             event_number: Optional[int] = None):
        """Load and display parameters for an event"""
        self.current_event_name = event_name
        self.current_event_definition = event_definition
        default_params = event_definition.get('default_params', {})
        self.current_params = current_params if current_params else default_params.copy()
        self.current_time_ms = event_time_ms
        self.time_var.set(event_time_ms)

        # Clear existing widgets
        if not self.params_frame.winfo_exists():
            return
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_widgets = {}
        self.param_vars = {}

        # Update title with category prefix
        display_name = self.format_event_display_name(event_name)
        self.title_label.config(text=f"Parameters: {display_name}")

        # Update editing label
        if event_number is not None:
            self.editing_label.config(text=f"Editing event #{event_number}")
        else:
            self.editing_label.config(text="")

        # Add time control at the top
        self.create_time_control()

        # Create parameter controls
        for param_name, default_value in default_params.items():
            self.create_parameter_control(param_name, default_value, self.current_params.get(param_name, default_value))

        # Update steps preview
        self.update_steps_preview()

    def create_time_control(self):
        """Create the time input control with quick adjustment buttons"""
        frame = ttk.Frame(self.params_frame)
        frame.pack(fill=tk.X, padx=5, pady=(0, 10))

        # Label
        label = ttk.Label(frame, text="Event Time:", width=15, anchor='w', font=('TkDefaultFont', 9, 'bold'))
        label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Time input
        time_spinbox = ttk.Spinbox(frame, from_=0, to=3600000, increment=1000, textvariable=self.time_var, width=10)
        time_spinbox.grid(row=0, column=1, sticky=tk.EW)
        frame.columnconfigure(1, weight=1)

        # Unit label
        unit_label = ttk.Label(frame, text="ms", width=3)
        unit_label.grid(row=0, column=2, padx=(5, 0))

        # MM:SS display
        def format_time():
            ms = self.time_var.get()
            total_seconds = ms / 1000
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"({minutes}:{seconds:02d})"

        self.time_display_label = ttk.Label(frame, text=format_time(), foreground='gray', width=8)
        self.time_display_label.grid(row=0, column=3, padx=(5, 5))

        # Update display when time changes
        def on_time_changed(*args):
            if self.time_display_label.winfo_exists():
                self.time_display_label.config(text=format_time())

        self.time_var.trace_add('write', on_time_changed)

        # Quick adjustment buttons
        btn_frame = ttk.Frame(self.params_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Label(btn_frame, text="Quick adjust:", width=15).grid(row=0, column=0, sticky=tk.W)

        # Helper function to adjust time
        def adjust_time(delta_ms):
            current = self.time_var.get()
            new_time = max(0, current + delta_ms)
            self.time_var.set(new_time)

        # Minutes buttons
        ttk.Button(btn_frame, text="-5m", width=4,
                  command=lambda: adjust_time(-5*60*1000)).grid(row=0, column=1, padx=1)
        ttk.Button(btn_frame, text="-1m", width=4,
                  command=lambda: adjust_time(-1*60*1000)).grid(row=0, column=2, padx=1)

        # Seconds buttons
        ttk.Button(btn_frame, text="-10s", width=4,
                  command=lambda: adjust_time(-10*1000)).grid(row=0, column=3, padx=1)
        ttk.Button(btn_frame, text="-5s", width=4,
                  command=lambda: adjust_time(-5*1000)).grid(row=0, column=4, padx=1)
        ttk.Button(btn_frame, text="-1s", width=4,
                  command=lambda: adjust_time(-1*1000)).grid(row=0, column=5, padx=1)

        ttk.Label(btn_frame, text="|", foreground='gray').grid(row=0, column=6, padx=3)

        ttk.Button(btn_frame, text="+1s", width=4,
                  command=lambda: adjust_time(1*1000)).grid(row=0, column=7, padx=1)
        ttk.Button(btn_frame, text="+5s", width=4,
                  command=lambda: adjust_time(5*1000)).grid(row=0, column=8, padx=1)
        ttk.Button(btn_frame, text="+10s", width=4,
                  command=lambda: adjust_time(10*1000)).grid(row=0, column=9, padx=1)
        ttk.Button(btn_frame, text="+1m", width=4,
                  command=lambda: adjust_time(1*60*1000)).grid(row=0, column=10, padx=1)
        ttk.Button(btn_frame, text="+5m", width=4,
                  command=lambda: adjust_time(5*60*1000)).grid(row=0, column=11, padx=1)

        # Separator
        ttk.Separator(self.params_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)

    def create_parameter_control(self, param_name: str, default_value, current_value):
        """Create appropriate control for a parameter"""
        frame = ttk.Frame(self.params_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)

        # Label
        display_name = param_name.replace('_', ' ').title()
        label = ttk.Label(frame, text=display_name + ':', width=15, anchor='w')
        label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Determine control type and create widget
        widget, var, unit = self.create_widget_for_parameter(frame, param_name, current_value)
        widget.grid(row=0, column=1, sticky=tk.EW)
        frame.columnconfigure(1, weight=1)

        # Unit label
        if unit:
            unit_label = ttk.Label(frame, text=unit, width=5)
            unit_label.grid(row=0, column=2, padx=(5, 0))

        self.param_widgets[param_name] = widget
        self.param_vars[param_name] = var  # Store the variable object

        # Add trace to update preview when parameter changes
        var.trace_add('write', lambda *args: self.update_steps_preview())

    def create_widget_for_parameter(self, parent, param_name: str, value):
        """Create appropriate widget based on parameter name and value, returns (widget, var, unit)"""
        # Time parameters
        if param_name.endswith('_ms'):
            var = tk.IntVar(value=int(value))
            widget = ttk.Spinbox(parent, from_=0, to=60000, increment=100, textvariable=var, width=10)
            return widget, var, 'ms'

        # Frequency parameters
        if 'freq' in param_name.lower() or param_name == 'pulse_rate':
            is_fractional = isinstance(value, float) and (value < 1.0 or value % 1.0 != 0.0)
            if is_fractional:
                var = tk.DoubleVar(value=float(value))
                widget = ttk.Spinbox(parent, from_=0.1, to=200, increment=0.05, textvariable=var,
                                   format='%.2f', width=10)
            else:
                var = tk.IntVar(value=int(value))
                widget = ttk.Spinbox(parent, from_=1, to=200, increment=1, textvariable=var, width=10)
            return widget, var, 'Hz'

        # Pulse width (percentage)
        if param_name == 'pulse_width' or param_name.endswith('_width'):
            var = tk.IntVar(value=int(value))
            widget = ttk.Spinbox(parent, from_=0, to=100, increment=1, textvariable=var, width=10)
            return widget, var, '%'

        # Phase (degrees)
        if param_name.endswith('_phase'):
            var = tk.IntVar(value=int(value))
            widget = ttk.Spinbox(parent, from_=0, to=360, increment=15, textvariable=var, width=10)
            return widget, var, '°'

        # Normalized values (0.0-1.0)
        if ('amplitude' in param_name or 'intensity' in param_name or
            'volume' in param_name):
            var = tk.DoubleVar(value=float(value))
            widget = ttk.Spinbox(parent, from_=-1.0, to=1.0, increment=0.01, textvariable=var,
                               format='%.2f', width=10)
            return widget, var, ''

        # Offset/boost parameters
        if 'offset' in param_name or 'boost' in param_name or 'reduction' in param_name or 'shift' in param_name or 'drop' in param_name:
            var = tk.DoubleVar(value=float(value))
            widget = ttk.Spinbox(parent, from_=-1.0, to=1.0, increment=0.01, textvariable=var,
                               format='%.2f', width=10)
            return widget, var, ''

        # Generic numeric
        if isinstance(value, (int, float)):
            var = tk.DoubleVar(value=float(value))
            widget = ttk.Entry(parent, textvariable=var, width=10)
            return widget, var, ''

        # String fallback
        var = tk.StringVar(value=str(value))
        widget = ttk.Entry(parent, textvariable=var, width=10)
        return widget, var, ''

    def get_parameter_values(self) -> Dict[str, Any]:
        """Extract current parameter values from widgets"""
        params = {}
        for param_name, var in self.param_vars.items():
            try:
                value = var.get()

                # Type conversion based on parameter name
                if param_name.endswith('_ms') or param_name == 'pulse_rate' or param_name == 'pulse_width':
                    params[param_name] = int(value) if isinstance(value, (int, float)) else int(float(value))
                elif 'freq' in param_name.lower():
                    fval = float(value) if not isinstance(value, (int, float)) else float(value)
                    params[param_name] = fval if fval % 1.0 != 0.0 else int(fval)
                elif param_name.endswith('_phase'):
                    params[param_name] = int(value) if isinstance(value, (int, float)) else int(float(value))
                else:
                    # Keep as is (float or string)
                    params[param_name] = value
            except Exception as e:
                print(f"Error getting value for {param_name}: {e}")
                params[param_name] = self.current_params.get(param_name, 0)

        return params

    def get_event_time(self) -> int:
        """Get the current event time in milliseconds"""
        return self.time_var.get()

    def reset_to_defaults(self):
        """Reset parameters to default values"""
        if self.current_event_name and hasattr(self, 'current_event_definition'):
            default_params = self.current_event_definition.get('default_params', {})
            self.load_event_parameters(self.current_event_name, self.current_event_definition, default_params)

    def update_steps_preview(self):
        """Update the event steps preview with current parameter values"""
        if not self.current_event_name or not hasattr(self, 'current_event_definition'):
            self.steps_text.config(state=tk.NORMAL)
            self.steps_text.delete('1.0', tk.END)
            self.steps_text.insert('1.0', "Select an event to see what it does...")
            self.steps_text.config(state=tk.DISABLED)
            return

        # Get current parameter values
        try:
            current_values = self.get_parameter_values()
        except:
            current_values = self.current_params.copy()

        # Get event steps
        steps = self.current_event_definition.get('steps', [])

        # Build preview text
        preview_lines = []
        for idx, step in enumerate(steps, start=1):
            operation = step.get('operation', 'unknown')
            axis = step.get('axis', 'unknown')
            params = step.get('params', {})

            preview_lines.append(f"Step {idx}: {operation} on {axis}")

            # Show parameters with substituted values
            for param_name, param_value in params.items():
                # Substitute parameter references like $buzz_freq
                if isinstance(param_value, str) and param_value.startswith('$'):
                    var_name = param_value[1:]  # Remove $
                    if var_name in current_values:
                        actual_value = current_values[var_name]
                        preview_lines.append(f"  • {param_name}: {actual_value} (from ${var_name})")
                    else:
                        preview_lines.append(f"  • {param_name}: {param_value}")
                else:
                    preview_lines.append(f"  • {param_name}: {param_value}")

            preview_lines.append("")  # Blank line between steps

        # Update text widget
        self.steps_text.config(state=tk.NORMAL)
        self.steps_text.delete('1.0', tk.END)
        self.steps_text.insert('1.0', '\n'.join(preview_lines))
        self.steps_text.config(state=tk.DISABLED)

    def apply_parameters(self):
        """Apply current parameters - calls parent callback"""
        if self.apply_callback:
            self.apply_callback()

    def _on_save_default(self):
        if self.save_default_callback:
            self.save_default_callback()


class CanvasTimelinePanel(ttk.Frame):
    """Canvas-based interactive timeline for event scheduling.

    Provides drag-to-reposition events, drag-to-resize event duration,
    click-to-select, zoom (Ctrl+scroll), and pan (scroll / drag background).
    """

    # Visual constants
    RULER_H = 28       # Height of the time ruler strip in pixels
    TRACK_H = 40       # Height of each event lane in pixels
    FUNSCRIPT_H = 50   # Height of the funscript waveform track in pixels
    LEFT_MARGIN = 62   # Width of the left label margin in pixels
    RESIZE_ZONE = 9    # Pixels from right edge of block that trigger resize cursor
    MIN_BLOCK_W = 16   # Minimum rendered block width in pixels

    # Canvas theme — active values (start in light mode; swapped by apply_canvas_theme)
    BG_COLOR     = '#f0f0f0'
    RULER_BG     = '#dde1ec'
    RULER_TEXT   = '#6677aa'
    RULER_ACCENT = '#1a2a5e'
    RULER_LINE   = '#b0b8cc'
    TICK_MINOR   = '#b0b8cc'
    GRID_MAJOR   = '#c8ccd8'
    GRID_MINOR   = '#e4e6ec'
    TRACK_LINE   = '#d8dae4'
    MARGIN_BG    = '#e4e8f4'
    GRID_COLOR      = '#c8ccd8'   # alias kept for compatibility
    SEL_OUTLINE     = '#1a2a5e'
    FUNSCRIPT_LINE  = '#3a7fc1'
    FUNSCRIPT_FILL  = '#b8d4f0'
    FUNSCRIPT_BG    = '#eef2fa'

    _LIGHT_THEME = dict(
        BG_COLOR='#f0f0f0', RULER_BG='#dde1ec', RULER_TEXT='#6677aa',
        RULER_ACCENT='#1a2a5e', RULER_LINE='#b0b8cc', TICK_MINOR='#b0b8cc',
        GRID_MAJOR='#c8ccd8', GRID_MINOR='#e4e6ec', TRACK_LINE='#d8dae4',
        MARGIN_BG='#e4e8f4', GRID_COLOR='#c8ccd8', SEL_OUTLINE='#1a2a5e',
        FUNSCRIPT_LINE='#3a7fc1', FUNSCRIPT_FILL='#b8d4f0', FUNSCRIPT_BG='#eef2fa',
    )
    _DARK_THEME = dict(
        BG_COLOR='#1e1e2e', RULER_BG='#16213e', RULER_TEXT='#7b8cad',
        RULER_ACCENT='#c8d4f0', RULER_LINE='#2e3a56', TICK_MINOR='#2e3a56',
        GRID_MAJOR='#272740', GRID_MINOR='#222232', TRACK_LINE='#26263a',
        MARGIN_BG='#141424', GRID_COLOR='#272740', SEL_OUTLINE='#ffffff',
        FUNSCRIPT_LINE='#5b9bd5', FUNSCRIPT_FILL='#1e3a5a', FUNSCRIPT_BG='#181828',
    )

    @classmethod
    def apply_canvas_theme(cls, dark: bool) -> None:
        """Swap all canvas colour constants for dark or light mode."""
        for k, v in (cls._DARK_THEME if dark else cls._LIGHT_THEME).items():
            setattr(cls, k, v)

    # Event block colours: (fill, darker outline)
    CATEGORY_COLORS = {
        'mcb':     ('#e8a010', '#b07000'),
        'clutch':  ('#9060c0', '#6030a0'),
        'test':    ('#28a870', '#0a7848'),
        'general': ('#3070d0', '#1040a8'),
    }

    def __init__(self, parent,
                 on_select_callback=None,
                 on_move_callback=None,
                 on_resize_callback=None,
                 change_callback=None,
                 add_callback=None,
                 duplicate_callback=None,
                 change_type_callback=None):
        super().__init__(parent)

        # ---- Data ----
        self.events: List[Dict[str, Any]] = []
        self.selected_index: Optional[int] = None
        self.auto_sort_var = tk.BooleanVar(value=True)
        self.on_change_time = None  # set externally by the dialog

        # ---- Timeline scale ----
        self.zoom: float = 50.0        # pixels per second
        self.pan_offset_ms: float = 0.0  # ms at the left edge of the visible area
        self.total_ms: int = 120_000   # total timeline duration in ms (updated by funscript)

        # ---- Interaction state ----
        self._drag = None       # dict: mode/idx/start_x/orig_time/orig_dur/moved
        self._pan_drag = None   # dict: start_x/orig_pan  (background pan drag)
        self._add_time_ms: Optional[int] = None  # pre-filled time for right-click "Add here"

        # ---- Playhead ----
        self._playhead_ms: float = 0.0
        self._playhead_drag: bool = False

        # ---- Snap ----
        self._snap_interval_ms: float = 0.0   # 0 = off
        self._snap_target_ms: Optional[float] = None  # active snap point during drag

        # ---- Frame step (updated from video fps when video is loaded) ----
        self._frame_ms: float = 1000.0 / 30   # ms per frame, default 30 fps

        # ---- Funscript waveform overlay ----
        self._funscript_actions: List[Dict] = []   # [{at: ms, pos: 0-100}, ...]
        self.show_funscript: bool = True            # toggled by dialog checkbox

        # ---- Undo / Redo ----
        self._history: List[List[Dict]] = []   # snapshots of self.events
        self._history_pos: int = -1            # current position in _history

        # ---- Layout cache (rebuilt each redraw) ----
        self._lanes: List[int] = []       # lane index per event (parallel to self.events)
        self._n_lanes: int = 1
        self._block_rects: List[tuple] = []  # (x1, y1, x2, y2) canvas coords per event
        self._conflicts: set = set()         # indices of events overlapping another

        # ---- Callbacks ----
        self.on_select_callback = on_select_callback
        self.on_move_callback   = on_move_callback
        self.on_resize_callback = on_resize_callback
        self.change_callback    = change_callback
        self.add_callback       = add_callback
        self.duplicate_callback   = duplicate_callback
        self.change_type_callback = change_type_callback
        self.on_redraw_callback = None    # set externally; called after every redraw
        self.on_playhead_change = None    # set externally; called with ms when playhead moves
        self.play_pause_callback = None   # set externally; called when spacebar pressed

        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI construction                                                       #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        """Build toolbar + canvas area."""
        # --- Toolbar ---
        tb = ttk.Frame(self)
        tb.pack(fill=tk.X, padx=2, pady=(2, 1))

        ttk.Button(tb, text="Add Event",   command=self._on_toolbar_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Remove",      command=self._on_remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Duplicate",   command=self._on_duplicate).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Change Time", command=self._on_change_time_btn).pack(side=tk.LEFT, padx=2)

        ttk.Separator(tb, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        self._undo_btn = ttk.Button(tb, text="Undo", command=self.undo, state='disabled')
        self._undo_btn.pack(side=tk.LEFT, padx=2)
        self._redo_btn = ttk.Button(tb, text="Redo", command=self.redo, state='disabled')
        self._redo_btn.pack(side=tk.LEFT, padx=2)

        ttk.Separator(tb, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        ttk.Button(tb, text="Fit View", command=self.fit_view).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(tb, text="Auto-sort by time",
                        variable=self.auto_sort_var).pack(side=tk.LEFT, padx=12)

        ttk.Separator(tb, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        ttk.Label(tb, text="Snap:").pack(side=tk.LEFT, padx=(0, 2))
        self._snap_combo = ttk.Combobox(
            tb, state='readonly', width=5,
            values=['Off', '0.5s', '1s', '5s', '10s', '30s', '1m'])
        self._snap_combo.current(0)
        self._snap_combo.pack(side=tk.LEFT)
        self._snap_combo.bind('<<ComboboxSelected>>', self._on_snap_changed)

        ttk.Separator(tb, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        self._playhead_label = ttk.Label(tb, text="\u25b6 0:00.000", foreground='#cc2222',
                                         font=('TkFixedFont', 9))
        self._playhead_label.pack(side=tk.LEFT, padx=4)

        self._zoom_label = ttk.Label(tb, text="", foreground='#666')
        self._zoom_label.pack(side=tk.RIGHT, padx=6)

        # --- Canvas area ---
        cf = ttk.Frame(self)
        cf.pack(fill=tk.BOTH, expand=True)

        self._h_scroll = ttk.Scrollbar(cf, orient='horizontal')
        self._h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(cf, bg=self.BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._h_scroll.config(command=self._on_hscroll)

        # --- Context menus ---
        self._ctx = tk.Menu(self, tearoff=0)
        self._ctx.add_command(label="Edit Parameters",   command=self._ctx_edit)
        self._ctx.add_command(label="Change Event Type", command=self._ctx_change_type)
        self._ctx.add_command(label="Change Time",       command=self._on_change_time_btn)
        self._ctx.add_command(label="Duplicate",         command=self._on_duplicate)
        self._ctx.add_separator()
        self._ctx.add_command(label="Remove",            command=self._on_remove)

        self._ctx_bg = tk.Menu(self, tearoff=0)
        self._ctx_bg.add_command(label="Add Event here", command=self._on_add_at_ctx)

        # --- Canvas event bindings ---
        c = self.canvas
        c.bind('<Configure>',         self._on_canvas_resize)
        c.bind('<ButtonPress-1>',     self._on_lpress)
        c.bind('<B1-Motion>',         self._on_ldrag)
        c.bind('<ButtonRelease-1>',   self._on_lrelease)
        c.bind('<ButtonPress-2>',     self._on_mpress)
        c.bind('<B2-Motion>',         self._on_mdrag)
        c.bind('<ButtonRelease-2>',   self._on_mrelease)
        c.bind('<MouseWheel>',        self._on_mousewheel)   # Windows / macOS
        c.bind('<Button-4>',          self._on_scroll_up)    # Linux scroll up
        c.bind('<Button-5>',          self._on_scroll_down)  # Linux scroll down
        c.bind('<Double-Button-1>',   self._on_double_click)
        c.bind('<Motion>',            self._on_motion)
        c.bind('<Leave>',             lambda e: self.canvas.config(cursor=''))
        c.bind('<ButtonPress-3>',     self._on_rclick)
        c.bind('<Delete>',            lambda e: self._on_remove())
        c.bind('<BackSpace>',         lambda e: self._on_remove())
        c.bind('<Control-z>',         lambda e: self.undo())
        c.bind('<Control-Z>',         lambda e: self.undo())
        c.bind('<Control-y>',         lambda e: self.redo())
        c.bind('<Control-Y>',         lambda e: self.redo())
        c.bind('<Control-d>',         lambda e: self._on_duplicate())
        c.bind('<Control-D>',         lambda e: self._on_duplicate())
        c.bind('<Left>',              lambda e: self._on_arrow(-1))
        c.bind('<Right>',             lambda e: self._on_arrow(1))
        c.bind('<Shift-Left>',              lambda e: self._on_arrow(-30))
        c.bind('<Shift-Right>',             lambda e: self._on_arrow(30))
        c.bind('<Shift-Control-Left>',      lambda e: self._on_seek_ms(-30_000))
        c.bind('<Shift-Control-Right>',     lambda e: self._on_seek_ms(30_000))
        c.bind('<space>',                   lambda e: self.play_pause_callback() if self.play_pause_callback else None)

    # ------------------------------------------------------------------ #
    # Public interface (API-compatible with the old TimelinePanel)         #
    # ------------------------------------------------------------------ #

    def add_event(self, time_ms: int, event_name: str, params: Dict[str, Any]):
        """Append an event, scroll it into view, and refresh the timeline."""
        self._push_history()
        self.events.append({'time': time_ms, 'name': event_name, 'params': params.copy()})
        if self.auto_sort_var.get():
            self.events.sort(key=lambda e: e['time'])
        self._scroll_into_view(time_ms)
        self.refresh_display()
        if self.change_callback:
            self.change_callback()

    def _scroll_into_view(self, time_ms: float):
        """Pan so that *time_ms* is visible, with some left-margin padding."""
        visible = self._visible_ms()
        # If it's already visible, do nothing
        if self.pan_offset_ms <= time_ms <= self.pan_offset_ms + visible:
            return
        # Centre the target time in the view
        self.pan_offset_ms = max(0.0, time_ms - visible * 0.25)

    def update_event(self, index: int, time_ms: int, event_name: str,
                     params: Dict[str, Any]) -> int:
        """Update event at *index*; returns the new index after optional re-sort."""
        if not (0 <= index < len(self.events)):
            return index
        self._push_history()
        ev_obj = {'time': time_ms, 'name': event_name, 'params': params.copy()}
        self.events[index] = ev_obj
        if self.auto_sort_var.get():
            self.events.sort(key=lambda e: e['time'])
            try:
                new_index = self.events.index(ev_obj)
            except ValueError:
                new_index = index
        else:
            new_index = index
        self.selected_index = new_index
        self.refresh_display()
        if self.change_callback:
            self.change_callback()
        return new_index

    def remove_event(self, index: int):
        """Remove event at *index*."""
        if not (0 <= index < len(self.events)):
            return
        self._push_history()
        was_selected = (self.selected_index == index)
        self.events.pop(index)
        if self.selected_index == index:
            self.selected_index = None
        elif self.selected_index is not None and self.selected_index > index:
            self.selected_index -= 1
        self.refresh_display()
        # Notify dialog so it can clear the params panel
        if was_selected and self.on_select_callback:
            self.on_select_callback(None)
        if self.change_callback:
            self.change_callback()

    def get_event(self, index: int) -> Optional[Dict[str, Any]]:
        """Return the event dict at *index*, or None."""
        return self.events[index] if 0 <= index < len(self.events) else None

    def load_events_from_yaml(self, events_list: List[Dict[str, Any]]):
        """Load events from a parsed YAML list and fit the view."""
        self.events = list(events_list)
        if self.auto_sort_var.get():
            self.events.sort(key=lambda e: e['time'])
        self.selected_index = None
        self.refresh_display()
        self.after(60, self.fit_view)  # fit after the canvas has been sized

    def get_yaml_data(self) -> Dict[str, Any]:
        """Return the YAML-compatible data structure."""
        return {'events': self.events}

    def refresh_display(self):
        """Trigger a full canvas redraw."""
        self.redraw()

    def set_duration(self, total_ms: int):
        """Update the total timeline duration (e.g. from a loaded funscript)."""
        self.total_ms = max(total_ms, 60_000)
        self.redraw()

    def set_funscript(self, actions: List[Dict]):
        """Load funscript actions for the waveform track.

        *actions* is a list of {'at': ms, 'pos': 0-100} dicts, already
        sorted by 'at'.  Pass an empty list to clear the track.
        """
        self._funscript_actions = sorted(actions, key=lambda a: a['at'])
        self.redraw()

    # ------------------------------------------------------------------ #
    # Undo / Redo                                                          #
    # ------------------------------------------------------------------ #

    def _snapshot(self) -> List[Dict]:
        import copy
        return copy.deepcopy(self.events)

    def _push_history(self):
        """Save current state before a mutation.  Clears any redo branch."""
        snapshot = self._snapshot()
        # Drop everything above the current position (clears redo)
        del self._history[self._history_pos + 1:]
        self._history.append(snapshot)
        self._history_pos = len(self._history) - 1
        self._update_undo_redo_buttons()

    def undo(self):
        """Restore the state before the last mutation."""
        if self._history_pos < 0:
            return
        # If we haven't stored the very latest state yet, do so now
        if self._history_pos == len(self._history) - 1:
            self._history.append(self._snapshot())
        self._history_pos -= 1
        import copy
        self.events = copy.deepcopy(self._history[self._history_pos])
        self.selected_index = None
        self.refresh_display()
        if self.change_callback:
            self.change_callback()
        self._update_undo_redo_buttons()

    def redo(self):
        """Re-apply a previously undone mutation."""
        if self._history_pos >= len(self._history) - 1:
            return
        self._history_pos += 1
        import copy
        self.events = copy.deepcopy(self._history[self._history_pos])
        self.selected_index = None
        self.refresh_display()
        if self.change_callback:
            self.change_callback()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self._undo_btn.config(state='normal' if self._history_pos > 0 else 'disabled')
        self._redo_btn.config(state='normal' if self._history_pos < len(self._history) - 1 else 'disabled')

    def fit_view(self):
        """Zoom and pan so all events (or the full duration) fit in the canvas."""
        canvas_w = max(self._canvas_w() - self.LEFT_MARGIN, 80)
        if self.events:
            max_end = 0
            for ev in self.events:
                dur = ev['params'].get('duration_ms', 0)
                max_end = max(max_end, ev['time'] + dur)
            content_ms = max(float(max_end) * 1.1, 1000.0)
        else:
            content_ms = max(float(self.total_ms), 60_000.0)
        self.zoom = max(0.1, min(2000.0, canvas_w * 1000.0 / content_ms))
        self.pan_offset_ms = 0.0
        self.redraw()

    @staticmethod
    def format_event_display_name(event_name: str) -> str:
        """Format event name with category prefix for display (matches ParameterPanel)."""
        if event_name.startswith('mcb_'):
            name = event_name.replace('mcb_', '').replace('_', ' ').title()
            return f"MCB - {name}"
        elif event_name.startswith('clutch_'):
            name = event_name.replace('clutch_', '').replace('_', ' ').title()
            return f"Clutch - {name}"
        else:
            name = event_name.replace('_', ' ').title()
            return f"General - {name}"

    @staticmethod
    def format_time(ms: int) -> str:
        """Format milliseconds as M:SS (matches old TimelinePanel API)."""
        total_s = ms / 1000
        m = int(total_s // 60)
        s = int(total_s % 60)
        return f"{m:2d}:{s:02d}"

    # ------------------------------------------------------------------ #
    # Coordinate helpers                                                   #
    # ------------------------------------------------------------------ #

    def _canvas_w(self) -> float:
        w = self.canvas.winfo_width()
        return float(w) if w > 1 else 800.0

    def _canvas_h(self) -> float:
        h = self.canvas.winfo_height()
        return float(h) if h > 1 else 200.0

    def _ms_to_x(self, ms: float) -> float:
        """Convert a time in ms to a canvas X coordinate."""
        return self.LEFT_MARGIN + (ms - self.pan_offset_ms) * self.zoom / 1000.0

    def _x_to_ms(self, x: float) -> float:
        """Convert a canvas X coordinate to ms."""
        return self.pan_offset_ms + (x - self.LEFT_MARGIN) * 1000.0 / self.zoom

    def _visible_ms(self) -> float:
        """Return the duration (ms) currently visible in the canvas."""
        return (self._canvas_w() - self.LEFT_MARGIN) * 1000.0 / self.zoom

    def _effective_total_ms(self) -> float:
        """Total timeline length accounting for event extents beyond self.total_ms."""
        event_max = 0.0
        for ev in self.events:
            dur = ev['params'].get('duration_ms', 0)
            event_max = max(event_max, float(ev['time'] + dur))
        return max(float(self.total_ms), event_max * 1.05, self._visible_ms(), 1.0)

    # ------------------------------------------------------------------ #
    # Lane assignment                                                       #
    # ------------------------------------------------------------------ #

    def _assign_lanes(self):
        """Greedy left-to-right lane packing to avoid visual block overlap."""
        if not self.events:
            self._lanes = []
            self._n_lanes = 1
            return

        order = sorted(range(len(self.events)), key=lambda i: self.events[i]['time'])
        lane_ends: List[float] = []   # end time (ms) of last event in each lane
        lane_map: Dict[int, int] = {}

        for i in order:
            ev = self.events[i]
            start = float(ev['time'])
            dur   = float(ev['params'].get('duration_ms', 0))
            # Use at least the minimum pixel footprint so short events don't collapse
            end   = start + max(dur, self.MIN_BLOCK_W * 1000.0 / max(self.zoom, 1.0))

            assigned = -1
            for lane_idx, le in enumerate(lane_ends):
                if le <= start:
                    assigned = lane_idx
                    break
            if assigned < 0:
                assigned = len(lane_ends)
                lane_ends.append(0.0)
            lane_ends[assigned] = end
            lane_map[i] = assigned

        self._lanes  = [lane_map.get(i, 0) for i in range(len(self.events))]
        self._n_lanes = max(1, len(lane_ends))

    def _find_conflicts(self) -> set:
        """Return the set of event indices that overlap in time with any other event."""
        conflicts: set = set()
        for i in range(len(self.events)):
            a = self.events[i]
            a_s = a['time']
            a_e = a_s + a['params'].get('duration_ms', 0)
            for j in range(i + 1, len(self.events)):
                b = self.events[j]
                b_s = b['time']
                b_e = b_s + b['params'].get('duration_ms', 0)
                if a_s < b_e and b_s < a_e:
                    conflicts.add(i)
                    conflicts.add(j)
        return conflicts

    # ------------------------------------------------------------------ #
    # Drawing                                                              #
    # ------------------------------------------------------------------ #

    def redraw(self):
        """Clear the canvas and redraw everything."""
        if not self.winfo_exists():
            return
        if self.canvas.cget('bg') != self.BG_COLOR:
            self.canvas.config(bg=self.BG_COLOR)
        self.canvas.delete('all')
        self._assign_lanes()
        self._block_rects = [self._compute_block_rect(i) for i in range(len(self.events))]
        self._conflicts   = self._find_conflicts()

        cw = self._canvas_w()
        ch = self._canvas_h()

        # Ruler background
        self.canvas.create_rectangle(0, 0, cw, self.RULER_H,
                                     fill=self.RULER_BG, outline='')
        # Left margin background
        self.canvas.create_rectangle(0, 0, self.LEFT_MARGIN, ch,
                                     fill=self.MARGIN_BG, outline='')

        self._draw_grid(cw, ch)
        self._draw_ruler(cw)
        self._draw_snap_indicator(cw, ch)
        self._draw_blocks(cw)
        self._draw_funscript_track(cw)
        self._draw_playhead(cw, ch)
        self._update_scrollbar()
        self._update_zoom_label()
        if self.on_redraw_callback:
            self.on_redraw_callback()

    def _tick_interval_s(self) -> float:
        """Return major tick spacing in seconds, adapted to current zoom."""
        ppm = self.zoom * 60  # pixels per minute
        if ppm < 40:    return 600.0
        if ppm < 100:   return 300.0
        if ppm < 200:   return 120.0
        if ppm < 500:   return 60.0
        if ppm < 1500:  return 30.0
        if ppm < 3000:  return 10.0
        if ppm < 6000:  return 5.0
        if ppm < 12000: return 2.0
        return 1.0

    def _minor_tick_interval_s(self) -> float:
        """Return minor tick spacing in seconds (subdivision of the major interval)."""
        major = self._tick_interval_s()
        subdivisions = {
            600.0: 60.0,
            300.0: 60.0,
            120.0: 30.0,
            60.0:  15.0,
            30.0:   5.0,
            10.0:   2.0,
            5.0:    1.0,
            2.0:    0.5,
            1.0:    0.25,
        }
        return subdivisions.get(major, major / 5.0)

    def _draw_ruler(self, cw: float):
        """Draw the time ruler with major and minor tick marks."""
        major = self._tick_interval_s()
        minor = self._minor_tick_interval_s()
        vis_start = self.pan_offset_ms / 1000.0
        vis_end   = (self.pan_offset_ms + self._visible_ms()) / 1000.0

        # --- Minor ticks (drawn first, under major) ---
        t = int(vis_start / minor) * minor
        while t <= vis_end + minor:
            x = self._ms_to_x(t * 1000.0)
            if self.LEFT_MARGIN <= x <= cw:
                is_maj = abs(round(t / major) * major - t) < 1e-6
                if not is_maj:
                    self.canvas.create_line(x, self.RULER_H - 5, x, self.RULER_H - 1,
                                            fill=self.TICK_MINOR)
            t = round(t + minor, 9)

        # --- Major ticks and labels ---
        t = int(vis_start / major) * major
        while t <= vis_end + major:
            x = self._ms_to_x(t * 1000.0)
            if x >= self.LEFT_MARGIN - 1 and x <= cw + 1:
                # Full-height tick mark
                self.canvas.create_line(x, 0, x, self.RULER_H - 1,
                                        fill=self.RULER_LINE, width=1)
                # Time label — right-aligned just before the tick
                m  = int(t // 60)
                s  = int(t % 60)
                ms = int(round(t * 1000) % 1000)
                label = f"{m}:{s:02d}" if ms == 0 else f"{m}:{s:02d}.{ms:03d}"
                self.canvas.create_text(x + 4, self.RULER_H // 2, text=label,
                                        fill=self.RULER_ACCENT,
                                        font=('TkFixedFont', 8), anchor='w')
            t = round(t + major, 9)

        # Ruler bottom border
        self.canvas.create_line(0, self.RULER_H, cw, self.RULER_H,
                                fill=self.RULER_LINE, width=1)
        # Left margin divider
        self.canvas.create_line(self.LEFT_MARGIN, 0, self.LEFT_MARGIN, self.RULER_H,
                                fill=self.RULER_LINE)

    def _draw_grid(self, cw: float, ch: float):
        """Draw vertical grid lines (major + minor) and horizontal track separator."""
        major = self._tick_interval_s()
        minor = self._minor_tick_interval_s()
        vis_start = self.pan_offset_ms / 1000.0
        vis_end   = (self.pan_offset_ms + self._visible_ms()) / 1000.0

        # Minor vertical grid lines
        t = int(vis_start / minor) * minor
        while t <= vis_end + minor:
            x = self._ms_to_x(t * 1000.0)
            if self.LEFT_MARGIN <= x <= cw:
                is_maj = abs(round(t / major) * major - t) < 1e-6
                if not is_maj:
                    self.canvas.create_line(x, self.RULER_H, x, ch,
                                            fill=self.GRID_MINOR)
            t = round(t + minor, 9)

        # Major vertical grid lines
        t = int(vis_start / major) * major
        while t <= vis_end + major:
            x = self._ms_to_x(t * 1000.0)
            if self.LEFT_MARGIN <= x <= cw:
                self.canvas.create_line(x, self.RULER_H, x, ch,
                                        fill=self.GRID_MAJOR)
            t = round(t + major, 9)

        # Horizontal track separator (bottom of event lane)
        y_sep = self.RULER_H + self.TRACK_H + 3
        if y_sep < ch:
            self.canvas.create_line(self.LEFT_MARGIN, y_sep, cw, y_sep,
                                    fill=self.TRACK_LINE)
        # Left margin divider (track area)
        self.canvas.create_line(self.LEFT_MARGIN, self.RULER_H,
                                self.LEFT_MARGIN, ch, fill=self.RULER_LINE)

    def _draw_blocks(self, cw: float):
        """Draw all event blocks."""
        for idx in range(len(self.events)):
            ev = self.events[idx]
            x1, y1, x2, y2 = self._block_rects[idx]

            # Skip completely off-screen
            if x2 < self.LEFT_MARGIN or x1 > cw:
                continue

            # Clip to visible horizontal range
            x1v = max(x1, float(self.LEFT_MARGIN))
            x2v = min(x2, cw)
            if x2v <= x1v:
                continue

            is_sel     = (idx == self.selected_index)
            is_conflict = idx in self._conflicts
            fill, dark = self._event_color(ev['name'])

            if is_sel:
                outline_col, outline_w = self.SEL_OUTLINE, 2
            elif is_conflict:
                outline_col, outline_w = '#ff6600', 2
            else:
                outline_col, outline_w = dark, 1

            # Main block
            self.canvas.create_rectangle(x1v, y1, x2v, y2,
                                         fill=fill, outline=outline_col, width=outline_w)

            # Conflict badge — small ⚠ in top-right corner
            if is_conflict and (x2v - x1v) >= 12:
                bx = min(x2v - 3, cw - 3)
                self.canvas.create_text(bx, y1 + 2, text='⚠',
                                        fill='#ff6600', font=('TkDefaultFont', 7),
                                        anchor='ne')

            # Resize grip: three short vertical lines near the right edge
            if x2 <= cw and (x2v - x1v) > self.RESIZE_ZONE + 4:
                gx = x2v - 5
                for offset in (0, -3, -6):
                    gxi = gx + offset
                    if gxi > x1v + 2:
                        self.canvas.create_line(gxi, y1 + 5, gxi, y2 - 5,
                                                fill='#888899', width=1)

            # Label
            block_w = x2v - x1v
            if block_w >= 18:
                label = self._block_label(ev['name'])
                dur_ms = ev['params'].get('duration_ms', 0)
                if dur_ms and block_w >= 65:
                    label += f"  {dur_ms // 1000}s"
                lx = x1v + 6
                self.canvas.create_text(
                    lx, (y1 + y2) / 2,
                    text=label,
                    fill='#ffffff',   # white text stays readable on saturated block colours
                    font=('TkDefaultFont', 8),
                    anchor='w',
                    width=max(1, int(block_w - 14))
                )

    def _compute_block_rect(self, idx: int) -> tuple:
        """Return the (x1, y1, x2, y2) canvas rectangle for event *idx*.

        All events share a single lane row.  Conflicts are indicated visually
        rather than by stacking events into additional rows.
        """
        ev = self.events[idx]

        x1 = self._ms_to_x(ev['time'])
        dur = ev['params'].get('duration_ms', 0)
        x2  = self._ms_to_x(ev['time'] + dur) if dur > 0 else x1 + self.MIN_BLOCK_W
        x2  = max(x2, x1 + self.MIN_BLOCK_W)

        y1 = self.RULER_H + 3
        y2 = y1 + self.TRACK_H - 6
        return x1, y1, x2, y2

    def _event_color(self, event_name: str):
        """Return (fill, dark_outline) colour pair for the given event name."""
        if event_name.startswith('mcb_'):
            return self.CATEGORY_COLORS['mcb']
        if event_name.startswith('clutch_'):
            return self.CATEGORY_COLORS['clutch']
        if event_name.startswith('test_'):
            return self.CATEGORY_COLORS['test']
        return self.CATEGORY_COLORS['general']

    def _block_label(self, event_name: str) -> str:
        """Short human-readable label for use inside an event block."""
        return (event_name
                .replace('mcb_', '').replace('clutch_', '').replace('test_', '')
                .replace('_', ' ').title())

    # ------------------------------------------------------------------ #
    # Scrollbar                                                            #
    # ------------------------------------------------------------------ #

    def _update_scrollbar(self):
        vis   = self._visible_ms()
        total = self._effective_total_ms()
        start = max(0.0, min(1.0, self.pan_offset_ms / total))
        end   = max(0.0, min(1.0, (self.pan_offset_ms + vis) / total))
        self._h_scroll.set(start, end)

    def _on_hscroll(self, *args):
        vis   = self._visible_ms()
        total = self._effective_total_ms()
        action = args[0]
        if action == 'moveto':
            self.pan_offset_ms = max(0.0, float(args[1]) * total)
        elif action == 'scroll':
            amount = int(args[1])
            unit   = args[2]
            delta  = vis * 0.8 if unit == 'pages' else vis * 0.1
            self.pan_offset_ms = max(0.0, self.pan_offset_ms + amount * delta)
        self.redraw()

    def _update_zoom_label(self):
        self._zoom_label.config(text=f"Zoom: {self.zoom:.0f} px/s")

    # ------------------------------------------------------------------ #
    # Playhead                                                             #
    # ------------------------------------------------------------------ #

    def _draw_playhead(self, cw: float, ch: float):
        """Draw the red playhead line and marker triangle."""
        px = self._ms_to_x(self._playhead_ms)
        if px < self.LEFT_MARGIN or px > cw:
            return

        # Vertical line through the track area
        self.canvas.create_line(px, self.RULER_H, px, ch,
                                fill='#cc2222', width=1, dash=(4, 3),
                                tags='playhead')

        # Small downward triangle in the ruler
        half = 6
        self.canvas.create_polygon(
            px - half, 2, px + half, 2, px, self.RULER_H - 2,
            fill='#cc2222', outline='', tags='playhead')

    def _update_playhead_label(self):
        """Refresh the toolbar playhead time display."""
        ms = self._playhead_ms
        total_s = ms / 1000.0
        m   = int(total_s // 60)
        s   = int(total_s % 60)
        frac = int(ms % 1000)
        self._playhead_label.config(text=f"\u25b6 {m}:{s:02d}.{frac:03d}")
        if self.on_playhead_change:
            self.on_playhead_change(self._playhead_ms)

    # ------------------------------------------------------------------ #
    # Snap                                                                 #
    # ------------------------------------------------------------------ #

    SNAP_THRESHOLD_PX = 12

    def _apply_snap(self, raw_ms: float, dur_ms: float = 0.0) -> float:
        """Return the snapped start time, testing both the start and end edges.

        *dur_ms* is the event duration; when > 0 the end edge (raw_ms + dur_ms)
        is also tested against every snap candidate.  The edge that lands closer
        to a candidate wins.  _snap_target_ms is set to the canvas position of
        the snapped edge so the indicator line appears in the right place.
        """
        threshold_ms = self.SNAP_THRESHOLD_PX * 1000.0 / max(self.zoom, 0.001)
        candidates: List[float] = []

        if self._snap_interval_ms > 0:
            # Nearest grid point for the start edge
            candidates.append(round(raw_ms / self._snap_interval_ms) * self._snap_interval_ms)
            if dur_ms > 0:
                # Nearest grid point for the end edge
                end_ms = raw_ms + dur_ms
                candidates.append(round(end_ms / self._snap_interval_ms) * self._snap_interval_ms)

        # Playhead is always a candidate for both edges
        candidates.append(self._playhead_ms)
        if dur_ms > 0:
            candidates.append(self._playhead_ms)  # same value; distance for end handled below

        # Other event start/end boundaries
        drag_idx = self._drag['idx'] if self._drag else None
        for i, ev in enumerate(self.events):
            if i == drag_idx:
                continue
            t = float(ev['time'])
            d = float(ev['params'].get('duration_ms', 0))
            candidates.append(t)
            if d > 0:
                candidates.append(t + d)

        # --- Test start edge ---
        best_start = min(candidates, key=lambda c: abs(raw_ms - c))
        dist_start = abs(raw_ms - best_start)

        # --- Test end edge (if we have a duration) ---
        best_end_target = None
        dist_end = float('inf')
        if dur_ms > 0:
            end_ms = raw_ms + dur_ms
            best_end_cand = min(candidates, key=lambda c: abs(end_ms - c))
            dist_end = abs(end_ms - best_end_cand)
            if dist_end <= threshold_ms:
                best_end_target = best_end_cand  # where the end edge would land

        # --- Pick whichever edge is closer to a snap point ---
        if dist_start <= threshold_ms and dist_start <= dist_end:
            self._snap_target_ms = best_start          # indicator at start edge
            return max(0.0, best_start)
        elif best_end_target is not None:
            self._snap_target_ms = best_end_target     # indicator at end edge
            return max(0.0, best_end_target - dur_ms)  # shift start so end lands there

        self._snap_target_ms = None
        return max(0.0, raw_ms)

    def _snap_end(self, raw_end_ms: float) -> float:
        """Snap an end-time value and set _snap_target_ms for the indicator.

        Used during resize drags where only the end edge moves.
        Returns the snapped end time in ms.
        """
        threshold_ms = self.SNAP_THRESHOLD_PX * 1000.0 / max(self.zoom, 0.001)
        candidates: List[float] = []

        if self._snap_interval_ms > 0:
            candidates.append(round(raw_end_ms / self._snap_interval_ms) * self._snap_interval_ms)

        candidates.append(self._playhead_ms)

        drag_idx = self._drag['idx'] if self._drag else None
        for i, ev in enumerate(self.events):
            if i == drag_idx:
                continue
            t = float(ev['time'])
            d = float(ev['params'].get('duration_ms', 0))
            candidates.append(t)
            if d > 0:
                candidates.append(t + d)

        best = min(candidates, key=lambda c: abs(raw_end_ms - c))
        if abs(raw_end_ms - best) <= threshold_ms:
            self._snap_target_ms = best
            return best

        self._snap_target_ms = None
        return raw_end_ms

    def _snap_start(self, raw_start_ms: float) -> float:
        """Snap a start-time value for left-edge resize drags.

        Returns the snapped start time in ms and sets _snap_target_ms.
        """
        threshold_ms = self.SNAP_THRESHOLD_PX * 1000.0 / max(self.zoom, 0.001)
        candidates: List[float] = []

        if self._snap_interval_ms > 0:
            candidates.append(round(raw_start_ms / self._snap_interval_ms) * self._snap_interval_ms)

        candidates.append(self._playhead_ms)

        drag_idx = self._drag['idx'] if self._drag else None
        for i, ev in enumerate(self.events):
            if i == drag_idx:
                continue
            t = float(ev['time'])
            d = float(ev['params'].get('duration_ms', 0))
            candidates.append(t)
            if d > 0:
                candidates.append(t + d)

        best = min(candidates, key=lambda c: abs(raw_start_ms - c))
        if abs(raw_start_ms - best) <= threshold_ms:
            self._snap_target_ms = best
            return best

        self._snap_target_ms = None
        return raw_start_ms

    def _draw_snap_indicator(self, cw: float, ch: float):
        """Draw a cyan snap-target line when an event is snapping during drag."""
        if self._snap_target_ms is None:
            return
        sx = self._ms_to_x(self._snap_target_ms)
        if sx < self.LEFT_MARGIN or sx > cw:
            return
        self.canvas.create_line(sx, self.RULER_H, sx, ch,
                                fill='#0077cc', width=1, dash=(3, 2))
        # Small label in ruler
        m   = int(self._snap_target_ms // 60000)
        s   = int((self._snap_target_ms % 60000) // 1000)
        frac = int(self._snap_target_ms % 1000)
        label = f"{m}:{s:02d}.{frac:03d}"
        self.canvas.create_text(sx + 3, self.RULER_H // 2, text=label,
                                fill='#0077cc', font=('TkDefaultFont', 7), anchor='w')

    def _draw_funscript_track(self, cw: float):
        """Draw the input funscript waveform below the event lane."""
        if not self._funscript_actions or not self.show_funscript:
            return

        # Track occupies the strip below the event lane separator
        y_top    = self.RULER_H + self.TRACK_H + 6
        y_bottom = y_top + self.FUNSCRIPT_H
        inner_h  = self.FUNSCRIPT_H - 4   # 2px padding top and bottom

        # Background
        self.canvas.create_rectangle(self.LEFT_MARGIN, y_top, cw, y_bottom,
                                     fill=self.FUNSCRIPT_BG, outline='')

        # Left margin label
        self.canvas.create_text(self.LEFT_MARGIN // 2, (y_top + y_bottom) // 2,
                                text='Input', font=('TkDefaultFont', 7),
                                fill=self.RULER_TEXT, anchor='center')

        # Separator line at bottom of track
        self.canvas.create_line(self.LEFT_MARGIN, y_bottom, cw, y_bottom,
                                fill=self.TRACK_LINE)

        # Determine visible time window
        vis_start_ms = self.pan_offset_ms
        vis_end_ms   = vis_start_ms + (cw - self.LEFT_MARGIN) * 1000.0 / max(self.zoom, 0.001)

        # Collect visible points (include one point on each side for clipping)
        actions = self._funscript_actions
        pts = []
        for i, a in enumerate(actions):
            at = float(a['at'])
            if at < vis_start_ms - 2000 or at > vis_end_ms + 2000:
                continue
            x = self._ms_to_x(at)
            # pos 0 = bottom, pos 100 = top
            y = y_bottom - 2 - (float(a['pos']) / 100.0) * inner_h
            pts.append((x, y))

        if len(pts) < 2:
            return

        # Filled polygon (waveform + baseline)
        poly = []
        poly.append((pts[0][0], y_bottom - 2))   # start at baseline
        poly.extend(pts)
        poly.append((pts[-1][0], y_bottom - 2))  # back to baseline
        flat = [v for p in poly for v in p]
        if len(flat) >= 6:
            self.canvas.create_polygon(flat, fill=self.FUNSCRIPT_FILL,
                                       outline='', smooth=False)

        # Waveform line on top
        flat_line = [v for p in pts for v in p]
        self.canvas.create_line(flat_line, fill=self.FUNSCRIPT_LINE,
                                width=1, smooth=False)

    def _on_snap_changed(self, event=None):
        """Update _snap_interval_ms from the combobox selection."""
        mapping = {'Off': 0, '0.5s': 500, '1s': 1000, '5s': 5000,
                   '10s': 10000, '30s': 30000, '1m': 60000}
        self._snap_interval_ms = float(mapping.get(self._snap_combo.get(), 0))

    # ------------------------------------------------------------------ #
    # Hit testing                                                          #
    # ------------------------------------------------------------------ #

    def _hit_test(self, x: float, y: float):
        """Return (idx, 'move'|'resize') or (None, None).

        When multiple events overlap at the click position, cycles to the
        next event in the stack each time the same area is clicked, so that
        all events remain reachable even when drawn on top of each other.
        """
        hits = []
        for idx in range(len(self.events)):
            x1, y1, x2, y2 = self._block_rects[idx]
            x1v = max(x1, float(self.LEFT_MARGIN))
            if y1 <= y <= y2 and x1v <= x <= x2:
                hits.append(idx)

        if not hits:
            return None, None

        # Cycle: if the currently selected event is in the hit list, advance
        # to the next one so repeated clicks walk through the stack.
        chosen = hits[-1]  # default: topmost (last drawn)
        if self.selected_index in hits:
            pos = hits.index(self.selected_index)
            chosen = hits[(pos + 1) % len(hits)]

        x1, y1, x2, y2 = self._block_rects[chosen]
        if x >= x2 - self.RESIZE_ZONE:
            mode = 'resize'
        elif x <= x1 + self.RESIZE_ZONE:
            mode = 'resize_left'
        else:
            mode = 'move'
        return chosen, mode

    # ------------------------------------------------------------------ #
    # Mouse event handlers                                                 #
    # ------------------------------------------------------------------ #

    def _on_lpress(self, event):
        self.canvas.focus_set()

        # Ruler click → move playhead
        if event.y < self.RULER_H:
            self._playhead_drag = True
            self._playhead_ms = max(0.0, self._x_to_ms(float(event.x)))
            self._update_playhead_label()
            self.redraw()
            return

        idx, mode = self._hit_test(event.x, event.y)

        if idx is not None:
            old_sel = self.selected_index
            self.selected_index = idx
            if old_sel != idx:
                self.redraw()
                if self.on_select_callback:
                    self.on_select_callback(idx)
            ev = self.events[idx]
            self._drag = {
                'mode':      mode,
                'idx':       idx,
                'start_x':   float(event.x),
                'orig_time': ev['time'],
                'orig_dur':  ev['params'].get('duration_ms', 0),
                'moved':     False,
                'history_pushed': False,  # push once when drag actually moves
            }
        else:
            # Click on empty canvas — deselect and prepare background pan
            if self.selected_index is not None:
                self.selected_index = None
                self.redraw()
            self._pan_drag = {
                'start_x':  float(event.x),
                'orig_pan': self.pan_offset_ms,
            }

    def _on_ldrag(self, event):
        x = float(event.x)

        if self._playhead_drag:
            raw_ms = max(0.0, self._x_to_ms(x))
            if self._snap_interval_ms > 0:
                threshold_ms = self.SNAP_THRESHOLD_PX * 1000.0 / max(self.zoom, 0.001)
                grid_ms = round(raw_ms / self._snap_interval_ms) * self._snap_interval_ms
                if abs(raw_ms - grid_ms) <= threshold_ms:
                    raw_ms = grid_ms
            self._playhead_ms = raw_ms
            self._update_playhead_label()
            self.redraw()
            return

        if self._drag is not None:
            dx = x - self._drag['start_x']
            if abs(dx) > 3:
                self._drag['moved'] = True

            if self._drag['moved']:
                if not self._drag['history_pushed']:
                    self._push_history()
                    self._drag['history_pushed'] = True
                delta_ms = dx * 1000.0 / self.zoom
                idx  = self._drag['idx']

                if self._drag['mode'] == 'move':
                    raw_ms = self._drag['orig_time'] + delta_ms
                    snapped = self._apply_snap(raw_ms, dur_ms=float(self._drag['orig_dur']))
                    self.events[idx]['time'] = max(0, int(snapped))
                elif self._drag['mode'] == 'resize':  # right-edge resize
                    raw_end_ms = self._drag['orig_time'] + self._drag['orig_dur'] + delta_ms
                    start_ms = float(self.events[idx]['time'])
                    snapped_end = self._snap_end(raw_end_ms)
                    new_dur = max(100, int(snapped_end - start_ms))
                    self.events[idx]['params']['duration_ms'] = new_dur
                else:  # resize_left — left-edge resize
                    raw_start = self._drag['orig_time'] + delta_ms
                    orig_end = self._drag['orig_time'] + self._drag['orig_dur']
                    snapped_start = self._snap_start(raw_start)
                    new_start = max(0, int(snapped_start))
                    new_dur = max(100, int(orig_end - new_start))
                    self.events[idx]['time'] = new_start
                    self.events[idx]['params']['duration_ms'] = new_dur

                self.redraw()

        elif self._pan_drag is not None:
            dx = x - self._pan_drag['start_x']
            self.pan_offset_ms = max(0.0,
                                     self._pan_drag['orig_pan'] - dx * 1000.0 / self.zoom)
            self.redraw()

        self._update_cursor(event.x, event.y)

    def _on_lrelease(self, event):
        if self._drag is not None and self._drag['moved']:
            idx  = self._drag['idx']
            ev   = self.events[idx]
            mode = self._drag['mode']

            if mode == 'move':
                if self.auto_sort_var.get():
                    ref = ev
                    self.events.sort(key=lambda e: e['time'])
                    try:
                        self.selected_index = self.events.index(ref)
                    except ValueError:
                        self.selected_index = idx
                self.redraw()
                if self.on_move_callback:
                    self.on_move_callback(self.selected_index, ev['time'])
                if self.change_callback:
                    self.change_callback()

            else:  # resize
                self.redraw()
                if self.on_resize_callback:
                    self.on_resize_callback(idx, ev['params'].get('duration_ms', 0))
                if self.change_callback:
                    self.change_callback()

        self._drag           = None
        self._pan_drag       = None
        self._playhead_drag  = False
        self._snap_target_ms = None

    def _on_double_click(self, event):
        idx, _ = self._hit_test(event.x, event.y)
        if idx is not None:
            self.selected_index = idx
            self.redraw()
            if self.on_select_callback:
                self.on_select_callback(idx)

    def _on_mpress(self, event):
        self._pan_drag = {'start_x': float(event.x), 'orig_pan': self.pan_offset_ms}

    def _on_mdrag(self, event):
        if self._pan_drag:
            dx = float(event.x) - self._pan_drag['start_x']
            self.pan_offset_ms = max(0.0,
                                     self._pan_drag['orig_pan'] - dx * 1000.0 / self.zoom)
            self.redraw()

    def _on_mrelease(self, event):
        self._pan_drag = None

    def _on_mousewheel(self, event):
        """Windows / macOS scroll wheel. Plain = zoom, Ctrl = pan."""
        if event.state & 0x0004:  # Ctrl held → pan
            vis = self._visible_ms()
            delta_ms = (-event.delta / 120.0) * vis * 0.15
            self.pan_offset_ms = max(0.0, self.pan_offset_ms + delta_ms)
            self.redraw()
        else:                      # plain scroll → zoom
            factor = 1.2 if event.delta > 0 else (1.0 / 1.2)
            self._zoom_at(factor, float(event.x))

    def _on_scroll_up(self, event):   # Linux Button-4
        if event.state & 0x0004:  # Ctrl → pan
            vis = self._visible_ms()
            self.pan_offset_ms = max(0.0, self.pan_offset_ms - vis * 0.15)
            self.redraw()
        else:                      # plain → zoom in
            self._zoom_at(1.2, float(event.x))

    def _on_scroll_down(self, event):  # Linux Button-5
        if event.state & 0x0004:  # Ctrl → pan
            vis = self._visible_ms()
            self.pan_offset_ms = max(0.0, self.pan_offset_ms + vis * 0.15)
            self.redraw()
        else:                      # plain → zoom out
            self._zoom_at(1.0 / 1.2, float(event.x))

    def _zoom_at(self, factor: float, screen_x: float):
        """Apply zoom factor, keeping the time at *screen_x* stationary."""
        time_at_x = self._x_to_ms(screen_x)
        self.zoom = max(0.1, min(2000.0, self.zoom * factor))
        # Recalculate pan so time_at_x stays under screen_x
        self.pan_offset_ms = max(
            0.0,
            time_at_x - (screen_x - self.LEFT_MARGIN) * 1000.0 / self.zoom
        )
        self.redraw()

    def _on_rclick(self, event):
        idx, _ = self._hit_test(event.x, event.y)
        if idx is not None:
            self.selected_index = idx
            self.redraw()
            if self.on_select_callback:
                self.on_select_callback(idx)
            try:
                self._ctx.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx.grab_release()
        else:
            self._add_time_ms = max(0, int(self._x_to_ms(float(event.x))))
            try:
                self._ctx_bg.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx_bg.grab_release()

    def _on_canvas_resize(self, event):
        self.redraw()

    def _on_motion(self, event):
        self._update_cursor(event.x, event.y)

    def _update_cursor(self, x, y):
        if y < self.RULER_H:
            self.canvas.config(cursor='hand2')
            return
        _, mode = self._hit_test(x, y)
        if mode in ('resize', 'resize_left'):
            self.canvas.config(cursor='sb_h_double_arrow')
        elif mode == 'move':
            self.canvas.config(cursor='fleur')
        else:
            self.canvas.config(cursor='')

    # ------------------------------------------------------------------ #
    # Toolbar / context menu actions                                       #
    # ------------------------------------------------------------------ #

    def _ctx_edit(self):
        if self.selected_index is not None and self.on_select_callback:
            self.on_select_callback(self.selected_index)

    def _ctx_change_type(self):
        if self.selected_index is not None and self.change_type_callback:
            self.change_type_callback(self.selected_index)

    def _on_toolbar_add(self):
        self._add_time_ms = None
        if self.add_callback:
            self.add_callback()

    def _on_add_at_ctx(self):
        if self.add_callback:
            self.add_callback(int(self._playhead_ms))
        self._add_time_ms = None

    def _on_remove(self):
        if self.selected_index is not None:
            self.remove_event(self.selected_index)

    def _on_duplicate(self):
        if self.duplicate_callback:
            self.duplicate_callback()

    def _on_arrow(self, frames: int):
        """Move playhead by *frames* frames (negative = backward)."""
        self._playhead_ms = max(0.0, min(
            float(self.total_ms),
            self._playhead_ms + frames * self._frame_ms
        ))
        self._update_playhead_label()
        self.redraw()

    def _on_seek_ms(self, delta_ms: float):
        """Move playhead by a fixed number of milliseconds (negative = backward)."""
        self._playhead_ms = max(0.0, min(
            float(self.total_ms),
            self._playhead_ms + delta_ms
        ))
        self._update_playhead_label()
        self.redraw()

    def _on_change_time_btn(self):
        if self.on_change_time:
            self.on_change_time()


_VIDEO_POLL_MS = 33  # ~30 fps polling interval for video playback


class VideoPanel(ttk.Frame):
    """
    Embeds a video player into a Tkinter Frame using python-vlc.
    VLC renders directly to the canvas HWND — no frame transfer needed.
    Seeking and play/pause are near-instant.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # VLC objects (created once on first load)
        self._vlc_inst = None     # vlc.Instance
        self._vlc_mp = None       # vlc.MediaPlayer
        # Playback state
        self._poll_id = None
        self._playing = False
        self._fps: float = 30.0
        self._duration_s: float = 0.0
        self._seek_updating = False   # suppress seek callback while programmatically moving bar
        self._on_playback_tick = None   # Callable[[float], None] set by dialog
        self._on_duration_known = None  # Callable[[float], None] fired with duration_ms
        self._meta_cached = False
        self._label_tick: int = 0
        self._time_show_remaining = False   # toggled by clicking the time label

        # Pack order matters: BOTTOM items stack upward, canvas fills remaining space.
        # Controls bar (bottom-most)
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, side=tk.BOTTOM)

        self._play_btn = ttk.Button(ctrl, text='\u25b6 Play', width=8, command=self.toggle_play)
        self._play_btn.pack(side=tk.LEFT, padx=4, pady=2)

        ttk.Label(ctrl, text='Vol:').pack(side=tk.LEFT)
        self._vol_var = tk.IntVar(value=80)
        ttk.Scale(ctrl, from_=0, to=100, orient='horizontal',
                  variable=self._vol_var, length=80,
                  command=self._on_vol_change).pack(side=tk.LEFT, padx=(0, 8))

        self._time_label = ttk.Label(ctrl, text='0:00 / 0:00', width=16, cursor='hand2')
        self._time_label.pack(side=tk.LEFT)
        self._time_label.bind('<Button-1>', self._toggle_time_mode)

        self._status_label = ttk.Label(ctrl, text='No video loaded', foreground='gray')
        self._status_label.pack(side=tk.LEFT, padx=8)

        # Seek bar (above controls)
        seek_frame = ttk.Frame(self)
        seek_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=(0, 1))
        self._seek_var = tk.DoubleVar(value=0.0)
        self._seek_bar = ttk.Scale(seek_frame, from_=0.0, to=1.0, orient='horizontal',
                                   variable=self._seek_var, command=self._on_seek_bar)
        self._seek_bar.pack(fill=tk.X)
        self._seek_bar.bind('<Button-1>', self._on_seek_click)
        self._seek_bar.bind('<B1-Motion>', self._on_seek_click)

        # Video canvas (fills remaining space above seek bar)
        self._canvas = tk.Canvas(self, bg='black')
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Keyboard callbacks — set by dialog after construction
        self.on_arrow: Optional[callable] = None        # fn(frames: int)
        self.on_seek_ms: Optional[callable] = None      # fn(delta_ms: float)
        self.on_play_pause: Optional[callable] = None   # fn()

        # Bind keys to canvas and toplevel (whichever has focus)
        for widget in (self._canvas, self):
            widget.bind('<space>',               lambda e: self.on_play_pause() if self.on_play_pause else None)
            widget.bind('<Left>',                lambda e: self.on_arrow(-1)    if self.on_arrow    else None)
            widget.bind('<Right>',               lambda e: self.on_arrow(1)     if self.on_arrow    else None)
            widget.bind('<Shift-Left>',          lambda e: self.on_arrow(-30)   if self.on_arrow    else None)
            widget.bind('<Shift-Right>',         lambda e: self.on_arrow(30)    if self.on_arrow    else None)
            widget.bind('<Shift-Control-Left>',  lambda e: self.on_seek_ms(-30_000) if self.on_seek_ms else None)
            widget.bind('<Shift-Control-Right>', lambda e: self.on_seek_ms(30_000)  if self.on_seek_ms else None)
        self._canvas.bind('<Button-1>', lambda e: self._canvas.focus_set())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: str) -> bool:
        """Load a video file. Returns True on success."""
        try:
            import vlc as _vlc
        except ImportError:
            self._status_label.config(
                text='python-vlc not installed — run: pip install python-vlc')
            return False
        # Create VLC instance once.
        # --avcodec-hw=none  : disable FFmpeg hardware video decoding
        # --vout=wingdi       : force Windows GDI video output (avoids D3D9/D3D11
        #                       renderer crashes for certain encoded files)
        if self._vlc_inst is None:
            self._vlc_inst = _vlc.Instance(
                '--no-xlib --quiet --no-video-title-show '
                '--avcodec-hw=none --vout=wingdi')
            self._vlc_mp = self._vlc_inst.media_player_new()
            em = self._vlc_mp.event_manager()
            em.event_attach(_vlc.EventType.MediaPlayerEndReached,
                            lambda _e: self.after(0, self._on_eof))
        # Reset state
        self._playing = False
        self._play_btn.config(text='\u25b6 Play')
        self._meta_cached = False
        self._duration_s = 0.0
        import os
        self._status_label.config(text=f'Loading {os.path.basename(path)}\u2026')
        media = self._vlc_inst.media_new(path)
        # Disable hardware video decoding per-media as a belt-and-suspenders
        # measure in case the Instance was already created without the flag.
        media.add_option(':avcodec-hw=none')
        self._vlc_mp.set_media(media)
        # Ensure the canvas HWND is realized before passing to VLC.
        # The video window may be withdrawn; update_idletasks forces HWND creation.
        self._canvas.winfo_toplevel().update_idletasks()
        self._vlc_mp.set_hwnd(self._canvas.winfo_id())
        self._vlc_mp.audio_set_volume(int(self._vol_var.get()))
        # NOTE: parse_with_options is intentionally omitted — it triggers an
        # async VLC thread that races with play() and can crash for large files.
        # Duration/fps are obtained via the poll loop once play() starts.
        self._vlc_mp.play()
        self.after(300, self._pause_after_first_frame)
        self._start_poll()
        return True

    def seek(self, ms: float):
        """Seek to position in milliseconds."""
        if self._vlc_mp is None:
            return
        self._vlc_mp.set_time(max(0, int(ms)))
        # Immediately update UI so timeline stays in sync
        self._update_time_label_from_ms(ms)
        if self._on_playback_tick is not None:
            self._on_playback_tick(float(ms))

    def toggle_play(self):
        """Toggle between play and pause."""
        if self._vlc_mp is None:
            return
        if self._playing:
            self._playing = False
            self._play_btn.config(text='\u25b6 Play')
            self._vlc_mp.pause()
        else:
            self._playing = True
            self._play_btn.config(text='\u23f8 Pause')
            self._vlc_mp.play()

    def stop(self):
        """Stop playback and release VLC media."""
        self._stop_poll()
        self._playing = False
        if hasattr(self, '_play_btn'):
            self._play_btn.config(text='\u25b6 Play')
        if self._vlc_mp is not None:
            try:
                self._vlc_mp.stop()
            except Exception:
                pass

    def destroy(self):
        """Ensure VLC resources are released before widget destruction."""
        self.stop()
        if self._vlc_mp is not None:
            try:
                self._vlc_mp.release()
            except Exception:
                pass
            self._vlc_mp = None
        if self._vlc_inst is not None:
            try:
                self._vlc_inst.release()
            except Exception:
                pass
            self._vlc_inst = None
        super().destroy()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pause_after_first_frame(self):
        """Called 300 ms after load() — pause VLC and read metadata."""
        if self._vlc_mp is None:
            return
        if not self._playing:
            self._vlc_mp.pause()
        if not self._meta_cached:
            self._read_metadata()

    def _read_metadata(self):
        """Read duration and fps from VLC after media is parsed."""
        if self._vlc_mp is None:
            return
        try:
            dur_ms = self._vlc_mp.get_length()
            if dur_ms > 0 and not self._meta_cached:
                self._duration_s = dur_ms / 1000.0
                self._seek_bar.config(to=float(self._duration_s))
                self._meta_cached = True
                # Use get_fps() rather than tracks_get() — the latter returns
                # raw ctypes pointers whose .contents dereference can segfault
                # if VLC frees the track structs concurrently.
                fps = self._vlc_mp.get_fps()
                if fps > 0:
                    self._fps = fps
                if self._on_duration_known is not None:
                    self._on_duration_known(float(dur_ms))
                # Update status to just the filename
                import os
                try:
                    path = self._vlc_mp.get_media().get_mrl()
                    # mrl may be file:///... — extract base name
                    from urllib.parse import unquote
                    name = os.path.basename(unquote(path.replace('file:///', '').replace('file://', '')))
                    self._status_label.config(text=name)
                except Exception:
                    self._status_label.config(text='Loaded')
        except Exception:
            pass

    def _on_eof(self):
        """VLC end-of-file — called on Tkinter thread via after(0)."""
        self._playing = False
        if hasattr(self, '_play_btn'):
            self._play_btn.config(text='\u25b6 Play')

    def _on_vol_change(self, *_):
        if self._vlc_mp is not None:
            try:
                self._vlc_mp.audio_set_volume(int(self._vol_var.get()))
            except Exception:
                pass

    def _on_canvas_resize(self, event):
        """Canvas resized — re-attach VLC HWND so it fills the new size."""
        if self._vlc_mp is not None:
            try:
                self._vlc_mp.set_hwnd(self._canvas.winfo_id())
            except Exception:
                pass

    def _start_poll(self):
        self._stop_poll()
        self._poll_loop()

    def _stop_poll(self):
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None

    def _poll_loop(self):
        """Poll VLC position and update UI — no frame transfer needed."""
        if self._vlc_mp is not None:
            # Check for VLC error state
            try:
                import vlc as _vlc
                state = self._vlc_mp.get_state()
                if state == _vlc.State.Error:
                    self._status_label.config(
                        text='Video error — try a different file', foreground='red')
                    self._playing = False
                    if hasattr(self, '_play_btn'):
                        self._play_btn.config(text='\u25b6 Play')
                    self._poll_id = None
                    return
            except Exception:
                pass

            # Try to read metadata if not yet cached
            if not self._meta_cached:
                self._read_metadata()

            if self._playing:
                ms = self._vlc_mp.get_time()
                if ms >= 0:
                    self._update_time_label_from_ms(float(ms))
                    if self._on_playback_tick is not None:
                        self._on_playback_tick(float(ms))

        self._poll_id = self.after(_VIDEO_POLL_MS, self._poll_loop)

    def _toggle_time_mode(self, *_):
        """Toggle between elapsed and remaining time display."""
        self._time_show_remaining = not self._time_show_remaining
        self._label_tick = 0  # force immediate redraw
        if self._vlc_mp is not None:
            self._update_time_label_from_ms(float(max(0, self._vlc_mp.get_time())))

    def _update_time_label_from_ms(self, ms: float):
        """Update time label and seek bar from position in milliseconds (throttled)."""
        try:
            cur_s = max(0.0, ms / 1000.0)
            length = self._duration_s
            self._label_tick += 1
            if self._label_tick % 6 == 0 or not self._playing:
                def fmt(s): return f'{int(s) // 60}:{int(s) % 60:02d}'
                if self._time_show_remaining and length > 0:
                    remaining = max(0.0, length - cur_s)
                    self._time_label.config(text=f'-{fmt(remaining)} / {fmt(length)}')
                else:
                    self._time_label.config(text=f'{fmt(cur_s)} / {fmt(length)}')
                if length > 0 and not self._seek_updating:
                    self._seek_updating = True
                    self._seek_var.set(cur_s)
                    self._seek_updating = False

            if length > 0 and self._on_duration_known is not None:
                self._on_duration_known(float(length) * 1000.0)
        except Exception:
            pass

    def _on_seek_click(self, event):
        """Click or drag on the seek bar — jump directly to that position."""
        if self._duration_s <= 0 or self._vlc_mp is None:
            return 'break'
        w = self._seek_bar.winfo_width()
        if w <= 0:
            return 'break'
        frac = max(0.0, min(1.0, event.x / w))
        pos_s = frac * self._duration_s
        self._seek_bar.set(pos_s)   # fires _on_seek_bar via command callback
        return 'break'              # suppress default ttk.Scale step behaviour

    def _on_seek_bar(self, val):
        """Seek bar value changed (by poll update or _on_seek_click)."""
        if self._seek_updating or self._vlc_mp is None:
            return
        pos_s = float(val)
        self._vlc_mp.set_time(max(0, int(pos_s * 1000)))
        self._update_time_label_from_ms(pos_s * 1000.0)
        if self._on_playback_tick is not None:
            self._on_playback_tick(pos_s * 1000.0)

class CustomEventsBuilderDialog(tk.Toplevel):
    """
    Main dialog for visual custom events timeline building.

    Layout: two-zone vertical PanedWindow.
      - Top zone: EventLibraryPanel (left) + ParameterPanel (right)
      - Bottom zone: CanvasTimelinePanel (full width)
    """

    def __init__(self, parent, config=None, last_processed_filename=None, last_processed_directory=None):
        super().__init__(parent)
        self.title("Custom Event Builder")
        self.resizable(True, True)

        screen_h = self.winfo_screenheight()
        dialog_h = min(900, screen_h - 48)
        self.geometry(f"1200x{dialog_h}")
        self.transient(parent)
        self.grab_set()

        # Store config
        self.config = config if config is not None else {}
        self.last_processed_filename  = last_processed_filename
        self.last_processed_directory = last_processed_directory

        # State
        self.event_file_path        = None
        self.event_definitions      = {}
        self.event_groups           = []
        self.normalization_config   = {}
        self.backup_path            = None
        self.current_event_for_params   = None
        self.current_editing_index      = None  # index of the event loaded in params panel

        # Load event definitions
        try:
            with open(EVENT_DEFINITIONS_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            self.event_definitions    = config_data.get('definitions', {})
            self.event_groups         = config_data.get('groups', [])
            self.normalization_config = config_data.get('normalization', {})

            if not self.event_groups:
                self.event_groups = [
                    {'name': 'General', 'prefix': '',        'description': 'General-purpose events'},
                    {'name': 'MCB',     'prefix': 'mcb_',    'description': 'MCB audio events'},
                    {'name': 'Clutch',  'prefix': 'clutch_', 'description': 'Clutch conditioning events'},
                ]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load event definitions: {e}", parent=self)
            self.destroy()
            return

        # Tk variables
        self.event_file_var      = tk.StringVar()
        self.backup_var          = tk.BooleanVar(value=True)
        self.headroom_var        = tk.IntVar(value=10)
        self.show_waveform_var   = tk.BooleanVar(value=True)
        self.is_dirty            = False

        self.setup_ui()
        self._load_funscript_duration()
        self._auto_load_events_file()
        # Sync canvas to current theme and listen for changes
        CanvasTimelinePanel.apply_canvas_theme(_theme.is_dark())
        self.timeline_panel.redraw()
        _theme.register(self._on_theme_change)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _on_close(self):
        if self.is_dirty and self.timeline_panel.events:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                parent=self
            )
            if result is True:        # Yes → save then close
                self.on_save_file()
                if self.is_dirty:     # save failed or was cancelled by user
                    return
            elif result is None:      # Cancel → abort close
                return
            # False → No, discard changes and close
        _theme.unregister(self._on_theme_change)
        self._video_panel.stop()
        # Delay destroy by 300 ms so ffpyplayer's internal C thread has time to
        # wind down after close_player(). Creating a new MediaPlayer while the old
        # one's SDL thread is still running causes an access violation in SDL2_mixer.
        self.after(300, self.destroy)

    def _on_theme_change(self, dark: bool):
        CanvasTimelinePanel.apply_canvas_theme(dark)
        self.timeline_panel.redraw()
        self._dark_toggle_btn.config(text='\u2600 Light' if dark else '\u263d Dark')

    def _on_waveform_toggle(self):
        self.timeline_panel.show_funscript = self.show_waveform_var.get()
        self.timeline_panel.redraw()

    def _toggle_dark_mode(self):
        _theme.toggle()  # sv_ttk with root=None applies to all windows

    # ------------------------------------------------------------------ #
    # UI construction                                                       #
    # ------------------------------------------------------------------ #

    def setup_ui(self):
        """Build the main UI layout (vertical PanedWindow)."""
        self.create_file_bar()

        # Pack bottom bars first to reserve space
        self.create_action_bar()
        self.create_options_bar()

        # Main content: vertical PanedWindow (top = library+params, bottom = timeline)
        self.main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Top pane: Library (left) + Parameters (right) ---
        top_paned = ttk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL)
        self.main_paned.add(top_paned, weight=2)

        library_outer = ttk.LabelFrame(top_paned, text="Event Library", padding=5)
        self.library_panel = EventLibraryPanel(
            library_outer, self.event_definitions,
            self.event_groups, self.on_library_event_selected
        )
        self.library_panel.pack(fill=tk.BOTH, expand=True)
        top_paned.add(library_outer, weight=1)

        # Wire Add-to-Timeline button
        self.library_panel.add_to_timeline_btn.config(command=self.on_add_event_to_timeline)

        params_outer = ttk.LabelFrame(top_paned, text="Parameters", padding=5)
        self.params_panel = ParameterPanel(params_outer, apply_callback=self.on_apply_parameters)
        self.params_panel.save_default_callback = self.on_save_event_defaults
        self.params_panel.pack(fill=tk.BOTH, expand=True)
        top_paned.add(params_outer, weight=2)

        # Event List (third top panel)
        list_outer = ttk.LabelFrame(top_paned, text="Event List", padding=5)
        self._event_list = ttk.Treeview(
            list_outer, columns=('time', 'name', 'dur'),
            show='headings', selectmode='browse'
        )
        self._event_list.heading('time', text='Time')
        self._event_list.heading('name', text='Event')
        self._event_list.heading('dur',  text='Duration')
        self._event_list.column('time', width=50, anchor='e', stretch=False)
        self._event_list.column('name', width=90, anchor='w')
        self._event_list.column('dur',  width=50, anchor='e', stretch=False)
        _ls = ttk.Scrollbar(list_outer, orient='vertical', command=self._event_list.yview)
        self._event_list.configure(yscrollcommand=_ls.set)
        self._event_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _ls.pack(side=tk.RIGHT, fill=tk.Y)
        self._event_list.bind('<<TreeviewSelect>>', self._on_event_list_select)
        top_paned.add(list_outer, weight=1)

        # --- Bottom pane: Timeline ---
        timeline_outer = ttk.LabelFrame(self.main_paned, text='Timeline', padding=5)
        self.main_paned.add(timeline_outer, weight=1)

        self.timeline_panel = CanvasTimelinePanel(
            timeline_outer,
            on_select_callback=self.on_canvas_event_select,
            on_move_callback=self.on_canvas_event_move,
            on_resize_callback=self.on_canvas_event_resize,
            change_callback=lambda: self.set_dirty(True),
            add_callback=self.on_add_event_to_timeline_direct,
            duplicate_callback=self.on_duplicate_timeline_event,
            change_type_callback=self.on_change_event_type,
        )
        self.timeline_panel.pack(fill=tk.BOTH, expand=True)

        # Wire "Change Time" action
        self.timeline_panel.on_change_time = self.on_change_timeline_event_time

        # Wire event list refresh to every timeline redraw
        self.timeline_panel.on_redraw_callback = self._refresh_event_list

        # --- Floating video window (hidden until toggled) ---
        self._video_win = tk.Toplevel(self)
        self._video_win.withdraw()  # hide immediately — before geometry/content, avoids WM focus-steal on Windows
        self._video_win.title('Video')
        self._video_win.geometry('800x500')
        self._video_win.protocol('WM_DELETE_WINDOW', self._on_video_win_close)
        self._video_panel = VideoPanel(self._video_win)
        self._video_panel.pack(fill=tk.BOTH, expand=True)
        self._video_driving = False       # True while video tick is updating playhead
        self._seek_settling_count = 0     # >0 while a seek is still settling; suppresses video tick
        self._video_tick_count = 0        # counts video ticks; used to throttle timeline redraws

        # Wire playhead ↔ video sync
        self.timeline_panel.on_playhead_change = self._on_playhead_change
        self.timeline_panel.play_pause_callback = self._video_panel.toggle_play
        self._video_panel._on_playback_tick = self._on_video_tick
        self._video_panel._on_duration_known = self._on_video_duration_known

        # Forward video-window key events to the timeline panel methods
        self._video_panel.on_arrow     = self.timeline_panel._on_arrow
        self._video_panel.on_seek_ms   = self.timeline_panel._on_seek_ms
        self._video_panel.on_play_pause = self._video_panel.toggle_play

        # Set initial sash position after layout is realised
        self.after(100, self._init_sash)

    def _init_sash(self):
        """Set initial sash so the timeline is tall enough to show the funscript track."""
        self.update_idletasks()
        try:
            total = self.main_paned.winfo_height()
            if total < 200:
                self.after(100, self._init_sash)
                return
            # Give timeline ~200 px — enough to show ruler + events + funscript waveform
            self.main_paned.sashpos(0, max(100, total - 200))
        except tk.TclError:
            pass

    def _refresh_event_list(self):
        """Rebuild the Event List Treeview from the current timeline state."""
        tp = self.timeline_panel
        self._event_list.delete(*self._event_list.get_children())
        for i, ev in enumerate(tp.events):
            t_ms  = ev['time']
            m, s  = divmod(t_ms // 1000, 60)
            t_str = f"{m}:{s:02d}"
            name  = CanvasTimelinePanel.format_event_display_name(ev['name'])
            dur   = ev['params'].get('duration_ms', 0)
            d_str = f"{dur // 1000}s" if dur else '—'
            iid   = str(i)
            tags  = ('conflict',) if i in tp._conflicts else ()
            self._event_list.insert('', 'end', iid=iid,
                                    values=(t_str, name, d_str), tags=tags)
        self._event_list.tag_configure('conflict', foreground='#ff6600')

        sel = str(tp.selected_index) if tp.selected_index is not None else None
        if sel and self._event_list.exists(sel):
            self._event_list.selection_set(sel)
            self._event_list.see(sel)
        else:
            self._event_list.selection_set()

    def _on_event_list_select(self, _event):
        """Sync canvas when the user clicks a row in the Event List."""
        sel = self._event_list.selection()
        if not sel:
            return
        idx = int(sel[0])
        tp = self.timeline_panel
        if idx == tp.selected_index:
            return
        tp.selected_index = idx
        tp._scroll_into_view(tp.events[idx]['time'])
        tp.redraw()
        if tp.on_select_callback:
            tp.on_select_callback(idx)

    def create_file_bar(self):
        """Create file operations bar."""
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, expand=False, padx=5, pady=(5, 0))

        ttk.Label(file_frame, text="Event File:").pack(side=tk.LEFT, padx=(0, 5))
        file_entry = ttk.Entry(file_frame, textvariable=self.event_file_var, state='readonly')
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(file_frame, text="New",  command=self.on_new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Load", command=self.on_load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save", command=self.on_save_file).pack(side=tk.LEFT, padx=2)

    def create_options_bar(self):
        """Create options bar."""
        options_frame = ttk.LabelFrame(self, text="Options", padding=5)
        options_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=5, pady=5)

        ttk.Checkbutton(options_frame, text="Backup files",
                        variable=self.backup_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(options_frame, text="Headroom:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Spinbox(options_frame, from_=0, to=20, textvariable=self.headroom_var,
                    width=5).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(options_frame, text="Show waveform",
                        variable=self.show_waveform_var,
                        command=self._on_waveform_toggle).pack(side=tk.LEFT, padx=(15, 5))

    def create_action_bar(self):
        """Create action buttons bar."""
        action_frame = ttk.Frame(self)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=5, pady=(0, 5))

        ttk.Button(action_frame, text="View YAML", command=self.on_view_yaml).pack(side=tk.LEFT, padx=2)

        self._dark_toggle_btn = ttk.Button(
            action_frame,
            text='\u263d Dark' if not _theme.is_dark() else '\u2600 Light',
            width=8,
            command=self._toggle_dark_mode,
        )
        self._dark_toggle_btn.pack(side=tk.LEFT, padx=2)

        self._video_toggle_btn = ttk.Button(
            action_frame, text='\u25b6 Video', width=9, command=self._toggle_video_panel)
        self._video_toggle_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text='Load Video',
                   command=self._load_video_dialog).pack(side=tk.LEFT, padx=2)

        self.apply_button = ttk.Button(action_frame, text="Apply Effects",
                                       command=self.on_apply_effects)
        self.apply_button.pack(side=tk.LEFT, padx=2)

        self.restore_button = ttk.Button(action_frame, text="Restore Backup",
                                         command=self.on_restore_backup, state='disabled')
        self.restore_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT, padx=2)

        self.status_label = ttk.Label(action_frame, text="Ready. Select or load an event file.")
        self.status_label.pack(side=tk.RIGHT, padx=10)

    # ------------------------------------------------------------------ #
    # Video panel                                                          #
    # ------------------------------------------------------------------ #

    def _toggle_video_panel(self):
        """Show or hide the floating video window."""
        if self._video_win.winfo_ismapped():
            self._video_win.withdraw()
            self._video_toggle_btn.config(text='\u25b6 Video')
        else:
            self._video_win.deiconify()
            self._video_win.lift()
            self._video_toggle_btn.config(text='\u23f9 Video')

    def _on_video_win_close(self):
        """User closed the video window via the X button."""
        self._video_win.withdraw()
        self._video_toggle_btn.config(text='\u25b6 Video')

    def _load_video_dialog(self):
        """Open file picker to load a video file into the video panel."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title='Select Video File',
            filetypes=[('Video files', '*.mp4 *.mkv *.avi *.mov *.wmv *.m4v'),
                       ('All files', '*.*')],
            parent=self,
        )
        if path:
            # Show the video window before loading so the canvas HWND is
            # realized and valid when VLC calls set_hwnd().
            if not self._video_win.winfo_ismapped():
                self._toggle_video_panel()
            self._video_panel.load(path)

    def _try_auto_load_video(self):
        """Look for a matching video file in the same directory as the events file."""
        if not self.last_processed_directory or not self.last_processed_filename:
            return
        from pathlib import Path
        for ext in ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v',
                    '.MP4', '.MKV', '.AVI', '.MOV', '.WMV', '.M4V'):
            candidate = Path(self.last_processed_directory) / f'{self.last_processed_filename}{ext}'
            if candidate.exists():
                self._video_panel.load(str(candidate))
                return  # load silently; panel stays hidden until user shows it

    def _on_playhead_change(self, ms: float):
        """Timeline playhead moved → seek video. Works during playback too."""
        if not self._video_driving:
            self._video_panel.seek(ms)
            # Suppress video tick from overwriting the playhead until the seek settles
            self._seek_settling_count += 1
            self.after(300, self._dec_seek_settling)

    def _dec_seek_settling(self):
        self._seek_settling_count = max(0, self._seek_settling_count - 1)

    def _on_video_tick(self, ms: float):
        """Video playback position update (~30 fps) → drive timeline playhead."""
        if self._seek_settling_count > 0:
            return  # seek still settling; don't overwrite the playhead
        self._video_driving = True
        self._video_tick_count += 1
        try:
            self.timeline_panel._playhead_ms = ms
            self.timeline_panel._update_playhead_label()
            # Auto-scroll: page forward when playhead runs off the right edge during playback
            if self._video_panel._playing:
                vis = self.timeline_panel._visible_ms()
                if ms > self.timeline_panel.pan_offset_ms + vis:
                    self.timeline_panel.pan_offset_ms = max(0.0, ms - vis * 0.2)
            # Redraw timeline at ~15 fps (every other video tick) to reduce canvas overhead
            if self._video_tick_count % 2 == 0:
                self.timeline_panel.redraw()
        finally:
            self._video_driving = False

    def _on_video_duration_known(self, duration_ms: float):
        """Called when the video's duration and fps are read from metadata."""
        if duration_ms > self.timeline_panel.total_ms:
            self.timeline_panel.set_duration(int(duration_ms))
        fps = self._video_panel._fps
        if fps > 0:
            self.timeline_panel._frame_ms = 1000.0 / fps

    # ------------------------------------------------------------------ #
    # Funscript duration loading                                           #
    # ------------------------------------------------------------------ #

    def _load_funscript_duration(self):
        """Read the loaded funscript to determine total duration for timeline scaling."""
        if not self.last_processed_filename or not self.last_processed_directory:
            return
        try:
            funscript_path = self.last_processed_directory / f"{self.last_processed_filename}.funscript"
            if funscript_path.exists():
                with open(funscript_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                actions = data.get('actions', [])
                if actions:
                    max_at_ms = max(float(a['at']) for a in actions)
                    total_ms  = int(max_at_ms) + 5000
                    self.timeline_panel.set_duration(total_ms)
                    self.timeline_panel.set_funscript(actions)
        except Exception:
            pass  # Silently fall back to default duration

    # ------------------------------------------------------------------ #
    # Auto-load                                                            #
    # ------------------------------------------------------------------ #

    def _auto_load_events_file(self):
        """Automatically load the .events.yml matching the last processed file."""
        if not self.last_processed_filename or not self.last_processed_directory:
            return

        events_file_path = self.last_processed_directory / f"{self.last_processed_filename}.events.yml"
        if not events_file_path.exists():
            return

        try:
            with open(events_file_path, 'r') as f:
                data = yaml.safe_load(f)
            events = data.get('events', [])
            if events is not None:
                self.timeline_panel.load_events_from_yaml(events)
                self.event_file_path = events_file_path
                self.event_file_var.set(str(self.event_file_path))
                self.set_dirty(False)
                if events:
                    self.status_label.config(
                        text=f"Auto-loaded {len(events)} events from {events_file_path.name}")
                else:
                    self.status_label.config(
                        text=f"Auto-loaded empty event file: {events_file_path.name}")
        except Exception:
            self.status_label.config(text="Ready. Could not auto-load events file.")

        if self.event_file_path:
            self._try_load_matching_funscript(self.event_file_path)

    # ------------------------------------------------------------------ #
    # Dirty / apply-button state                                          #
    # ------------------------------------------------------------------ #

    def set_dirty(self, dirty=True):
        self.is_dirty = dirty
        if dirty:
            self.apply_button.config(text="Save and Apply Effects")
        else:
            self.apply_button.config(text="Apply Effects")

    # ------------------------------------------------------------------ #
    # Canvas timeline callbacks                                            #
    # ------------------------------------------------------------------ #

    def on_canvas_event_select(self, idx: Optional[int]):
        """Called when the user clicks an event block (or None on deselect/remove)."""
        if idx is None:
            self.current_editing_index = None
            self.params_panel.show_placeholder()
            self.params_panel.editing_label.config(text="")
            self.params_panel.title_label.config(text="Parameters")
            return

        self.current_editing_index = idx
        event_data = self.timeline_panel.get_event(idx)
        if not event_data:
            return
        event_def = self.event_definitions.get(event_data['name'])
        if not event_def:
            return

        event_number = idx + 1
        self.params_panel.load_event_parameters(
            event_data['name'], event_def,
            event_data['params'], event_data['time'],
            event_number
        )
        self.params_panel.current_event_definition = event_def
        self.current_event_for_params = event_data['name']
        display_name = CanvasTimelinePanel.format_event_display_name(event_data['name'])
        self.status_label.config(text=f"Selected #{event_number}: {display_name}")

    def on_canvas_event_move(self, idx: int, new_time_ms: int):
        """Called after a drag-move is committed."""
        self.current_editing_index = idx
        # Sync params-panel time display if this event is loaded there
        event_data = self.timeline_panel.get_event(idx)
        if event_data and self.params_panel.current_event_name == event_data['name']:
            try:
                self.params_panel.time_var.set(event_data['time'])
            except Exception:
                pass
        self.status_label.config(text=f"Event moved to {self._fmt_time(new_time_ms)}")

    def on_canvas_event_resize(self, idx: int, new_dur_ms: int):
        """Called after a drag-resize is committed."""
        if self.current_editing_index == idx:
            if 'duration_ms' in self.params_panel.param_vars:
                try:
                    self.params_panel.param_vars['duration_ms'].set(new_dur_ms)
                except Exception:
                    pass
        self.status_label.config(text=f"Duration changed to {new_dur_ms} ms")

    def _fmt_time(self, ms: int) -> str:
        total_s = ms / 1000
        m = int(total_s // 60)
        s = int(total_s % 60)
        return f"{m}:{s:02d}"

    # ------------------------------------------------------------------ #
    # Library / parameter panel event handlers                            #
    # ------------------------------------------------------------------ #

    def on_library_event_selected(self, event_name: str):
        """Handle event selection in the library panel."""
        self.current_event_for_params = event_name
        event_def = self.event_definitions[event_name]
        self.params_panel.load_event_parameters(event_name, event_def)
        self.params_panel.current_event_definition = event_def

    def on_add_event_to_timeline(self, default_time_ms: Optional[int] = None):
        """Add the currently selected library event via time-input dialog.

        Pre-fills the dialog with the playhead position so the user can
        confirm or adjust the time before adding.
        """
        selected_event = self.library_panel.get_selected_event()
        if not selected_event:
            messagebox.showwarning("No Event Selected",
                                   "Please select an event from the library first.",
                                   parent=self)
            return

        initial = (default_time_ms if default_time_ms is not None
                   else int(self.timeline_panel._playhead_ms))
        time_dialog = TimeInputDialog(self, "Add Event", initial_value=initial)
        if time_dialog.result is None:
            return
        event_def = self.event_definitions[selected_event]
        params    = event_def.get('default_params', {}).copy()
        self.timeline_panel.add_event(time_dialog.result, selected_event, params)
        self.status_label.config(
            text=f"Added {selected_event} at {self._fmt_time(time_dialog.result)}")

    def on_add_event_to_timeline_direct(self, time_ms: Optional[int] = None):
        """Add the currently selected library event without a dialog.

        Uses *time_ms* when provided (right-click position), otherwise the
        current playhead position.  Intended for the timeline toolbar button
        and right-click menu so the user can place events quickly.
        """
        selected_event = self.library_panel.get_selected_event()
        if not selected_event:
            messagebox.showwarning("No Event Selected",
                                   "Please select an event from the library first.",
                                   parent=self)
            return

        t = time_ms if time_ms is not None else int(self.timeline_panel._playhead_ms)
        event_def = self.event_definitions[selected_event]
        params    = event_def.get('default_params', {}).copy()
        self.timeline_panel.add_event(t, selected_event, params)
        self.status_label.config(
            text=f"Added {selected_event} at {self._fmt_time(t)}")

    def on_edit_timeline_event(self):
        """Load the selected timeline event into the parameters panel."""
        idx = self.timeline_panel.selected_index
        if idx is None:
            messagebox.showwarning("No Event Selected",
                                   "Please select an event from the timeline first.",
                                   parent=self)
            return
        self.on_canvas_event_select(idx)

    def on_change_timeline_event_time(self):
        """Change the time of the selected timeline event via a dialog."""
        idx = self.timeline_panel.selected_index
        if idx is None:
            messagebox.showwarning("No Event Selected",
                                   "Please select an event from the timeline first.",
                                   parent=self)
            return

        event_data = self.timeline_panel.get_event(idx)
        if event_data:
            time_dialog = TimeInputDialog(self, "Change Event Time",
                                         initial_value=event_data['time'])
            if time_dialog.result is not None:
                new_index = self.timeline_panel.update_event(
                    idx, time_dialog.result, event_data['name'], event_data['params']
                )
                self.timeline_panel.selected_index = new_index
                if self.current_editing_index == idx:
                    self.current_editing_index = new_index
                    self.params_panel.editing_label.config(text=f"Editing event #{new_index + 1}")
                    try:
                        self.params_panel.time_var.set(time_dialog.result)
                    except Exception:
                        pass
                self.status_label.config(
                    text=f"Event time updated to {self._fmt_time(time_dialog.result)}")

    def on_apply_parameters(self):
        """Apply current parameters from the params panel to the editing event."""
        if self.current_editing_index is None:
            messagebox.showinfo("No Event Being Edited",
                                "Please select an event from the timeline first.",
                                parent=self)
            return

        event_data = self.timeline_panel.get_event(self.current_editing_index)
        if event_data:
            new_params = self.params_panel.get_parameter_values()
            new_time   = self.params_panel.get_event_time()

            new_index = self.timeline_panel.update_event(
                self.current_editing_index, new_time, event_data['name'], new_params
            )

            self.current_editing_index            = new_index
            self.timeline_panel.selected_index    = new_index
            self.params_panel.editing_label.config(text=f"Editing event #{new_index + 1}")

            display_name = CanvasTimelinePanel.format_event_display_name(event_data['name'])
            self.status_label.config(
                text=f"Event #{new_index + 1} updated — {display_name} at {self._fmt_time(new_time)}")

    def on_duplicate_timeline_event(self):
        """Duplicate the selected timeline event."""
        idx = self.timeline_panel.selected_index
        if idx is None:
            messagebox.showwarning("No Event Selected",
                                   "Please select an event from the timeline first.",
                                   parent=self)
            return

        event_data = self.timeline_panel.get_event(idx)
        if event_data:
            time_dialog = TimeInputDialog(self, "Duplicate Event",
                                          initial_value=event_data['time'] + 5000)
            if time_dialog.result is not None:
                self.timeline_panel.add_event(
                    time_dialog.result, event_data['name'], event_data['params'])

    # ------------------------------------------------------------------ #
    # File operations                                                       #
    # ------------------------------------------------------------------ #

    def on_new_file(self):
        self.timeline_panel.events.clear()
        self.timeline_panel.selected_index = None
        self.timeline_panel.refresh_display()
        self.event_file_path = None
        self.event_file_var.set("")
        self.set_dirty(False)
        self.current_editing_index = None
        self.params_panel.show_placeholder()
        self.params_panel.editing_label.config(text="")
        self.params_panel.title_label.config(text="Parameters")
        self.status_label.config(text="New timeline created")

    def on_load_file(self):
        file_path = filedialog.askopenfilename(
            title="Load Event File",
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")],
            parent=self
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            events = data.get('events') or []
            self.timeline_panel.load_events_from_yaml(events)
            self.event_file_path = Path(file_path)
            self.event_file_var.set(str(self.event_file_path))
            self.set_dirty(False)
            self.current_editing_index = None
            self.params_panel.show_placeholder()
            self.status_label.config(text=f"Loaded {len(events)} events from file")
            self._try_load_matching_funscript(self.event_file_path)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load event file: {e}", parent=self)

    def _try_load_matching_funscript(self, events_path: Path):
        """Given an events file path, find and load the sibling .funscript file."""
        try:
            # e.g. "name.events.yml" → "name.funscript"
            fs_name = events_path.name
            for suffix in ('.events.yml', '.events.yaml', '.yml', '.yaml'):
                if fs_name.endswith(suffix):
                    fs_name = fs_name[: -len(suffix)] + '.funscript'
                    break
            funscript_path = events_path.parent / fs_name
            if funscript_path.exists():
                with open(funscript_path, 'r', encoding='utf-8') as f:
                    fs_data = json.load(f)
                actions = fs_data.get('actions', [])
                if actions:
                    self.timeline_panel.set_funscript(actions)
        except Exception:
            pass  # waveform track stays empty if no matching funscript

    def on_save_event_defaults(self):
        """Save current parameter values as the new defaults for the event type."""
        if self.current_editing_index is not None:
            ev = self.timeline_panel.get_event(self.current_editing_index)
            event_name = ev['name'] if ev else None
        elif self.current_event_for_params:
            event_name = self.current_event_for_params
        else:
            return

        if not event_name or event_name not in self.event_definitions:
            return

        new_params = self.params_panel.get_parameter_values()

        # Update in-memory definition
        self.event_definitions[event_name]['default_params'].update(new_params)

        # Write back to the definitions YAML file
        try:
            with open(EVENT_DEFINITIONS_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            config_data['definitions'][event_name]['default_params'].update(new_params)
            with open(EVENT_DEFINITIONS_PATH, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            self.status_label.config(text=f"Saved default params for '{event_name}'")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save defaults: {e}", parent=self)
            return

        # Offer to update matching timeline events
        matching = [i for i, ev in enumerate(self.timeline_panel.events)
                    if ev['name'] == event_name]
        if matching:
            if messagebox.askyesno(
                "Update Timeline Events",
                f"Update {len(matching)} existing '{event_name}' event(s) on the "
                f"timeline to use these new defaults?",
                parent=self
            ):
                for i in matching:
                    self.timeline_panel.events[i]['params'].update(new_params)
                self.timeline_panel.refresh_display()
                self.set_dirty(True)

    def on_change_event_type(self, idx: int):
        """Show a dialog to change the type of a timeline event."""
        ev = self.timeline_panel.get_event(idx)
        if ev is None:
            return

        dlg = tk.Toplevel(self)
        dlg.title("Change Event Type")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)

        ttk.Label(dlg, text="Select new event type:").pack(padx=12, pady=(12, 4))

        event_names = sorted(self.event_definitions.keys())
        var = tk.StringVar(value=ev['name'])
        cb = ttk.Combobox(dlg, textvariable=var, values=event_names, state='readonly', width=38)
        cb.pack(padx=12, pady=4)

        keep_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dlg, text="Keep compatible parameters", variable=keep_var).pack(padx=12, pady=4)

        result = {}

        def confirm():
            result['name'] = var.get()
            result['keep'] = keep_var.get()
            dlg.destroy()

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=(4, 12))
        ttk.Button(btn_frame, text="OK",     command=confirm).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=4)
        self.wait_window(dlg)

        if not result:
            return

        new_name = result['name']
        new_def = self.event_definitions[new_name]
        new_params = dict(new_def['default_params'])

        if result['keep']:
            for k, v in ev['params'].items():
                if k in new_params:
                    new_params[k] = v

        new_idx = self.timeline_panel.update_event(idx, ev['time'], new_name, new_params)
        self.current_editing_index = new_idx
        self.params_panel.load_event_parameters(
            new_name, new_def, current_params=new_params,
            event_time_ms=ev['time'], event_number=new_idx
        )

    def on_save_file(self):
        if not self.timeline_panel.events:
            messagebox.showwarning("No Events",
                                   "Timeline is empty. Add events before saving.",
                                   parent=self)
            return

        conflicts = self.timeline_panel._find_conflicts()
        if conflicts:
            names = ", ".join(
                self.timeline_panel.events[i]['name'] for i in sorted(conflicts)
            )
            proceed = messagebox.askyesno(
                "Overlapping Events",
                f"{len(conflicts)} events overlap in time and may produce unexpected "
                f"output:\n\n{names}\n\nSave anyway?",
                icon='warning',
                parent=self
            )
            if not proceed:
                return

        if self.event_file_path:
            file_path = self.event_file_path
        else:
            file_path = filedialog.asksaveasfilename(
                title="Save Event File",
                defaultextension=".events.yml",
                filetypes=[("YAML files", "*.yml"), ("All files", "*.*")],
                parent=self
            )

        if not file_path:
            return

        try:
            data = self.timeline_panel.get_yaml_data()
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            self.event_file_path = Path(file_path)
            self.event_file_var.set(str(self.event_file_path))
            self.set_dirty(False)
            self.status_label.config(
                text=f"Saved {len(self.timeline_panel.events)} events")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save event file: {e}", parent=self)

    def on_view_yaml(self):
        if not self.timeline_panel.events:
            messagebox.showinfo("No Events", "Timeline is empty.", parent=self)
            return

        yaml_data = self.timeline_panel.get_yaml_data()
        yaml_text = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)

        dialog = tk.Toplevel(self)
        dialog.title("Generated YAML")
        dialog.geometry("600x400")

        text_widget = tk.Text(dialog, wrap='none')
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(text_widget, orient='vertical', command=text_widget.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar_y.set)

        text_widget.insert('1.0', yaml_text)
        text_widget.config(state='disabled')

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=5)

    # ------------------------------------------------------------------ #
    # Apply effects / restore backup                                       #
    # ------------------------------------------------------------------ #

    def on_apply_effects(self):
        if not self.timeline_panel.events:
            messagebox.showwarning("No Events",
                                   "Timeline is empty. Add events before applying.",
                                   parent=self)
            return

        conflicts = self.timeline_panel._find_conflicts()
        if conflicts:
            names = ", ".join(
                self.timeline_panel.events[i]['name'] for i in sorted(conflicts)
            )
            proceed = messagebox.askyesno(
                "Overlapping Events",
                f"{len(conflicts)} events overlap in time and may produce unexpected "
                f"output:\n\n{names}\n\nApply anyway?",
                icon='warning',
                parent=self
            )
            if not proceed:
                return

        if not self.event_file_path or self.is_dirty:
            if not self.event_file_path:
                result = messagebox.askyesno(
                    "Save Required",
                    "Event file must be saved before applying. Save now?",
                    parent=self)
                if not result:
                    return
            self.on_save_file()
            if not self.event_file_path:
                return

        self.status_label.config(text="Processing… Please wait.")
        processing_thread = threading.Thread(target=self.apply_effects_worker, daemon=True)
        processing_thread.start()

    def apply_effects_worker(self):
        try:
            success_message, _, backup_path = process_events(
                str(self.event_file_path),
                self.backup_var.get(),
                EVENT_DEFINITIONS_PATH,
                self.headroom_var.get(),
                self.config
            )
            self.after(0, self.on_processing_success, success_message, backup_path)
        except EventProcessorError as e:
            self.after(0, self.on_processing_error, str(e))
        except Exception as e:
            tb = traceback.format_exc()
            self.after(0, self.on_processing_error, f"Unexpected error: {e}\n\nDetails:\n{tb}")

    def on_processing_success(self, message: str, backup_path):
        self.backup_path = backup_path
        messagebox.showinfo("Success", message, parent=self)
        if backup_path:
            self.restore_button.config(state='normal',
                                       text=f"Restore Backup ({backup_path.name})")
            self.status_label.config(text="Processing complete. Backup available.")
        else:
            self.status_label.config(text="Processing complete.")

    def on_processing_error(self, error_message: str):
        messagebox.showerror("Processing Error", error_message, parent=self)
        self.status_label.config(text="Processing failed.")

    def on_restore_backup(self):
        if not self.backup_path or not self.backup_path.exists():
            messagebox.showerror("Error", "Backup file not found.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"This will restore all files from:\n{self.backup_path.name}\n\nContinue?",
            parent=self)
        if not confirm:
            return

        try:
            target_dir = self.backup_path.parent
            with zipfile.ZipFile(self.backup_path, 'r') as zipf:
                file_list = zipf.namelist()
                zipf.extractall(target_dir)
            messagebox.showinfo("Restore Complete",
                                f"Successfully restored {len(file_list)} files.",
                                parent=self)
            self.restore_button.config(state='disabled')
            self.status_label.config(text="Backup restored successfully.")
            if self.event_file_path:
                self.on_load_file()
        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore: {e}", parent=self)


class TimeInputDialog(tk.Toplevel):
    """Dialog for entering event time."""

    def __init__(self, parent, title="Enter Time", initial_value=0):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None

        frame = ttk.Frame(self, padding=10)
        frame.pack()

        ttk.Label(frame, text="Time (MM:SS or milliseconds):").grid(
            row=0, column=0, columnspan=2, pady=(0, 5))

        self.time_var = tk.StringVar()
        if initial_value > 0:
            minutes = initial_value // 60000
            seconds = (initial_value % 60000) // 1000
            self.time_var.set(f"{minutes}:{seconds:02d}")
        else:
            self.time_var.set("0:00")

        entry = ttk.Entry(frame, textvariable=self.time_var, width=20)
        entry.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        entry.bind('<Return>', lambda e: self.on_ok())

        self.update_idletasks()
        entry.focus_force()
        entry.select_range(0, tk.END)

        ttk.Button(frame, text="OK",     command=self.on_ok).grid(row=2, column=0, padx=5)
        ttk.Button(frame, text="Cancel", command=self.destroy).grid(row=2, column=1, padx=5)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.wait_window()

    def on_ok(self):
        time_str = self.time_var.get().strip()
        try:
            if ':' in time_str:
                parts   = time_str.split(':')
                minutes = int(parts[0])
                seconds = int(parts[1])
                self.result = (minutes * 60 + seconds) * 1000
            else:
                self.result = int(time_str)
            if self.result < 0:
                raise ValueError("Time cannot be negative")
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Time",
                                 "Please enter time as MM:SS or milliseconds.",
                                 parent=self)


if __name__ == '__main__':
    # Test the dialog
    root = tk.Tk()
    root.title("Main App")
    root.geometry("300x100")

    def open_dialog():
        dialog = CustomEventsBuilderDialog(root)
        root.wait_window(dialog)

    ttk.Button(root, text="Open Custom Events Builder", command=open_dialog).pack(padx=20, pady=20)
    root.mainloop()
