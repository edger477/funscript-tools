"""
Custom Events Builder Dialog - Visual Event Timeline Editor

This module provides a user-friendly visual interface for creating and editing
custom event timelines without requiring manual YAML editing.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import zipfile
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from processing.event_processor import process_events, EventProcessorError


# Path to the event definitions YAML file
EVENT_DEFINITIONS_PATH = Path(__file__).parent.parent / "config.event_definitions.yml"


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
        self.search_var.trace('w', self.on_search_changed)
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

        self.setup_ui()

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

        # Event steps preview section
        preview_frame = ttk.LabelFrame(self, text="Event Steps Preview", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.steps_text = tk.Text(preview_frame, height=20, wrap=tk.WORD,
                                  font=('Courier', 9), bg='#f5f5f5',
                                  relief=tk.FLAT, state=tk.DISABLED)
        steps_scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.steps_text.yview)
        self.steps_text.configure(yscrollcommand=steps_scrollbar.set)

        self.steps_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        steps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Apply Parameters", command=self.apply_parameters).pack(side=tk.LEFT, padx=2)

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
            self.time_display_label.config(text=format_time())

        self.time_var.trace('w', on_time_changed)

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
        var.trace('w', lambda *args: self.update_steps_preview())

    def create_widget_for_parameter(self, parent, param_name: str, value):
        """Create appropriate widget based on parameter name and value, returns (widget, var, unit)"""
        # Time parameters
        if param_name.endswith('_ms'):
            var = tk.IntVar(value=int(value))
            widget = ttk.Spinbox(parent, from_=0, to=60000, increment=100, textvariable=var, width=10)
            return widget, var, 'ms'

        # Frequency parameters
        if 'freq' in param_name.lower() or param_name == 'pulse_rate':
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
                    params[param_name] = int(value) if isinstance(value, (int, float)) else int(float(value))
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


class TimelinePanel(ttk.Frame):
    """Panel for displaying and managing the event timeline"""

    def __init__(self, parent, add_callback=None, edit_callback=None, duplicate_callback=None):
        super().__init__(parent)
        self.events = []  # List of timeline events: [{'time': ms, 'name': str, 'params': dict}, ...]
        self.selected_index = None

        # Callbacks to parent dialog
        self.add_callback = add_callback
        self.edit_callback = edit_callback
        self.duplicate_callback = duplicate_callback

        self.setup_ui()

    def setup_ui(self):
        """Create the UI components"""
        # Title
        title_label = ttk.Label(self, text="Timeline", font=('TkDefaultFont', 10, 'bold'))
        title_label.pack(pady=(0, 5))

        # Timeline list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.timeline_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                        selectmode=tk.SINGLE, font=('Courier', 9))
        self.timeline_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.timeline_list.yview)

        self.timeline_list.bind('<<ListboxSelect>>', self.on_selection_changed)
        self.timeline_list.bind('<Double-Button-1>', lambda e: self.on_edit_event())

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Add Event", command=self.on_add_event).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="Edit Event", command=self.on_edit_event).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="Change Time", command=self.on_change_time).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="Remove Event", command=self.on_remove_event).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="Duplicate", command=self.on_duplicate_event).pack(fill=tk.X, pady=1)

        # Auto-sort checkbox
        self.auto_sort_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(btn_frame, text="Auto-sort by time", variable=self.auto_sort_var).pack(pady=5)

    def add_event(self, time_ms: int, event_name: str, params: Dict[str, Any]):
        """Add an event to the timeline"""
        self.events.append({
            'time': time_ms,
            'name': event_name,
            'params': params.copy()
        })

        if self.auto_sort_var.get():
            self.events.sort(key=lambda e: e['time'])

        self.refresh_display()

    def update_event(self, index: int, time_ms: int, event_name: str, params: Dict[str, Any]) -> int:
        """Update an existing event, returns new index after potential re-sort"""
        if 0 <= index < len(self.events):
            # Store the event object to track it after sorting
            updated_event = {
                'time': time_ms,
                'name': event_name,
                'params': params.copy()
            }
            self.events[index] = updated_event

            if self.auto_sort_var.get():
                self.events.sort(key=lambda e: e['time'])
                # Find new index of the updated event
                try:
                    new_index = self.events.index(updated_event)
                    self.selected_index = new_index
                except ValueError:
                    new_index = index
            else:
                new_index = index

            self.refresh_display()

            # Re-select the item at the new index
            if 0 <= new_index < len(self.events):
                self.timeline_list.selection_clear(0, tk.END)
                self.timeline_list.selection_set(new_index)
                self.timeline_list.see(new_index)

            return new_index
        return index

    def remove_event(self, index: int):
        """Remove an event from the timeline"""
        if 0 <= index < len(self.events):
            self.events.pop(index)
            self.refresh_display()

    def get_event(self, index: int) -> Optional[Dict[str, Any]]:
        """Get event at index"""
        if 0 <= index < len(self.events):
            return self.events[index]
        return None

    def refresh_display(self):
        """Refresh the timeline display"""
        self.timeline_list.delete(0, tk.END)

        for idx, event in enumerate(self.events, start=1):
            time_str = self.format_time(event['time'])
            display_name = self.format_event_display_name(event['name'])
            line = f"#{idx}  {time_str}  {display_name}"
            self.timeline_list.insert(tk.END, line)

    @staticmethod
    def format_event_display_name(event_name: str) -> str:
        """Format event name with category prefix for display"""
        if event_name.startswith('mcb_'):
            name = event_name.replace('mcb_', '').replace('_', ' ').title()
            return f"MCB - {name}"
        elif event_name.startswith('clutch_'):
            name = event_name.replace('clutch_', '').replace('_', ' ').title()
            return f"Clutch - {name}"
        else:
            name = event_name.replace('_', ' ').title()
            return f"General - {name}"

    def format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS"""
        total_seconds = ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes:2d}:{seconds:02d}"

    def on_selection_changed(self, event):
        """Handle selection change in timeline"""
        selection = self.timeline_list.curselection()
        if selection:
            self.selected_index = selection[0]
        else:
            self.selected_index = None

    def on_add_event(self):
        """Add event - calls parent callback"""
        if self.add_callback:
            self.add_callback()

    def on_edit_event(self):
        """Edit event - calls parent callback"""
        if self.edit_callback:
            self.edit_callback()

    def on_change_time(self):
        """Placeholder for change time (handled by parent dialog)"""
        pass

    def on_remove_event(self):
        """Remove selected event"""
        if self.selected_index is not None:
            self.remove_event(self.selected_index)
            self.selected_index = None

    def on_duplicate_event(self):
        """Duplicate event - calls parent callback"""
        if self.duplicate_callback:
            self.duplicate_callback()

    def load_events_from_yaml(self, events_list: List[Dict[str, Any]]):
        """Load events from parsed YAML data"""
        self.events = events_list.copy()
        if self.auto_sort_var.get():
            self.events.sort(key=lambda e: e['time'])
        self.refresh_display()

    def get_yaml_data(self) -> Dict[str, Any]:
        """Generate YAML-compatible data structure"""
        return {
            'events': self.events
        }


class CustomEventsBuilderDialog(tk.Toplevel):
    """
    Main dialog for visual custom events timeline building
    """

    def __init__(self, parent, config=None):
        super().__init__(parent)
        self.title("Custom Event Builder")
        self.geometry("1200x950")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # Store config
        self.config = config if config is not None else {}

        # State
        self.event_file_path = None
        self.event_definitions = {}
        self.event_groups = []
        self.normalization_config = {}
        self.backup_path = None
        self.current_event_for_params = None
        self.current_editing_index = None  # Track which timeline event is being edited

        # Load event definitions
        try:
            with open(EVENT_DEFINITIONS_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            self.event_definitions = config_data.get('definitions', {})
            self.event_groups = config_data.get('groups', [])
            self.normalization_config = config_data.get('normalization', {})

            # Fallback to default groups if not defined in YAML
            if not self.event_groups:
                self.event_groups = [
                    {'name': 'General', 'prefix': '', 'description': 'General-purpose events'},
                    {'name': 'MCB', 'prefix': 'mcb_', 'description': 'MCB audio events'},
                    {'name': 'Clutch', 'prefix': 'clutch_', 'description': 'Clutch conditioning events'}
                ]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load event definitions: {e}", parent=self)
            self.destroy()
            return

        # Variables
        self.event_file_var = tk.StringVar()
        self.backup_var = tk.BooleanVar(value=True)
        self.headroom_var = tk.IntVar(value=10)
        self.apply_to_linked_var = tk.BooleanVar(value=True)

        self.setup_ui()

    def setup_ui(self):
        """Create the main UI layout"""
        # Top bar - File operations
        self.create_file_bar()

        # Main content - 3 panel layout
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Event Library
        library_frame = ttk.LabelFrame(main_paned, text="Event Library", padding=5)
        self.library_panel = EventLibraryPanel(library_frame, self.event_definitions,
                                               self.event_groups, self.on_library_event_selected)
        self.library_panel.pack(fill=tk.BOTH, expand=True)
        main_paned.add(library_frame, weight=1)

        # Connect add to timeline button
        self.library_panel.add_to_timeline_btn.config(command=self.on_add_event_to_timeline)

        # Center panel - Parameters
        params_frame = ttk.LabelFrame(main_paned, text="Parameters", padding=5)
        self.params_panel = ParameterPanel(params_frame, apply_callback=self.on_apply_parameters)
        self.params_panel.pack(fill=tk.BOTH, expand=True)
        main_paned.add(params_frame, weight=1)

        # Right panel - Timeline
        timeline_frame = ttk.LabelFrame(main_paned, text="Timeline", padding=5)
        self.timeline_panel = TimelinePanel(
            timeline_frame,
            add_callback=self.on_add_event_to_timeline,
            edit_callback=self.on_edit_timeline_event,
            duplicate_callback=self.on_duplicate_timeline_event
        )
        self.timeline_panel.pack(fill=tk.BOTH, expand=True)
        main_paned.add(timeline_frame, weight=1)

        # Connect change time button
        self.timeline_panel.on_change_time = self.on_change_timeline_event_time

        # Bottom bar - Options and actions
        self.create_options_bar()
        self.create_action_bar()

    def create_file_bar(self):
        """Create file operations bar"""
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, expand=False, padx=5, pady=(5, 0))

        ttk.Label(file_frame, text="Event File:").pack(side=tk.LEFT, padx=(0, 5))

        file_entry = ttk.Entry(file_frame, textvariable=self.event_file_var, state='readonly')
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(file_frame, text="New", command=self.on_new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Load", command=self.on_load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Save", command=self.on_save_file).pack(side=tk.LEFT, padx=2)

    def create_options_bar(self):
        """Create options bar"""
        options_frame = ttk.LabelFrame(self, text="Options", padding=5)
        options_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        ttk.Checkbutton(options_frame, text="Backup files",
                       variable=self.backup_var).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(options_frame, text="Apply to linked axes",
                       variable=self.apply_to_linked_var).pack(side=tk.LEFT, padx=5)

        ttk.Label(options_frame, text="Headroom:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Spinbox(options_frame, from_=0, to=20, textvariable=self.headroom_var,
                   width=5).pack(side=tk.LEFT, padx=2)

    def create_action_bar(self):
        """Create action buttons bar"""
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, expand=False, padx=5, pady=(0, 5))

        ttk.Button(action_frame, text="View YAML", command=self.on_view_yaml).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Apply Effects", command=self.on_apply_effects).pack(side=tk.LEFT, padx=2)

        self.restore_button = ttk.Button(action_frame, text="Restore Backup",
                                        command=self.on_restore_backup, state='disabled')
        self.restore_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=2)

        self.status_label = ttk.Label(action_frame, text="Ready. Select or load an event file.")
        self.status_label.pack(side=tk.RIGHT, padx=10)

    # Event Handlers
    def on_library_event_selected(self, event_name: str):
        """Handle event selection in library"""
        self.current_event_for_params = event_name
        event_def = self.event_definitions[event_name]
        self.params_panel.load_event_parameters(event_name, event_def)
        self.params_panel.current_event_definition = event_def

    def on_add_event_to_timeline(self):
        """Add selected event from library to timeline"""
        selected_event = self.library_panel.get_selected_event()
        if not selected_event:
            messagebox.showwarning("No Event Selected",
                                  "Please select an event from the library first.",
                                  parent=self)
            return

        # Prompt for time
        time_dialog = TimeInputDialog(self, "Add Event")
        if time_dialog.result is not None:
            event_def = self.event_definitions[selected_event]
            params = event_def.get('default_params', {}).copy()

            self.timeline_panel.add_event(time_dialog.result, selected_event, params)
            self.status_label.config(text=f"Added {selected_event} at {time_dialog.result}ms")

    def on_edit_timeline_event(self):
        """Edit selected timeline event - loads parameters into params panel"""
        if self.timeline_panel.selected_index is None:
            messagebox.showwarning("No Event Selected",
                                  "Please select an event from the timeline first.",
                                  parent=self)
            return

        # Track which event is being edited
        self.current_editing_index = self.timeline_panel.selected_index

        event_data = self.timeline_panel.get_event(self.timeline_panel.selected_index)
        if event_data:
            # Load parameters in params panel for editing
            event_def = self.event_definitions[event_data['name']]
            event_number = self.timeline_panel.selected_index + 1  # 1-based numbering for display
            self.params_panel.load_event_parameters(
                event_data['name'],
                event_def,
                event_data['params'],
                event_data['time'],
                event_number
            )
            self.params_panel.current_event_definition = event_def
            self.current_event_for_params = event_data['name']
            display_name = self.timeline_panel.format_event_display_name(event_data['name'])
            self.status_label.config(text=f"Editing #{event_number} - {display_name}")

    def on_change_timeline_event_time(self):
        """Change the time of selected timeline event"""
        if self.timeline_panel.selected_index is None:
            messagebox.showwarning("No Event Selected",
                                  "Please select an event from the timeline first.",
                                  parent=self)
            return

        event_data = self.timeline_panel.get_event(self.timeline_panel.selected_index)
        if event_data:
            time_dialog = TimeInputDialog(self, "Change Event Time", initial_value=event_data['time'])
            if time_dialog.result is not None:
                new_index = self.timeline_panel.update_event(
                    self.timeline_panel.selected_index,
                    time_dialog.result,
                    event_data['name'],
                    event_data['params']
                )
                self.timeline_panel.selected_index = new_index
                self.status_label.config(text=f"Event time updated to {self.timeline_panel.format_time(time_dialog.result)}")

    def on_apply_parameters(self):
        """Apply current parameters and time to currently editing event"""
        if self.current_editing_index is None:
            messagebox.showinfo("No Event Being Edited",
                               "Please select an event from the timeline and click 'Edit Event' first.",
                               parent=self)
            return

        event_data = self.timeline_panel.get_event(self.current_editing_index)
        if event_data:
            new_params = self.params_panel.get_parameter_values()
            new_time = self.params_panel.get_event_time()

            # Update the event
            new_index = self.timeline_panel.update_event(
                self.current_editing_index,
                new_time,
                event_data['name'],
                new_params
            )

            # Update tracking to the new index (event may have moved due to time change)
            self.current_editing_index = new_index
            self.timeline_panel.selected_index = new_index

            # Update the event number display in case it changed
            new_event_number = new_index + 1
            self.params_panel.editing_label.config(text=f"Editing event #{new_event_number}")

            display_name = self.timeline_panel.format_event_display_name(event_data['name'])
            self.status_label.config(text=f"Event #{new_event_number} updated - {display_name} at {self.timeline_panel.format_time(new_time)}")

    def on_duplicate_timeline_event(self):
        """Duplicate selected timeline event"""
        if self.timeline_panel.selected_index is None:
            messagebox.showwarning("No Event Selected",
                                  "Please select an event from the timeline first.",
                                  parent=self)
            return

        event_data = self.timeline_panel.get_event(self.timeline_panel.selected_index)
        if event_data:
            time_dialog = TimeInputDialog(self, "Duplicate Event", initial_value=event_data['time'] + 5000)
            if time_dialog.result is not None:
                self.timeline_panel.add_event(time_dialog.result, event_data['name'], event_data['params'])

    # File Operations
    def on_new_file(self):
        """Create new event timeline"""
        self.timeline_panel.events.clear()
        self.timeline_panel.refresh_display()
        self.event_file_path = None
        self.event_file_var.set("")
        self.status_label.config(text="New timeline created")

    def on_load_file(self):
        """Load existing event file"""
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

            events = data.get('events', [])
            self.timeline_panel.load_events_from_yaml(events)
            self.event_file_path = Path(file_path)
            self.event_file_var.set(str(self.event_file_path))
            self.status_label.config(text=f"Loaded {len(events)} events from file")

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load event file: {e}", parent=self)

    def on_save_file(self):
        """Save event timeline to file"""
        if not self.timeline_panel.events:
            messagebox.showwarning("No Events", "Timeline is empty. Add events before saving.", parent=self)
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
            self.status_label.config(text=f"Saved {len(self.timeline_panel.events)} events")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save event file: {e}", parent=self)

    def on_view_yaml(self):
        """Show generated YAML in a dialog"""
        if not self.timeline_panel.events:
            messagebox.showinfo("No Events", "Timeline is empty.", parent=self)
            return

        yaml_data = self.timeline_panel.get_yaml_data()
        yaml_text = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)

        # Create dialog
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

    def on_apply_effects(self):
        """Apply events using the processing backend"""
        if not self.timeline_panel.events:
            messagebox.showwarning("No Events", "Timeline is empty. Add events before applying.", parent=self)
            return

        if not self.event_file_path:
            # Save first
            result = messagebox.askyesno("Save Required",
                                        "Event file must be saved before applying. Save now?",
                                        parent=self)
            if result:
                self.on_save_file()
                if not self.event_file_path:
                    return
            else:
                return

        # Start processing in background thread
        self.status_label.config(text="Processing... Please wait.")
        processing_thread = threading.Thread(target=self.apply_effects_worker, daemon=True)
        processing_thread.start()

    def apply_effects_worker(self):
        """Worker thread for applying effects"""
        try:
            success_message, _, backup_path = process_events(
                str(self.event_file_path),
                self.backup_var.get(),
                EVENT_DEFINITIONS_PATH,
                self.headroom_var.get(),
                self.apply_to_linked_var.get(),
                self.config
            )

            self.after(0, self.on_processing_success, success_message, backup_path)

        except EventProcessorError as e:
            self.after(0, self.on_processing_error, str(e))
        except Exception as e:
            self.after(0, self.on_processing_error, f"Unexpected error: {e}")

    def on_processing_success(self, message: str, backup_path):
        """Handle successful processing"""
        self.backup_path = backup_path
        messagebox.showinfo("Success", message, parent=self)

        if backup_path:
            self.restore_button.config(state='normal', text=f"Restore Backup ({backup_path.name})")
            self.status_label.config(text="Processing complete. Backup available.")
        else:
            self.status_label.config(text="Processing complete.")

    def on_processing_error(self, error_message: str):
        """Handle processing error"""
        messagebox.showerror("Processing Error", error_message, parent=self)
        self.status_label.config(text="Processing failed.")

    def on_restore_backup(self):
        """Restore from backup"""
        if not self.backup_path or not self.backup_path.exists():
            messagebox.showerror("Error", "Backup file not found.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"This will restore all files from:\n{self.backup_path.name}\n\nContinue?",
            parent=self
        )

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

            # Reload the event file
            if self.event_file_path:
                self.on_load_file()

        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore: {e}", parent=self)


class TimeInputDialog(tk.Toplevel):
    """Dialog for entering event time"""

    def __init__(self, parent, title="Enter Time", initial_value=0):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None

        # Create UI
        frame = ttk.Frame(self, padding=10)
        frame.pack()

        ttk.Label(frame, text="Time (MM:SS or milliseconds):").grid(row=0, column=0, columnspan=2, pady=(0, 5))

        self.time_var = tk.StringVar()
        if initial_value > 0:
            # Convert to MM:SS
            minutes = initial_value // 60000
            seconds = (initial_value % 60000) // 1000
            self.time_var.set(f"{minutes}:{seconds:02d}")
        else:
            self.time_var.set("0:00")

        entry = ttk.Entry(frame, textvariable=self.time_var, width=20)
        entry.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        entry.focus()
        entry.bind('<Return>', lambda e: self.on_ok())

        ttk.Button(frame, text="OK", command=self.on_ok).grid(row=2, column=0, padx=5)
        ttk.Button(frame, text="Cancel", command=self.destroy).grid(row=2, column=1, padx=5)

        # Center dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.wait_window()

    def on_ok(self):
        """Parse time and close"""
        time_str = self.time_var.get().strip()

        try:
            # Try parsing as MM:SS
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = int(parts[1])
                self.result = (minutes * 60 + seconds) * 1000
            else:
                # Parse as raw milliseconds
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
