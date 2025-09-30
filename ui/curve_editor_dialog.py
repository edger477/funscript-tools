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
        """Setup the dialog user interface."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Left panel - Presets
        self.setup_presets_panel(main_frame)

        # Center panel - Interactive editor
        self.setup_editor_panel(main_frame)

        # Right panel - Control points list
        self.setup_control_points_panel(main_frame)

        # Bottom panel - Action buttons
        self.setup_action_buttons(main_frame)

    def setup_presets_panel(self, parent):
        """Setup the curve presets panel."""
        presets_frame = ttk.LabelFrame(parent, text="Curve Presets", padding="5")
        presets_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        presets_frame.columnconfigure(0, weight=1)
        presets_frame.rowconfigure(0, weight=1)

        # Presets listbox
        self.presets_listbox = tk.Listbox(presets_frame, width=20, height=12)
        self.presets_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(presets_frame, orient=tk.VERTICAL, command=self.presets_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.presets_listbox.config(yscrollcommand=scrollbar.set)

        # Load preset button
        load_preset_btn = ttk.Button(presets_frame, text="Load Preset", command=self.load_selected_preset)
        load_preset_btn.grid(row=1, column=0, columnspan=2, pady=5)

        # Bind listbox selection
        self.presets_listbox.bind('<<ListboxSelect>>', self.on_preset_select)
        self.presets_listbox.bind('<Double-Button-1>', lambda e: self.load_selected_preset())

    def setup_editor_panel(self, parent):
        """Setup the interactive curve editor panel."""
        editor_frame = ttk.LabelFrame(parent, text=f"{self.axis_name} Curve Editor", padding="5")
        editor_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        points_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
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

        # Add/Remove buttons
        button_frame = ttk.Frame(points_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=5)

        add_btn = ttk.Button(button_frame, text="Add Point", command=self.add_manual_point)
        add_btn.grid(row=0, column=0, padx=(0, 5))

        remove_btn = ttk.Button(button_frame, text="Remove Point", command=self.remove_selected_point)
        remove_btn.grid(row=0, column=1)

        # Bind tree selection
        self.points_tree.bind('<<TreeviewSelect>>', self.on_point_select)

    def setup_action_buttons(self, parent):
        """Setup the action buttons panel."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=1, column=0, columnspan=3, pady=10)

        # Reset button
        reset_btn = ttk.Button(buttons_frame, text="Reset", command=self.reset_curve)
        reset_btn.grid(row=0, column=0, padx=(0, 10))

        # Cancel button
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.grid(row=0, column=1, padx=(0, 10))

        # Save button
        save_btn = ttk.Button(buttons_frame, text="Save Curve", command=self.on_save)
        save_btn.grid(row=0, column=2)

        # Bind keyboard shortcuts
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        self.dialog.bind('<Return>', lambda e: self.on_save())

    def load_presets(self):
        """Load available curve presets into the listbox."""
        self.presets = get_curve_presets()

        self.presets_listbox.delete(0, tk.END)
        for preset_name, preset_data in self.presets.items():
            display_name = preset_data['name']
            self.presets_listbox.insert(tk.END, display_name)

    def on_preset_select(self, event):
        """Handle preset selection in listbox."""
        # This is called when user clicks on a preset, but doesn't load it yet
        pass

    def load_selected_preset(self):
        """Load the selected preset curve."""
        selection = self.presets_listbox.curselection()
        if not selection:
            return

        # Get selected preset
        preset_names = list(self.presets.keys())
        if selection[0] >= len(preset_names):
            return

        preset_key = preset_names[selection[0]]
        preset_data = self.presets[preset_key]

        # Update current curve
        self.current_curve = {
            'name': preset_data['name'],
            'description': preset_data['description'],
            'control_points': preset_data['control_points'].copy()
        }

        # Update displays
        self.update_curve_display()
        self.update_points_list()

    def update_curve_display(self):
        """Update the matplotlib curve display."""
        if not MATPLOTLIB_AVAILABLE:
            return

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

    def reset_curve(self):
        """Reset curve to original state."""
        if messagebox.askyesno("Reset Curve", "Reset curve to original state? This will lose all changes."):
            self.current_curve = copy.deepcopy(self.original_curve)
            self.selected_point_index = None

            # Update displays
            self.update_curve_display()
            self.update_points_list()

            # Clear entry fields
            self.x_entry.delete(0, tk.END)
            self.y_entry.delete(0, tk.END)

    def on_save(self):
        """Save the current curve configuration."""
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