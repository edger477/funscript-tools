"""
Curve Editor Dialog for Motion Axis Generation.

Provides an interactive modal dialog for editing response curves with preset selection,
custom control point manipulation, and real-time preview.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Dict, Any, Optional
import copy

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.patches as patches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import from processing modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from processing.linear_mapping import apply_linear_response_curve, validate_control_points
from processing.motion_axis_generation import get_curve_presets, create_custom_curve
from processing.linear_mapping import get_default_response_curves
from processing.curve_library import (
    load_library, save_curve as lib_save_curve,
    delete_curve as lib_delete_curve, rename_curve as lib_rename_curve,
)

# Names of built-in presets that cannot be overwritten in the library.
_BUILTIN_PRESET_NAMES = set()


def _init_builtin_names():
    """Cache the set of built-in preset display names."""
    global _BUILTIN_PRESET_NAMES
    if not _BUILTIN_PRESET_NAMES:
        for data in get_curve_presets().values():
            _BUILTIN_PRESET_NAMES.add(data['name'])
        # Also include the default axis curve names
        for data in get_default_response_curves().values():
            _BUILTIN_PRESET_NAMES.add(data['name'])


class CurveEditorDialog:
    """
    Modal dialog for editing motion axis response curves.

    Features:
    - Preset curve selection
    - Interactive control point editing
    - Real-time curve preview
    - Validation and error handling
    """

    def __init__(self, parent, axis_name: str, current_curve: Dict[str, Any]):
        """
        Initialize the curve editor dialog.

        Args:
            parent: Parent tkinter window
            axis_name: Name of the axis being edited (e1, e2, e3, e4)
            current_curve: Current curve configuration
        """
        self.parent = parent
        self.axis_name = axis_name.upper()
        self.original_curve = copy.deepcopy(current_curve)
        self.current_curve = copy.deepcopy(current_curve)
        self.result = None  # Will store the final curve configuration

        # Control point editing state
        self.selected_point_index = None
        self.dragging = False

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit {self.axis_name} Curve")
        self.dialog.geometry("800x650")
        self.dialog.minsize(700, 550)  # Set minimum size to prevent shrinking
        self.dialog.resizable(True, True)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Setup UI first
        self.setup_ui()

        # Load presets
        self.load_presets()

        # Initialize curve display and points list
        self.update_curve_display()
        self.update_points_list()

        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Center dialog after UI is setup
        self.dialog.after(10, self._center_dialog)

        # Focus on dialog
        self.dialog.focus_set()

    def _center_dialog(self):
        """Center the dialog on the parent window."""
        # Wait for dialog to be fully created
        self.dialog.update_idletasks()

        # Get parent window geometry
        try:
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
        except tk.TclError:
            # Fallback to screen center if parent info unavailable
            parent_x = self.dialog.winfo_screenwidth() // 4
            parent_y = self.dialog.winfo_screenheight() // 4
            parent_width = self.dialog.winfo_screenwidth() // 2
            parent_height = self.dialog.winfo_screenheight() // 2

        # Use fixed dialog size instead of calculated size
        dialog_width = 800
        dialog_height = 650

        # Calculate position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Ensure dialog is on screen
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))

        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def setup_ui(self):
        """Setup the dialog user interface with resizable paned panels."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky='nsew')

        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Horizontal PanedWindow for the three resizable panels
        self._paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self._paned.grid(row=0, column=0, sticky='nsew')

        # Create wrapper frames for each pane (PanedWindow needs children
        # added via .add(), not .grid())
        self._presets_pane = ttk.Frame(self._paned)
        self._editor_pane = ttk.Frame(self._paned)
        self._points_pane = ttk.Frame(self._paned)

        self._paned.add(self._presets_pane, weight=0)
        self._paned.add(self._editor_pane, weight=1)
        self._paned.add(self._points_pane, weight=0)

        # Make each pane's content fill it
        for pane in (self._presets_pane, self._editor_pane, self._points_pane):
            pane.columnconfigure(0, weight=1)
            pane.rowconfigure(0, weight=1)

        # Build panels inside their panes
        self.setup_presets_panel(self._presets_pane)
        self.setup_editor_panel(self._editor_pane)
        self.setup_control_points_panel(self._points_pane)

        # Bottom panel - Action buttons (below the paned window)
        self.setup_action_buttons(main_frame)

    def setup_presets_panel(self, parent):
        """Setup the curve presets panel with built-in presets + user library."""
        presets_frame = ttk.LabelFrame(parent, text="Curve Presets", padding="5")
        presets_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        presets_frame.columnconfigure(0, weight=1)
        presets_frame.rowconfigure(0, weight=1)

        # Presets listbox — shows built-in presets, then a separator,
        # then user-saved curves from the library.
        self.presets_listbox = tk.Listbox(presets_frame, width=22, height=14)
        self.presets_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        scrollbar = ttk.Scrollbar(presets_frame, orient=tk.VERTICAL, command=self.presets_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.presets_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = ttk.Frame(presets_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="Load",
                   command=self.load_selected_preset).grid(row=0, column=0, sticky='ew', padx=(0, 2), pady=2)
        ttk.Button(btn_frame, text="Save to Library",
                   command=self._save_to_library).grid(row=0, column=1, sticky='ew', padx=(2, 0), pady=2)
        ttk.Button(btn_frame, text="Delete from Library",
                   command=self._delete_from_library).grid(row=1, column=0, sticky='ew', padx=(0, 2), pady=2)
        ttk.Button(btn_frame, text="Rename",
                   command=self._rename_in_library).grid(row=1, column=1, sticky='ew', padx=(2, 0), pady=2)

        # Bind listbox selection
        self.presets_listbox.bind('<<ListboxSelect>>', self.on_preset_select)
        self.presets_listbox.bind('<Double-Button-1>', lambda e: self.load_selected_preset())

    def setup_editor_panel(self, parent):
        """Setup the interactive curve editor panel."""
        editor_frame = ttk.LabelFrame(parent, text=f"{self.axis_name} Curve Editor", padding="5")
        editor_frame.grid(row=0, column=0, sticky='nsew', padx=2)
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        if not MATPLOTLIB_AVAILABLE:
            # Fallback if matplotlib not available
            fallback_label = ttk.Label(editor_frame, text="Matplotlib not available for curve editing")
            fallback_label.grid(row=0, column=0, pady=20)
            return

        # Create matplotlib figure
        self.fig = Figure(figsize=(6, 4.5), dpi=80)
        self.ax = self.fig.add_subplot(111)

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, editor_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Bind mouse events for interaction
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('button_release_event', self.on_canvas_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_motion)

        # Instructions
        instructions = ttk.Label(editor_frame,
                               text="• Click to add control points\n• Drag points to move\n• Right-click to delete points",
                               font=('TkDefaultFont', 8))
        instructions.grid(row=1, column=0, pady=5)

    def setup_control_points_panel(self, parent):
        """Setup the control points list panel."""
        points_frame = ttk.LabelFrame(parent, text="Control Points", padding="5")
        points_frame.grid(row=0, column=0, sticky='nsew', padx=(2, 0))
        points_frame.columnconfigure(0, weight=1)
        points_frame.rowconfigure(0, weight=1)

        # Control points tree
        columns = ('X', 'Y')
        self.points_tree = ttk.Treeview(points_frame, columns=columns, show='headings', height=12)
        self.points_tree.heading('X', text='Input (X)')
        self.points_tree.heading('Y', text='Output (Y)')
        self.points_tree.column('X', width=80)
        self.points_tree.column('Y', width=80)
        self.points_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # Scrollbar for tree
        tree_scrollbar = ttk.Scrollbar(points_frame, orient=tk.VERTICAL, command=self.points_tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.points_tree.config(yscrollcommand=tree_scrollbar.set)

        # Manual entry frame
        entry_frame = ttk.Frame(points_frame)
        entry_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        entry_frame.columnconfigure(1, weight=1)
        entry_frame.columnconfigure(3, weight=1)

        ttk.Label(entry_frame, text="X:").grid(row=0, column=0, padx=(0, 2))
        self.x_entry = ttk.Entry(entry_frame, width=8)
        self.x_entry.grid(row=0, column=1, padx=(0, 5))

        ttk.Label(entry_frame, text="Y:").grid(row=0, column=2, padx=(0, 2))
        self.y_entry = ttk.Entry(entry_frame, width=8)
        self.y_entry.grid(row=0, column=3)

        # Bind Enter in entry fields to add/update
        self.x_entry.bind('<Return>', lambda e: self._add_or_update_point())
        self.y_entry.bind('<Return>', lambda e: self._add_or_update_point())

        # Point manipulation buttons
        button_frame = ttk.Frame(points_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        ttk.Button(button_frame, text="Add Point",
                   command=self.add_manual_point).grid(row=0, column=0, sticky='ew', padx=1)
        ttk.Button(button_frame, text="Update Point",
                   command=self._update_selected_point).grid(row=0, column=1, sticky='ew', padx=1)
        ttk.Button(button_frame, text="Remove Point",
                   command=self.remove_selected_point).grid(row=0, column=2, sticky='ew', padx=1)

        # Bulk entry button
        ttk.Button(button_frame, text="Bulk Entry\u2026",
                   command=self._open_bulk_entry).grid(
            row=1, column=0, columnspan=3, sticky='ew', padx=1, pady=(4, 0))

        # Bind tree selection
        self.points_tree.bind('<<TreeviewSelect>>', self.on_point_select)

    def setup_action_buttons(self, parent):
        """Setup the action buttons panel."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=1, column=0, pady=10)

        # Restore Default — resets to the code-defined default for this axis
        restore_btn = ttk.Button(buttons_frame, text="Restore Default",
                                 command=self._restore_default)
        restore_btn.grid(row=0, column=0, padx=(0, 10))

        # Reset button — reverts to the curve as it was when the editor opened
        reset_btn = ttk.Button(buttons_frame, text="Reset", command=self.reset_curve)
        reset_btn.grid(row=0, column=1, padx=(0, 10))

        # Cancel button
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.grid(row=0, column=2, padx=(0, 10))

        # Save button
        save_btn = ttk.Button(buttons_frame, text="Save Curve", command=self.on_save)
        save_btn.grid(row=0, column=3)

        # Bind keyboard shortcuts
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        self.dialog.bind('<Return>', lambda e: self.on_save())

    # Separator label used in the listbox between built-in and user curves
    _SEPARATOR = '\u2500\u2500\u2500 Saved Curves \u2500\u2500\u2500'

    def load_presets(self):
        """Load built-in presets + user library into the listbox."""
        self.presets = get_curve_presets()
        self._user_curves = load_library()

        # Build ordered list: (key, data, is_user) — None key = separator
        self._preset_entries = []
        for key, data in self.presets.items():
            self._preset_entries.append((key, data, False))

        if self._user_curves:
            self._preset_entries.append((None, None, None))  # separator
            for name in sorted(self._user_curves.keys()):
                self._preset_entries.append(
                    (name, self._user_curves[name], True))

        self.presets_listbox.delete(0, tk.END)
        for key, data, is_user in self._preset_entries:
            if key is None:
                self.presets_listbox.insert(tk.END, self._SEPARATOR)
            elif is_user:
                self.presets_listbox.insert(
                    tk.END, f"\u2605 {data.get('name', key)}")
            else:
                self.presets_listbox.insert(tk.END, data['name'])

    def on_preset_select(self, event):
        """Handle preset selection in listbox."""
        pass

    def _get_selected_entry(self):
        """Return (key, data, is_user) for the selected item, or None."""
        selection = self.presets_listbox.curselection()
        if not selection:
            return None
        idx = selection[0]
        if idx >= len(self._preset_entries):
            return None
        key, data, is_user = self._preset_entries[idx]
        if key is None:  # separator
            return None
        return key, data, is_user

    def load_selected_preset(self):
        """Load the selected preset or library curve."""
        entry = self._get_selected_entry()
        if entry is None:
            return

        preset_key, preset_data, is_user = entry

        # Update current curve
        self.current_curve = {
            'name': preset_data.get('name', preset_key),
            'description': preset_data.get('description', ''),
            'control_points': copy.deepcopy(
                preset_data.get('control_points', [(0.0, 0.0), (1.0, 1.0)]))
        }

        # Update displays
        self.update_curve_display()
        self.update_points_list()

    def _save_to_library(self):
        """Save the current curve to the user library."""
        _init_builtin_names()
        from tkinter import simpledialog
        current_name = self.current_curve.get('name', 'Custom')
        # If the current name is a built-in, suggest "My <name>" instead
        if current_name in _BUILTIN_PRESET_NAMES:
            current_name = f"My {current_name}"
        name = simpledialog.askstring(
            "Save to Library",
            "Curve name:",
            initialvalue=current_name,
            parent=self.dialog)
        if not name or not name.strip():
            return
        name = name.strip()

        # Block built-in names
        if name in _BUILTIN_PRESET_NAMES:
            messagebox.showerror(
                "Reserved Name",
                f"'{name}' is a built-in preset name and cannot be used.\n"
                f"Try a different name, e.g. 'My {name}'.",
                parent=self.dialog)
            return

        # Check for overwrite of existing user curve
        existing = load_library()
        if name in existing:
            if not messagebox.askyesno(
                    "Overwrite",
                    f"A saved curve named '{name}' already exists. Overwrite?",
                    parent=self.dialog):
                return

        # Save with the typed name as the curve's display name
        curve_to_save = copy.deepcopy(self.current_curve)
        curve_to_save['name'] = name
        lib_save_curve(name, curve_to_save)
        self.load_presets()  # refresh listbox
        messagebox.showinfo("Saved", f"Curve '{name}' saved to library.",
                            parent=self.dialog)

    def _delete_from_library(self):
        """Delete the selected user curve from the library."""
        entry = self._get_selected_entry()
        if entry is None:
            messagebox.showinfo("Delete", "Select a saved curve first.",
                                parent=self.dialog)
            return
        key, data, is_user = entry
        if not is_user:
            messagebox.showinfo(
                "Delete",
                "Built-in presets cannot be deleted. Only saved curves "
                "(marked with \u2605) can be removed.",
                parent=self.dialog)
            return
        if not messagebox.askyesno(
                "Delete Curve",
                f"Delete '{data.get('name', key)}' from the library?",
                parent=self.dialog):
            return
        lib_delete_curve(key)
        self.load_presets()

    def _rename_in_library(self):
        """Rename a user curve in the library."""
        _init_builtin_names()
        from tkinter import simpledialog
        entry = self._get_selected_entry()
        if entry is None:
            messagebox.showinfo("Rename", "Select a saved curve first.",
                                parent=self.dialog)
            return
        key, data, is_user = entry
        if not is_user:
            messagebox.showinfo(
                "Rename",
                "Built-in presets cannot be renamed.",
                parent=self.dialog)
            return
        new_name = simpledialog.askstring(
            "Rename Curve",
            "New name:",
            initialvalue=key,
            parent=self.dialog)
        if not new_name or not new_name.strip() or new_name.strip() == key:
            return
        new_name = new_name.strip()
        if new_name in _BUILTIN_PRESET_NAMES:
            messagebox.showerror(
                "Reserved Name",
                f"'{new_name}' is a built-in preset name and cannot be used.",
                parent=self.dialog)
            return
        if not lib_rename_curve(key, new_name):
            messagebox.showerror(
                "Rename Failed",
                f"A curve named '{new_name}' already exists.",
                parent=self.dialog)
            return
        self.load_presets()

    def update_curve_display(self):
        """Update the matplotlib curve display."""
        if not MATPLOTLIB_AVAILABLE:
            return

        # Auto-rename if the user modified a built-in preset's points
        self._auto_rename_if_modified()

        # Clear the axes
        self.ax.clear()

        # Set up the plot
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.set_xlabel('Input Position')
        self.ax.set_ylabel('Output Position')
        self.ax.set_title(f"{self.current_curve['name']}")
        self.ax.grid(True, alpha=0.3)

        # Generate curve data
        control_points = self.current_curve['control_points']
        if len(control_points) >= 2:
            x_vals = np.linspace(0, 1, 101)
            y_vals = []

            for x in x_vals:
                y = apply_linear_response_curve(x, control_points)
                y_vals.append(y)

            # Plot the curve
            self.ax.plot(x_vals, y_vals, 'b-', linewidth=2, label='Response Curve')

        # Plot control points
        if control_points:
            x_points = [p[0] for p in control_points]
            y_points = [p[1] for p in control_points]

            # Plot all control points
            self.ax.scatter(x_points, y_points, c='red', s=50, zorder=5, label='Control Points')

            # Highlight selected point
            if self.selected_point_index is not None and self.selected_point_index < len(control_points):
                x_sel = control_points[self.selected_point_index][0]
                y_sel = control_points[self.selected_point_index][1]
                self.ax.scatter([x_sel], [y_sel], c='orange', s=80, zorder=6, marker='o', linewidth=2, edgecolor='black')

        # Add legend
        self.ax.legend(loc='upper left', fontsize=8)

        # Refresh canvas
        self.canvas.draw()

    def update_points_list(self):
        """Update the control points list in the treeview."""
        # Clear existing items
        for item in self.points_tree.get_children():
            self.points_tree.delete(item)

        # Add current control points
        control_points = self.current_curve['control_points']
        for i, (x, y) in enumerate(control_points):
            self.points_tree.insert('', 'end', values=(f'{x:.3f}', f'{y:.3f}'))

    def on_canvas_click(self, event):
        """Handle mouse clicks on the matplotlib canvas."""
        if not MATPLOTLIB_AVAILABLE or event.inaxes != self.ax:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Clamp coordinates to valid range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        if event.button == 1:  # Left click
            # Check if clicking near an existing point
            tolerance = 0.05
            control_points = self.current_curve['control_points']

            for i, (px, py) in enumerate(control_points):
                if abs(px - x) < tolerance and abs(py - y) < tolerance:
                    # Start dragging existing point
                    self.selected_point_index = i
                    self.dragging = True
                    self.update_curve_display()
                    return

            # Add new control point
            self.add_control_point(x, y)

        elif event.button == 3:  # Right click
            # Remove nearest control point (if any)
            self.remove_nearest_point(x, y)

    def on_canvas_release(self, event):
        """Handle mouse button release on canvas."""
        self.dragging = False

    def on_canvas_motion(self, event):
        """Handle mouse motion on canvas."""
        if not MATPLOTLIB_AVAILABLE or not self.dragging or event.inaxes != self.ax:
            return

        if self.selected_point_index is None:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Clamp coordinates
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        # Update control point
        control_points = self.current_curve['control_points']
        if self.selected_point_index < len(control_points):
            control_points[self.selected_point_index] = (x, y)

            # Re-sort control points by x coordinate
            control_points.sort(key=lambda p: p[0])

            # Find new index of the moved point
            for i, (px, py) in enumerate(control_points):
                if abs(px - x) < 0.001 and abs(py - y) < 0.001:
                    self.selected_point_index = i
                    break

            # Update displays
            self.update_curve_display()
            self.update_points_list()

    def add_control_point(self, x: float, y: float):
        """Add a new control point."""
        control_points = self.current_curve['control_points']
        control_points.append((x, y))

        # Sort by x coordinate
        control_points.sort(key=lambda p: p[0])

        # Find index of new point
        for i, (px, py) in enumerate(control_points):
            if abs(px - x) < 0.001 and abs(py - y) < 0.001:
                self.selected_point_index = i
                break

        # Update displays
        self.update_curve_display()
        self.update_points_list()

    def remove_nearest_point(self, x: float, y: float):
        """Remove the control point nearest to the given coordinates."""
        control_points = self.current_curve['control_points']

        if len(control_points) <= 2:
            messagebox.showwarning("Cannot Remove", "A curve must have at least 2 control points.")
            return

        # Find nearest point
        min_distance = float('inf')
        nearest_index = None

        for i, (px, py) in enumerate(control_points):
            distance = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_index = i

        # Remove if close enough
        if nearest_index is not None and min_distance < 0.1:
            control_points.pop(nearest_index)
            self.selected_point_index = None

            # Update displays
            self.update_curve_display()
            self.update_points_list()

    def on_point_select(self, event):
        """Handle selection in the points treeview."""
        selection = self.points_tree.selection()
        if selection:
            # Get index of selected item
            item = selection[0]
            all_items = self.points_tree.get_children()
            self.selected_point_index = all_items.index(item)

            # Update curve display to highlight selected point
            self.update_curve_display()

            # Fill entry fields
            control_points = self.current_curve['control_points']
            if self.selected_point_index < len(control_points):
                x, y = control_points[self.selected_point_index]
                self.x_entry.delete(0, tk.END)
                self.x_entry.insert(0, f'{x:.3f}')
                self.y_entry.delete(0, tk.END)
                self.y_entry.insert(0, f'{y:.3f}')

    def add_manual_point(self):
        """Add a control point from manual entry."""
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())

            # Validate range
            if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
                messagebox.showerror("Invalid Values", "X and Y coordinates must be between 0.0 and 1.0")
                return

            self.add_control_point(x, y)

            # Clear entry fields
            self.x_entry.delete(0, tk.END)
            self.y_entry.delete(0, tk.END)

        except ValueError:
            messagebox.showerror("Invalid Values", "Please enter valid numeric values for X and Y coordinates")

    def remove_selected_point(self):
        """Remove the currently selected control point."""
        if self.selected_point_index is None:
            messagebox.showinfo("No Selection", "Please select a control point to remove.")
            return

        control_points = self.current_curve['control_points']

        if len(control_points) <= 2:
            messagebox.showwarning("Cannot Remove", "A curve must have at least 2 control points.")
            return

        if self.selected_point_index < len(control_points):
            control_points.pop(self.selected_point_index)
            self.selected_point_index = None

            # Update displays
            self.update_curve_display()
            self.update_points_list()

            # Clear entry fields
            self.x_entry.delete(0, tk.END)
            self.y_entry.delete(0, tk.END)

    def _update_selected_point(self):
        """Overwrite the selected point's coordinates with the entry values."""
        if self.selected_point_index is None:
            messagebox.showinfo("No Selection",
                                "Select a point in the list first, then edit X/Y and click Update.",
                                parent=self.dialog)
            return
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Values",
                                 "X and Y must be numbers.",
                                 parent=self.dialog)
            return
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            messagebox.showerror("Out of Range",
                                 "X and Y must be between 0.0 and 1.0.",
                                 parent=self.dialog)
            return

        cp = self.current_curve['control_points']
        if self.selected_point_index < len(cp):
            # Check for duplicate X (another point already has this X)
            for i, (px, _) in enumerate(cp):
                if i != self.selected_point_index and abs(px - x) < 0.001:
                    messagebox.showerror("Duplicate X",
                                         f"Another point already has X={px:.3f}.",
                                         parent=self.dialog)
                    return
            cp[self.selected_point_index] = (x, y)
            cp.sort(key=lambda p: p[0])
            # Re-find the point index after sorting
            for i, (px, py) in enumerate(cp):
                if abs(px - x) < 0.001 and abs(py - y) < 0.001:
                    self.selected_point_index = i
                    break
            self.update_curve_display()
            self.update_points_list()
            # Re-select the updated point in the tree
            children = self.points_tree.get_children()
            if self.selected_point_index < len(children):
                self.points_tree.selection_set(children[self.selected_point_index])
                self.points_tree.see(children[self.selected_point_index])

    def _add_or_update_point(self):
        """Smart Enter handler: update if a point is selected, add if not."""
        if self.selected_point_index is not None:
            self._update_selected_point()
        else:
            self.add_manual_point()

    def _open_bulk_entry(self):
        """Open a dialog for entering multiple X,Y coordinate pairs at once."""
        bulk = tk.Toplevel(self.dialog)
        bulk.title("Bulk Coordinate Entry")
        bulk.geometry("400x350")
        bulk.transient(self.dialog)
        bulk.grab_set()

        ttk.Label(bulk, text="Enter one X,Y pair per line (values 0.0-1.0):").pack(
            padx=10, pady=(10, 2), anchor='w')
        ttk.Label(bulk, text="Formats: \"0.5, 0.8\" or \"0.5  0.8\" or \"(0.5, 0.8)\"",
                  foreground='#666').pack(padx=10, pady=(0, 5), anchor='w')

        text_frame = ttk.Frame(bulk)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text = tk.Text(text_frame, wrap=tk.WORD, font=('Menlo', 11), width=35, height=12)
        text.grid(row=0, column=0, sticky='nsew')
        sb = ttk.Scrollbar(text_frame, command=text.yview)
        sb.grid(row=0, column=1, sticky='ns')
        text.config(yscrollcommand=sb.set)

        # Pre-fill with current points
        for x, y in self.current_curve['control_points']:
            text.insert(tk.END, f"{x:.3f}, {y:.3f}\n")

        # Mode: replace all vs append
        mode_var = tk.StringVar(value='replace')
        mode_frame = ttk.Frame(bulk)
        mode_frame.pack(padx=10, anchor='w')
        ttk.Radiobutton(mode_frame, text="Replace all points",
                        variable=mode_var, value='replace').pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Append to existing",
                        variable=mode_var, value='append').pack(side=tk.LEFT, padx=(10, 0))

        def _apply():
            raw = text.get('1.0', tk.END).strip()
            if not raw:
                messagebox.showerror("Empty", "No coordinates entered.",
                                     parent=bulk)
                return

            parsed = []
            for line_num, line in enumerate(raw.split('\n'), start=1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Strip parens/brackets
                line = line.replace('(', '').replace(')', '')
                line = line.replace('[', '').replace(']', '')
                # Split by comma, semicolon, or whitespace
                import re
                parts = re.split(r'[,;\s]+', line)
                parts = [p for p in parts if p]
                if len(parts) != 2:
                    messagebox.showerror(
                        "Parse Error",
                        f"Line {line_num}: expected 2 values, got {len(parts)}.\n"
                        f"Line: \"{line}\"",
                        parent=bulk)
                    return
                try:
                    x, y = float(parts[0]), float(parts[1])
                except ValueError:
                    messagebox.showerror(
                        "Parse Error",
                        f"Line {line_num}: not valid numbers.\nLine: \"{line}\"",
                        parent=bulk)
                    return
                if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
                    messagebox.showerror(
                        "Out of Range",
                        f"Line {line_num}: values must be 0.0-1.0.\n"
                        f"Got X={x}, Y={y}",
                        parent=bulk)
                    return
                parsed.append((x, y))

            if len(parsed) < 2 and mode_var.get() == 'replace':
                messagebox.showerror("Too Few Points",
                                     "Need at least 2 points to define a curve.",
                                     parent=bulk)
                return

            if mode_var.get() == 'replace':
                self.current_curve['control_points'] = parsed
            else:
                self.current_curve['control_points'].extend(parsed)

            # Remove duplicates by X (keep last), sort
            seen = {}
            for x, y in self.current_curve['control_points']:
                seen[round(x, 6)] = (x, y)
            self.current_curve['control_points'] = sorted(
                seen.values(), key=lambda p: p[0])

            self.selected_point_index = None
            self.update_curve_display()
            self.update_points_list()
            bulk.destroy()

        btn_frame = ttk.Frame(bulk)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Apply", command=_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel",
                   command=bulk.destroy).pack(side=tk.LEFT, padx=5)

    def _restore_default(self):
        """Restore this axis to its code-defined default curve."""
        defaults = get_default_response_curves()
        axis_key = self.axis_name.lower()  # 'E1' -> 'e1'
        if axis_key not in defaults:
            messagebox.showinfo(
                "No Default",
                f"No built-in default found for axis {self.axis_name}.",
                parent=self.dialog)
            return

        default_curve = defaults[axis_key]
        if not messagebox.askyesno(
                "Restore Default",
                f"Restore {self.axis_name} to the built-in default "
                f"'{default_curve['name']}'?\n\n"
                f"This will replace the current curve.",
                parent=self.dialog):
            return

        self.current_curve = {
            'name': default_curve['name'],
            'description': default_curve['description'],
            'control_points': copy.deepcopy(default_curve['control_points']),
        }
        self.selected_point_index = None
        self.update_curve_display()
        self.update_points_list()
        self.x_entry.delete(0, tk.END)
        self.y_entry.delete(0, tk.END)

    def reset_curve(self):
        """Reset curve to the state it was when the editor opened."""
        if messagebox.askyesno("Reset Curve", "Reset curve to the state when the editor opened?\n"
                               "This will lose all changes made in this session."):
            self.current_curve = copy.deepcopy(self.original_curve)
            self.selected_point_index = None

            # Update displays
            self.update_curve_display()
            self.update_points_list()

            # Clear entry fields
            self.x_entry.delete(0, tk.END)
            self.y_entry.delete(0, tk.END)

    def _is_builtin_modified(self):
        """Check if the current curve uses a built-in name but has different points."""
        _init_builtin_names()
        name = self.current_curve.get('name', '')
        if name not in _BUILTIN_PRESET_NAMES:
            return False
        # Find the built-in curve with this name
        for data in get_curve_presets().values():
            if data['name'] == name:
                builtin_cp = sorted(
                    [(round(x, 6), round(y, 6)) for x, y in data['control_points']])
                current_cp = sorted(
                    [(round(float(x), 6), round(float(y), 6))
                     for x, y in self.current_curve['control_points']])
                return builtin_cp != current_cp
        return False

    def _auto_rename_if_modified(self):
        """If the curve is a modified built-in, rename to 'Custom (<name>)'."""
        if self._is_builtin_modified():
            original_name = self.current_curve['name']
            self.current_curve['name'] = f"Custom ({original_name})"
            self.current_curve['description'] = (
                f"Modified from built-in '{original_name}'")

    def on_save(self):
        """Save the current curve configuration."""
        # Auto-rename modified built-in curves so the built-in name
        # doesn't get associated with wrong control points
        self._auto_rename_if_modified()

        # Validate the current curve
        control_points = self.current_curve['control_points']

        if not validate_control_points(control_points):
            messagebox.showerror("Invalid Curve",
                               "The current curve is invalid. Please ensure:\n"
                               "• At least 2 control points\n"
                               "• All coordinates between 0.0 and 1.0\n"
                               "• No duplicate X coordinates")
            return

        # Ensure we have end points at 0 and 1
        has_start = any(abs(p[0] - 0.0) < 0.001 for p in control_points)
        has_end = any(abs(p[0] - 1.0) < 0.001 for p in control_points)

        if not has_start or not has_end:
            if messagebox.askyesno("Missing End Points",
                                 "The curve should have control points at X=0.0 and X=1.0. "
                                 "Add them automatically?"):
                # Add missing endpoints
                if not has_start:
                    # Find Y value at start
                    y_start = apply_linear_response_curve(0.0, control_points)
                    control_points.append((0.0, y_start))

                if not has_end:
                    # Find Y value at end
                    y_end = apply_linear_response_curve(1.0, control_points)
                    control_points.append((1.0, y_end))

                # Re-sort
                control_points.sort(key=lambda p: p[0])
                self.current_curve['control_points'] = control_points

        # Set result and close
        self.result = copy.deepcopy(self.current_curve)
        self.dialog.destroy()

    def on_cancel(self):
        """Cancel editing and close dialog."""
        if self.current_curve != self.original_curve:
            if not messagebox.askyesno("Discard Changes", "Discard all changes to the curve?"):
                return

        self.result = None
        self.dialog.destroy()

    def show(self) -> Optional[Dict[str, Any]]:
        """
        Show the dialog and return the result.

        Returns:
            Modified curve configuration, or None if cancelled
        """
        self.dialog.wait_window()
        return self.result


def edit_curve(parent, axis_name: str, current_curve: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convenience function to show the curve editor dialog.

    Args:
        parent: Parent tkinter window
        axis_name: Name of the axis being edited
        current_curve: Current curve configuration

    Returns:
        Modified curve configuration, or None if cancelled
    """
    dialog = CurveEditorDialog(parent, axis_name, current_curve)
    return dialog.show()