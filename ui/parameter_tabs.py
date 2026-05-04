import copy
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import Dict, Any


def calculate_combine_percentages(ratio):
    """Calculate the percentages for combine ratio."""
    left_pct = (ratio - 1) / ratio * 100
    right_pct = 1 / ratio * 100
    return left_pct, right_pct


def format_percentage_label(file1_name, file2_name, ratio):
    """Format a percentage label for combine ratios."""
    left_pct, right_pct = calculate_combine_percentages(ratio)
    return f"{file1_name} {left_pct:.1f}% | {file2_name} {right_pct:.1f}%"


class CombineRatioControl:
    """A control that shows both slider and text entry for combine ratios with percentage display."""

    def __init__(self, parent, label_text, file1_name, file2_name, initial_value, min_val=1, max_val=10, row=0):
        self.file1_name = file1_name
        self.file2_name = file2_name
        self.var = tk.DoubleVar(value=initial_value)

        # Label
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Slider - we'll handle rounding in the callback
        self.slider = ttk.Scale(parent, from_=min_val, to=max_val, variable=self.var,
                               orient=tk.HORIZONTAL, length=200, command=self._on_change)
        self.slider.grid(row=row, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Text entry with better formatting
        self.entry = ttk.Entry(parent, textvariable=self.var, width=8)
        self.entry.grid(row=row, column=2, padx=5, pady=5)
        self.entry.bind('<Return>', self._on_entry_change)
        self.entry.bind('<FocusOut>', self._on_entry_change)

        # Set initial value with proper formatting
        self.var.set(round(initial_value, 1))

        # Percentage display
        self.percentage_label = ttk.Label(parent, text="",
                                           style='Accent.TLabel')
        self.percentage_label.grid(row=row, column=3, sticky=tk.W, padx=5, pady=5)

        # Initial update
        self._update_percentage_display()

    def _on_change(self, value=None):
        """Called when slider moves."""
        # Ensure value is rounded to one decimal place
        try:
            current_value = float(self.var.get())
            rounded_value = round(current_value, 1)
            # Only update if significantly different to avoid infinite loops
            if abs(current_value - rounded_value) > 0.01:
                self.var.set(rounded_value)
            self._update_percentage_display()
        except (ValueError, tk.TclError):
            pass

    def _on_entry_change(self, event=None):
        """Called when text entry changes."""
        try:
            value = float(self.var.get())
            if value >= 1:  # Minimum ratio of 1
                # Round to one decimal place for consistency
                rounded_value = round(value, 1)
                if abs(value - rounded_value) > 0.01:
                    self.var.set(rounded_value)
                self._update_percentage_display()
        except (ValueError, tk.TclError):
            pass

    def _update_percentage_display(self):
        """Update the percentage display label."""
        try:
            ratio = float(self.var.get())
            if ratio >= 1:
                percentage_text = format_percentage_label(self.file1_name, self.file2_name, ratio)
                self.percentage_label.config(text=percentage_text)
        except ValueError:
            self.percentage_label.config(text="Invalid ratio")


class MultiRowNotebook(ttk.Frame):
    """Notebook-compatible widget whose tab buttons wrap to multiple rows.

    Drop-in replacement for ttk.Notebook for the .add(frame, text=...) API
    used in this app. Tabs are rendered as ttk.Radiobutton-in-Toolbutton
    style so they look and feel like real tabs with a visible selected
    state. `max_tabs_per_row` controls when the bar wraps (default 6).

    The content frames passed to .add() may be children of this widget
    (as in the original Notebook code — `ttk.Frame(self)`); we visually
    place them inside our internal content area via `grid(in_=content)`.
    """

    def __init__(self, parent, max_tabs_per_row: int = 6, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._max_per_row = int(max_tabs_per_row)
        self._tabs = []  # list of dicts: {'btn', 'frame', 'text'}
        self._current = None
        self._selected_var = tk.IntVar(value=-1)

        # Tab-bar strip across the top (auto-wraps to multiple rows).
        self._tab_bar = ttk.Frame(self)
        self._tab_bar.grid(row=0, column=0, sticky='ew', pady=(0, 2))

        # Content area (houses whichever tab-frame is currently selected).
        self._content = ttk.Frame(self, borderwidth=1, relief='sunken')
        self._content.grid(row=1, column=0, sticky='nsew')
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

    def add(self, frame, text: str = ""):
        idx = len(self._tabs)
        btn = ttk.Radiobutton(
            self._tab_bar, text=text, variable=self._selected_var,
            value=idx, command=lambda i=idx: self._select(i),
            style='Toolbutton')
        # Wrap: row = idx // N, col = idx % N.
        row = idx // self._max_per_row
        col = idx % self._max_per_row
        btn.grid(row=row, column=col, sticky='ew', padx=1, pady=1)
        # Make each column stretch so tab widths look even.
        self._tab_bar.columnconfigure(col, weight=1)

        # Place the frame inside the content area (even though its
        # logical parent is self — tkinter accepts cross-parent grid).
        frame.grid(row=0, column=0, sticky='nsew', in_=self._content)
        frame.grid_remove()

        self._tabs.append({'btn': btn, 'frame': frame, 'text': text})
        if self._current is None:
            self._select(0)

    def _select(self, idx: int):
        if not (0 <= idx < len(self._tabs)):
            return
        if self._current is not None and 0 <= self._current < len(self._tabs):
            self._tabs[self._current]['frame'].grid_remove()
        self._tabs[idx]['frame'].grid(row=0, column=0, sticky='nsew',
                                      in_=self._content)
        self._current = idx
        self._selected_var.set(idx)

    # ttk.Notebook-ish helpers (only what this codebase needs) -----
    def select(self, tab_id=None):
        """Mirror ttk.Notebook.select semantics lightly."""
        if tab_id is None:
            return self._current
        if isinstance(tab_id, int):
            self._select(tab_id)
        else:
            # Support passing a frame or a window-path string.
            for i, t in enumerate(self._tabs):
                if t['frame'] is tab_id or str(t['frame']) == str(tab_id):
                    self._select(i)
                    return
            # Fallback: search by text
            for i, t in enumerate(self._tabs):
                if t['text'] == tab_id:
                    self._select(i)
                    return

    def tabs(self):
        return [str(t['frame']) for t in self._tabs]


class ParameterTabs(MultiRowNotebook):
    def __init__(self, parent, config: Dict[str, Any]):
        # 6 tabs per row → 11 tabs fits cleanly into 2 rows (6 + 5).
        super().__init__(parent, max_tabs_per_row=6)

        self.config = config
        self.parameter_vars = {}
        self.combine_ratio_controls = {}  # Store custom ratio controls

        # Store reference to root window for dialogs
        self.root = parent
        while hasattr(self.root, 'master') and self.root.master:
            self.root = self.root.master

        # Canvases of scrollable tabs. Populated by _make_scrollable so
        # we can re-layout them on tab change.
        self._scrollable_canvases = []

        # Batch-update flag: when True, preview refresh handlers bail
        # out immediately. Used by update_display() to avoid running N
        # expensive matplotlib redraws while every tk var is being
        # swapped in from a new config snapshot (e.g. variant switch).
        self._loading_config = False

        self.setup_tabs()

        # Re-layout the active tab's canvas every time the user switches.
        # This kills the "contents invisible until you mouse over" bug
        # that appears when ttk fires a spurious 1x1 Configure before
        # the tab is actually mapped.
        self.bind('<<NotebookTabChanged>>',
                  lambda e: self._on_notebook_tab_changed())

    def _on_notebook_tab_changed(self):
        for entry in self._scrollable_canvases:
            # Tuple is (canvas, inner, inner_id) or
            # (canvas, inner, inner_id, rebind_fn).
            canvas, inner, inner_id = entry[0], entry[1], entry[2]
            rebind = entry[3] if len(entry) > 3 else None
            try:
                canvas.update_idletasks()
                w = canvas.winfo_width()
                if w > 1:
                    canvas.itemconfig(inner_id, width=w)
                inner.update_idletasks()
                bbox = canvas.bbox("all")
                if bbox is not None:
                    canvas.configure(scrollregion=bbox)
            except tk.TclError:
                pass
            # Re-bind mousewheel on any descendants that were added
            # after the initial passes (e.g. matplotlib previews that
            # build lazily).
            if rebind is not None:
                try:
                    rebind()
                except tk.TclError:
                    pass

    def set_mode_change_callback(self, callback):
        """Set callback function to be called when mode changes (kept for API compat)."""
        self.mode_change_callback = callback

    def set_conversion_callbacks(self, basic_callback, prostate_callback):
        """Set callback functions for the embedded conversion tabs."""
        if hasattr(self, 'embedded_conversion_tabs'):
            self.embedded_conversion_tabs.set_conversion_callbacks(basic_callback, prostate_callback)
    
    def _on_mode_change(self):
        """Internal method called when mode changes (kept for API compat)."""
        pass

    def _create_entry_tooltip(self, widget, text, wraplength=420):
        """Attach a hover tooltip. Delegates to ui.tooltip_helper."""
        from ui.tooltip_helper import create_tooltip
        create_tooltip(widget, text, wraplength)

    def _make_scrollable(self, outer):
        """Add a vertical scrollbar to outer frame and return the inner frame for widgets."""
        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            # Guard against the spurious 1x1 first Configure that ttk
            # sometimes emits before the real size is known — without
            # this, the inner window gets pinned at width=1 until the
            # user hovers and triggers another Configure.
            if event.width > 1:
                canvas.itemconfig(inner_id, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Force an initial layout pass after the widget is mapped. The
        # Tk Canvas doesn't sync inner-frame geometry until its first
        # <Configure> event fires, which on some platforms doesn't
        # happen until a mouse event triggers redraw — leaving the
        # tab's contents invisible until hovered. Two after() calls
        # (early + late) cover both fast-render and slow-layout paths.
        def _force_initial_sizing():
            try:
                canvas.update_idletasks()
                w = canvas.winfo_width()
                if w > 1:
                    canvas.itemconfig(inner_id, width=w)
                inner.update_idletasks()
                bbox = canvas.bbox("all")
                if bbox is not None:
                    canvas.configure(scrollregion=bbox)
            except tk.TclError:
                pass

        outer.after(50, _force_initial_sizing)
        outer.after(250, _force_initial_sizing)

        # Register so <<NotebookTabChanged>> can re-layout us.
        if not hasattr(self, '_scrollable_canvases'):
            self._scrollable_canvases = []
        self._scrollable_canvases.append((canvas, inner, inner_id))

        # Per-widget mousewheel binding — bind_all loses to widget- and
        # class-level bindings (notably matplotlib's FigureCanvasTkAgg,
        # which installs its own <MouseWheel> handler for plot zoom/pan
        # and effectively swallows our scroll). Walking the inner tree
        # and adding an explicit bind() on every descendant guarantees
        # the tab scrolls regardless of what's under the pointer.
        def _scroll_for(canvas_ref):
            def _handler(event):
                if getattr(event, 'num', None) == 4:
                    delta = -1
                elif getattr(event, 'num', None) == 5:
                    delta = 1
                else:
                    d = getattr(event, 'delta', 0)
                    if d == 0:
                        return
                    delta = -1 if d > 0 else 1
                try:
                    canvas_ref.yview_scroll(delta, "units")
                except tk.TclError:
                    pass
                return "break"
            return _handler

        def _walk_and_bind(widget, handler):
            try:
                for child in widget.winfo_children():
                    for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                        try:
                            child.bind(seq, handler, add='+')
                        except tk.TclError:
                            pass
                    _walk_and_bind(child, handler)
            except tk.TclError:
                pass

        def _bind_descendants():
            _walk_and_bind(inner, _scroll_for(canvas))

        # Two passes: early for widgets already placed, later for
        # matplotlib canvases that get built asynchronously.
        outer.after(100, _bind_descendants)
        outer.after(500, _bind_descendants)
        # Save for re-binding when new children appear after tab switch.
        self._scrollable_canvases[-1] = (canvas, inner, inner_id,
                                          _bind_descendants)

        def _on_mousewheel(event):
            """Scroll this canvas IF the pointer sits over any descendant
            of its inner frame — including nested entries/labels. This
            gives the same 'scroll anywhere in the page' behavior as a
            browser, without requiring the pointer to hover the scrollbar.
            """
            w = event.widget
            try:
                while w is not None:
                    if w is canvas or w is inner:
                        # Resolve scroll delta across platforms.
                        if getattr(event, 'num', None) == 4:
                            delta = -1
                        elif getattr(event, 'num', None) == 5:
                            delta = 1
                        else:
                            d = getattr(event, 'delta', 0)
                            if d == 0:
                                return
                            # Windows uses ±120; macOS often uses small
                            # deltas like ±1..±3. Normalize to a 1-unit
                            # step either way.
                            delta = -1 if d > 0 else 1
                        canvas.yview_scroll(delta, "units")
                        return
                    w = w.master
            except Exception:
                pass

        # Bind globally and permanently — the handler's widget-ancestor
        # check routes each event to the right canvas. add='+' lets
        # multiple scrollable canvases coexist; each one's handler only
        # scrolls when its own descendants are under the pointer.
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add='+')
        canvas.bind_all("<Button-4>", _on_mousewheel, add='+')  # Linux up
        canvas.bind_all("<Button-5>", _on_mousewheel, add='+')  # Linux down
        return inner

    def setup_tabs(self):
        """Setup all parameter tabs."""
        # General tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="General")
        self.general_frame = self._make_scrollable(_outer)
        self.setup_general_tab()

        # Speed tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Speed")
        self.speed_frame = self._make_scrollable(_outer)
        self.setup_speed_tab()

        # Frequency tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Frequency")
        self.frequency_frame = self._make_scrollable(_outer)
        self.setup_frequency_tab()

        # Volume tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Volume")
        self.volume_frame = self._make_scrollable(_outer)
        self.setup_volume_tab()

        # Pulse tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Pulse")
        self.pulse_frame = self._make_scrollable(_outer)
        self.setup_pulse_tab()

        # Initialize positional_axes parameter vars once (shared by both motion axis tabs)
        self.parameter_vars['positional_axes'] = {}

        # Motion Axis (3P) tab - Legacy alpha/beta mode
        _outer = ttk.Frame(self)
        self.add(_outer, text="Motion Axis (3P)")
        self.motion_axis_3p_frame = self._make_scrollable(_outer)
        self.setup_motion_axis_3p_tab()

        # Motion Axis (4P) tab - E1-E4 mode
        _outer = ttk.Frame(self)
        self.add(_outer, text="Motion Axis (4P)")
        self.motion_axis_4p_frame = self._make_scrollable(_outer)
        self.setup_motion_axis_4p_tab()

        # Advanced tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Advanced")
        self.advanced_frame = self._make_scrollable(_outer)
        self.setup_advanced_tab()

        # Trochoid Quantization tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Trochoid")
        self.trochoid_frame = self._make_scrollable(_outer)
        self.setup_trochoid_tab()

        # Trochoid Spatial tab — alternative E1-E4 driver via curve
        # parameterization + per-electrode directional projection.
        _outer = ttk.Frame(self)
        self.add(_outer, text="Trochoid Spatial")
        self.trochoid_spatial_frame = self._make_scrollable(_outer)
        self.setup_trochoid_spatial_tab()

        # Traveling Wave tab — linear/axial E1-E4 driver: time-driven
        # crest that runs along the shaft, modulated by the input signal.
        _outer = ttk.Frame(self)
        self.add(_outer, text="Traveling Wave")
        self.traveling_wave_frame = self._make_scrollable(_outer)
        self.setup_traveling_wave_tab()

        # Signal Generator tab
        _outer = ttk.Frame(self)
        self.add(_outer, text="Signal Gen")
        self.signal_gen_frame = self._make_scrollable(_outer)
        self.setup_signal_gen_tab()

    def setup_general_tab(self):
        """Setup the General parameters tab."""
        frame = self.general_frame
        self.parameter_vars['general'] = {}

        row = 0

        # Rest Level
        ttk.Label(frame, text="Rest Level:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['general']['rest_level'])
        self.parameter_vars['general']['rest_level'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Signal level when volume ramp or speed is 0").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Baseline signal level during quiet moments (no stroke / "
            "speed = 0). Higher values keep a subtle presence during "
            "pauses; 0 = silence. Typical: 0.3-0.5.")

        row += 1

        # Ramp Up Duration After Rest
        ttk.Label(frame, text="Ramp Up Duration After Rest:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['general']['ramp_up_duration_after_rest'])
        self.parameter_vars['general']['ramp_up_duration_after_rest'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-10.0) Seconds to ramp from rest level back to normal (0 = instant)").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "How long to fade from the rest level back up to the "
            "active signal after a quiet section ends. 0 = instant "
            "snap-back; 3-5 s = smooth ease-in. Prevents jarring "
            "re-entry of stimulation after pauses.")

        row += 1

        # Speed Window Size
        ttk.Label(frame, text="Speed Window (sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['general']['speed_window_size'])
        self.parameter_vars['general']['speed_window_size'] = var
        speed_win_entry = ttk.Entry(frame, textvariable=var, width=10)
        speed_win_entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.5-30) Rolling average window for speed. Smaller = reactive, larger = smoother").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(speed_win_entry,
            "How many seconds of movement history are averaged to compute speed.\n"
            "Smaller (0.5-1): tracks fast strokes, noisier signal.\n"
            "Larger (3-5): smooth, sluggish, averages out peaks.\n"
            "Also affects alpha/beta radius scaling.")

        row += 1

        # Acceleration Window Size
        ttk.Label(frame, text="Accel Window (sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['general']['accel_window_size'])
        self.parameter_vars['general']['accel_window_size'] = var
        accel_win_entry = ttk.Entry(frame, textvariable=var, width=10)
        accel_win_entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.5-10) Rolling average window for acceleration (speed-of-speed)").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(accel_win_entry,
            "Same concept as speed window but applied to the speed signal.\n"
            "Measures how fast the speed itself is changing.\n"
            "Smaller (1): reactive, catches sudden speed changes.\n"
            "Larger (4-6): smoother acceleration curve.")

        row += 2

        # Processing Options section
        ttk.Label(frame, text="Processing Options:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Initialize options parameter vars
        self.parameter_vars['options'] = {}

        # Create frame for processing options with 2 equal columns
        options_frame = ttk.Frame(frame)
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2)
        options_frame.columnconfigure(0, weight=1, uniform="opt")
        options_frame.columnconfigure(1, weight=1, uniform="opt")

        # Row 1: Normalize Volume | Delete Intermediary Files
        var = tk.BooleanVar(value=self.config['options']['normalize_volume'])
        self.parameter_vars['options']['normalize_volume'] = var
        ttk.Checkbutton(options_frame, text="Normalize Volume", variable=var).grid(row=0, column=0, sticky=tk.W, pady=2)

        var = tk.BooleanVar(value=self.config['options']['delete_intermediary_files'])
        self.parameter_vars['options']['delete_intermediary_files'] = var
        ttk.Checkbutton(options_frame, text="Delete Intermediary Files When Done", variable=var).grid(row=0, column=1, sticky=tk.W, pady=2)

        # Row 2: Overwrite Existing Files
        overwrite_value = self.config.get('options', {}).get('overwrite_existing_files', False)
        var = tk.BooleanVar(value=overwrite_value)
        self.parameter_vars['options']['overwrite_existing_files'] = var
        ttk.Checkbutton(options_frame, text="Overwrite existing output files", variable=var).grid(row=1, column=0, sticky=tk.W, pady=2)

        row += 1

        # File Management section
        ttk.Label(frame, text="File Management:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        # Initialize file_management parameter vars
        self.parameter_vars['file_management'] = {}

        # Mode selection
        ttk.Label(frame, text="Output Mode:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar(value=self.config['file_management']['mode'])
        self.parameter_vars['file_management']['mode'] = var

        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Radiobutton(mode_frame, text="Local", variable=var, value="local").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="Central Restim funscripts folder", variable=var, value="central").pack(side=tk.LEFT)

        row += 1

        # Mode description (dynamically updated based on selection)
        self.mode_desc_label = ttk.Label(frame, text="Local mode:", font=('TkDefaultFont', 9))
        self.mode_desc_label.grid(row=row, column=0, sticky=tk.W, padx=20, pady=2)

        self.mode_desc_text = ttk.Label(frame, text="All outputs are saved to same folder where the source funscript is found",
                  font=('TkDefaultFont', 9, 'italic'))
        self.mode_desc_text.grid(row=row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # Add trace to update description when mode changes
        var.trace_add('write', lambda *args: self._update_mode_description())

        row += 1

        # Central folder path
        ttk.Label(frame, text="Central folder:").grid(row=row, column=0, sticky=tk.W, padx=20, pady=5)

        central_frame = ttk.Frame(frame)
        central_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        central_path_var = tk.StringVar(value=self.config['file_management']['central_folder_path'])
        self.parameter_vars['file_management']['central_folder_path'] = central_path_var

        central_entry = ttk.Entry(central_frame, textvariable=central_path_var, width=40)
        central_entry.pack(side=tk.LEFT, padx=(0, 5))

        browse_button = ttk.Button(central_frame, text="Browse", command=self._browse_central_folder)
        browse_button.pack(side=tk.LEFT)

        row += 1

        # Create backups checkbox
        backup_var = tk.BooleanVar(value=self.config['file_management']['create_backups'])
        self.parameter_vars['file_management']['create_backups'] = backup_var
        ttk.Checkbutton(frame, text="Create backups (zip with timestamp) before overwriting files in central mode",
                       variable=backup_var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=20, pady=2)

        row += 1

        # Zip output checkbox (only meaningful in central mode)
        zip_var = tk.BooleanVar(value=self.config['file_management'].get('zip_output', False))
        self.parameter_vars['file_management']['zip_output'] = zip_var
        self.zip_output_checkbox = ttk.Checkbutton(
            frame,
            text="Zip output files (copy single .zip to central folder instead of individual files)",
            variable=zip_var
        )
        self.zip_output_checkbox.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=20, pady=2)
        if self.config['file_management']['mode'] != 'central':
            self.zip_output_checkbox.state(['disabled'])

    # Speed calculation method metadata for the UI dropdown.
    _SPEED_METHODS = [
        ("rolling_average", "Rolling Average",
         "Original method. Backward-looking rectangular window,\n"
         "averages per-sample absolute velocity. O(n\u00b2).\n"
         "Window param = how many seconds to look back."),
        ("ema", "Exponential Moving Average (EMA)",
         "Smooth single-pass filter. Recent samples weighted\n"
         "more than old ones (exponential decay). O(n), no lag.\n"
         "Window param = half-life in seconds."),
        ("savgol", "Savitzky-Golay Derivative",
         "Fits a local polynomial, takes analytical derivative.\n"
         "Preserves peaks better than averaging. Requires scipy.\n"
         "Window param = polynomial fit window in seconds."),
    ]

    def setup_speed_tab(self):
        """Setup the Speed parameters tab."""
        frame = self.speed_frame
        self.parameter_vars['speed'] = {}

        row = 0

        # Speed Processing section
        ttk.Label(frame, text="Speed Processing:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        row += 1

        # Calculation Method
        ttk.Label(frame, text="Calculation Method:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        method_value = self.config['speed'].get('method', 'rolling_average')
        var = tk.StringVar(value=method_value)
        self.parameter_vars['speed']['method'] = var
        method_display_map = {key: label for key, label, _ in self._SPEED_METHODS}
        method_reverse_map = {label: key for key, label, _ in self._SPEED_METHODS}
        display_var = tk.StringVar(value=method_display_map.get(method_value, 'Rolling Average'))
        method_combo = ttk.Combobox(
            frame, textvariable=display_var,
            values=[label for _, label, _ in self._SPEED_METHODS],
            state="readonly", width=32)
        method_combo.grid(row=row, column=1, padx=5, pady=5)
        self._speed_method_desc_var = tk.StringVar(value="")

        method_var = var  # capture reference before 'var' gets reused below

        def _update_method_ui():
            """Sync description, display label, and savgol panel visibility."""
            key = method_var.get()
            # Update description
            for k, _, desc in self._SPEED_METHODS:
                if k == key:
                    self._speed_method_desc_var.set(desc.split('\n')[0])
                    break
            # Sync combo display label
            lbl = method_display_map.get(key, 'Rolling Average')
            if display_var.get() != lbl:
                display_var.set(lbl)
            # Show/hide savgol options
            if hasattr(self, '_savgol_frame'):
                if key == 'savgol':
                    self._savgol_frame.grid(row=self._savgol_frame_row, column=0,
                                            columnspan=3, sticky=(tk.W, tk.E),
                                            padx=5, pady=(0, 5))
                else:
                    self._savgol_frame.grid_remove()

        def _on_method_combo_change(*_):
            key = method_reverse_map.get(display_var.get(), 'rolling_average')
            method_var.set(key)
            _update_method_ui()
        method_combo.bind('<<ComboboxSelected>>', _on_method_combo_change)

        # When var changes programmatically (e.g. update_display), sync UI
        def _on_method_var_change(*_):
            _update_method_ui()
        var.trace_add('write', _on_method_var_change)

        self._speed_method_display_var = display_var
        self._update_speed_method_ui = _update_method_ui

        desc_label = ttk.Label(frame, textvariable=self._speed_method_desc_var, foreground='#666')
        desc_label.grid(row=row, column=2, sticky=tk.W, padx=5)
        # Full tooltip on the combo
        for k, label, desc in self._SPEED_METHODS:
            if k == method_value:
                self._speed_method_desc_var.set(desc.split('\n')[0])
                break
        self._create_entry_tooltip(method_combo,
            "Rolling Average: original O(n\u00b2) backward-looking window.\n"
            "EMA: smooth O(n) exponential decay, no lag artifacts.\n"
            "Savitzky-Golay: polynomial-fit derivative, best peak preservation.\n\n"
            "All three use the Speed/Accel Window and Interpolation Interval settings.\n"
            "The window parameter means slightly different things per method\n"
            "(see General tab tooltips).")

        row += 1

        # Savitzky-Golay options (shown only when savgol is selected)
        savgol_cfg = self.config['speed'].get('savgol_options', {})
        self._savgol_frame = ttk.LabelFrame(frame, text="Savitzky-Golay Options", padding="5")
        self._savgol_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(0, 5))

        sg_poly_var = tk.IntVar(value=int(savgol_cfg.get('poly_order', 3)))
        sg_fit_var = tk.DoubleVar(value=float(savgol_cfg.get('fit_window_factor', 0.15)))
        sg_smooth_var = tk.DoubleVar(value=float(savgol_cfg.get('post_smooth_factor', 0.25)))

        # Store for config round-trip (nested under a special key)
        self.parameter_vars['speed']['savgol_options'] = {
            'poly_order': sg_poly_var,
            'fit_window_factor': sg_fit_var,
            'post_smooth_factor': sg_smooth_var,
        }

        ttk.Label(self._savgol_frame, text="Polynomial Order:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        poly_entry = ttk.Spinbox(self._savgol_frame, from_=2, to=5, textvariable=sg_poly_var, width=5)
        poly_entry.grid(row=0, column=1, padx=5, pady=3)
        ttk.Label(self._savgol_frame, text="(2-5) Lower = smoother, higher = sharper peaks but noisier").grid(
            row=0, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(poly_entry,
            "Order of the polynomial fitted to each window of samples.\n"
            "2 (quadratic): very smooth, rounds off stroke peaks.\n"
            "3 (cubic, default): good balance of shape and smoothness.\n"
            "4-5 (quartic/quintic): tracks sharper features but\n"
            "amplifies noise on jittery scripts.")

        ttk.Label(self._savgol_frame, text="Fit Window Factor:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        fit_entry = ttk.Entry(self._savgol_frame, textvariable=sg_fit_var, width=6)
        fit_entry.grid(row=1, column=1, padx=5, pady=3)
        ttk.Label(self._savgol_frame, text="(0.05-0.5) Fraction of Speed Window used for polynomial fit").grid(
            row=1, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(fit_entry,
            "Controls how local the polynomial fit is, as a fraction\n"
            "of the Speed Window setting.\n"
            "0.05: very short fit, tracks every wiggle.\n"
            "0.15 (default): good balance.\n"
            "0.3-0.5: broader fit, smooths over short strokes.")

        ttk.Label(self._savgol_frame, text="Post-Smoothing:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        smooth_entry = ttk.Entry(self._savgol_frame, textvariable=sg_smooth_var, width=6)
        smooth_entry.grid(row=2, column=1, padx=5, pady=3)
        ttk.Label(self._savgol_frame, text="(0.0-1.0) EMA smoothing applied after the derivative. 0 = off").grid(
            row=2, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(smooth_entry,
            "Light EMA smoothing applied on top of the savgol derivative\n"
            "so the output's overall 'smoothness feel' matches the\n"
            "other methods at the same Speed Window setting.\n"
            "0.0: raw derivative, most detail, may be spiky.\n"
            "0.25 (default): gentle smoothing.\n"
            "0.5-1.0: heavy smoothing, approaches EMA behavior.")

        self._savgol_frame_row = row  # remembered by _update_method_ui
        # Set initial visibility
        self._update_speed_method_ui()

        row += 1

        # Interpolation Interval
        ttk.Label(frame, text="Interpolation Interval:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['speed']['interpolation_interval'])
        self.parameter_vars['speed']['interpolation_interval'] = var
        interp_entry = ttk.Entry(frame, textvariable=var, width=10)
        interp_entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.01-1.0) Seconds between interpolated points").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(interp_entry,
            "Resampling density before speed/accel calculation.\n"
            "0.02 = 50 pts/sec (default, good balance).\n"
            "0.01 = 100 pts/sec (captures faster transients, slower processing).\n"
            "0.05-0.1 = 20-10 pts/sec (faster processing, loses high-freq detail).\n"
            "Also sets the alpha/beta grid density.")

        row += 1

        # Normalization Method
        ttk.Label(frame, text="Normalization Method:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar(value=self.config['speed']['normalization_method'])
        self.parameter_vars['speed']['normalization_method'] = var
        combo = ttk.Combobox(frame, textvariable=var, values=["max", "rms"], state="readonly", width=15)
        combo.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="Method for normalizing speed values").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # Speed/Accel Preview
        self._build_speed_preview(frame, row)

    def _build_speed_preview(self, parent, row):
        """Build a stacked preview showing input, speed, and acceleration."""
        preview_frame = ttk.LabelFrame(parent, text="Speed / Acceleration Preview", padding="5")
        preview_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(10, 5))
        preview_frame.columnconfigure(0, weight=1)

        btn_row = ttk.Frame(preview_frame)
        btn_row.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(btn_row, text="Refresh Preview",
                   command=self._refresh_speed_preview).pack(side=tk.LEFT)

        self._speed_compare_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(btn_row, text="Compare all methods",
                        variable=self._speed_compare_var).pack(side=tk.LEFT, padx=(10, 0))

        self._speed_preview_source_label = ttk.Label(btn_row, text="", foreground='#666')
        self._speed_preview_source_label.pack(side=tk.LEFT, padx=(10, 0))

        self._speed_preview_canvas_frame = ttk.Frame(preview_frame)
        self._speed_preview_canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self._speed_preview_canvas_frame.columnconfigure(0, weight=1)

        self._speed_preview_data = None

    def _refresh_speed_preview(self):
        """Compute and draw the speed/accel preview."""
        try:
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            return

        from funscript import Funscript
        from processing.speed_processing import convert_to_speed
        import os

        # Load source funscript or generate synthetic
        source_label = "Source: synthetic sine wave (no file loaded)"
        t = None
        input_y = None

        mw = getattr(self, 'main_window', None)
        if mw and hasattr(mw, 'input_files') and mw.input_files:
            input_path = mw.input_files[0]
            if os.path.isfile(input_path) and input_path.endswith('.funscript'):
                try:
                    fs = Funscript.from_file(input_path)
                    t = np.asarray(fs.x, dtype=float)
                    input_y = np.asarray(fs.y, dtype=float)
                    source_label = f"Source: {os.path.basename(input_path)}"
                except Exception:
                    pass

        if t is None:
            duration = 10.0
            n = 500
            t = np.linspace(0, duration, n)
            # Mixed-speed synthetic: fast/slow/fast sections
            input_y = np.piecewise(t, [t < 3, (t >= 3) & (t < 7), t >= 7], [
                lambda tt: 0.5 + 0.4 * np.sin(2 * np.pi * 2 * tt),
                lambda tt: 0.5 + 0.1 * np.sin(2 * np.pi * 0.3 * tt),
                lambda tt: 0.5 + 0.4 * np.sin(2 * np.pi * 3 * tt),
            ])

        self._speed_preview_source_label.config(text=source_label)

        source_fs = Funscript(t, input_y)

        # Read current settings
        window_s = float(self.config['general'].get('speed_window_size', 2))
        accel_w = float(self.config['general'].get('accel_window_size', 3))
        interp = float(self.config['speed'].get('interpolation_interval', 0.02))
        current_method = self.parameter_vars['speed']['method'].get()
        savgol_opts = {}
        sg_vars = self.parameter_vars['speed'].get('savgol_options', {})
        if isinstance(sg_vars, dict):
            try:
                savgol_opts = {
                    'poly_order': int(sg_vars['poly_order'].get()),
                    'fit_window_factor': float(sg_vars['fit_window_factor'].get()),
                    'post_smooth_factor': float(sg_vars['post_smooth_factor'].get()),
                }
            except (tk.TclError, ValueError, KeyError):
                pass

        compare = self._speed_compare_var.get()
        methods_to_plot = ['rolling_average', 'ema', 'savgol'] if compare else [current_method]

        method_labels = {
            'rolling_average': 'Rolling Avg',
            'ema': 'EMA',
            'savgol': 'Savitzky-Golay',
        }
        method_colors = {
            'rolling_average': '#2196F3',
            'ema': '#4CAF50',
            'savgol': '#FF9800',
        }

        # Compute speed and accel for each method
        results = {}
        for method in methods_to_plot:
            try:
                opts = savgol_opts if method == 'savgol' else {}
                speed_fs = convert_to_speed(source_fs, window_s, interp,
                                            method=method, savgol_options=opts)
                accel_fs = convert_to_speed(speed_fs, accel_w, interp,
                                           method=method, savgol_options=opts)
                results[method] = {
                    'speed_x': np.asarray(speed_fs.x),
                    'speed_y': np.asarray(speed_fs.y),
                    'accel_x': np.asarray(accel_fs.x),
                    'accel_y': np.asarray(accel_fs.y),
                }
            except Exception as e:
                print(f"Speed preview error ({method}): {e}")

        if not results:
            return

        # Clear old canvas
        for widget in self._speed_preview_canvas_frame.winfo_children():
            widget.destroy()

        # Build figure: 3 stacked subplots (input, speed, accel)
        n_rows = 3
        fig = Figure(figsize=(8, 4.5), dpi=85)
        fig.patch.set_facecolor('#f0f0f0')

        # 1) Input position
        ax1 = fig.add_subplot(n_rows, 1, 1)
        ax1.plot(t, input_y, color='#333', linewidth=0.8, alpha=0.8)
        ax1.set_ylabel('Position', fontsize=7)
        ax1.set_ylim(-0.05, 1.05)
        ax1.set_xlim(t[0], t[-1])
        ax1.tick_params(labelsize=6)
        ax1.grid(True, alpha=0.2)
        ax1.set_title('Input Signal', fontsize=8, loc='left')

        # 2) Speed
        ax2 = fig.add_subplot(n_rows, 1, 2, sharex=ax1)
        for method in methods_to_plot:
            if method in results:
                r = results[method]
                ax2.plot(r['speed_x'], r['speed_y'],
                         color=method_colors[method],
                         linewidth=1.0 if compare else 1.2,
                         alpha=0.7 if compare else 0.9,
                         label=method_labels[method])
        ax2.set_ylabel('Speed', fontsize=7)
        ax2.set_ylim(-0.05, 1.05)
        ax2.tick_params(labelsize=6)
        ax2.grid(True, alpha=0.2)
        title = f'Speed (window={window_s}s)'
        if not compare:
            title += f' \u2014 {method_labels.get(current_method, current_method)}'
        ax2.set_title(title, fontsize=8, loc='left')
        if compare:
            ax2.legend(fontsize=6, loc='upper right', ncol=3)

        # 3) Acceleration
        ax3 = fig.add_subplot(n_rows, 1, 3, sharex=ax1)
        for method in methods_to_plot:
            if method in results:
                r = results[method]
                ax3.plot(r['accel_x'], r['accel_y'],
                         color=method_colors[method],
                         linewidth=1.0 if compare else 1.2,
                         alpha=0.7 if compare else 0.9,
                         label=method_labels[method])
        ax3.set_ylabel('Accel', fontsize=7)
        ax3.set_xlabel('Time (s)', fontsize=7)
        ax3.set_ylim(-0.05, 1.05)
        ax3.tick_params(labelsize=6)
        ax3.grid(True, alpha=0.2)
        ax3.set_title(f'Acceleration (window={accel_w}s)', fontsize=8, loc='left')
        if compare:
            ax3.legend(fontsize=6, loc='upper right', ncol=3)

        fig.tight_layout(pad=0.8)

        canvas = FigureCanvasTkAgg(fig, self._speed_preview_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._speed_preview_canvas = canvas

    def setup_frequency_tab(self):
        """Setup the Frequency parameters tab."""
        frame = self.frequency_frame
        self.parameter_vars['frequency'] = {}

        row = 0

        # Pulse Frequency Min
        ttk.Label(frame, text="Pulse Frequency Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['pulse_freq_min'])
        self.parameter_vars['frequency']['pulse_freq_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum value for final pulse frequency output").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Floor of the pulse-frequency output range. The combined "
            "Ramp/Speed signal is mapped into [min, max], so this "
            "caps the lowest frequency restim will ever see. Raise to "
            "feel continuous buzz even on slow sections; lower for "
            "more silence.")

        row += 1

        # Pulse Frequency Max
        ttk.Label(frame, text="Pulse Frequency Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['frequency']['pulse_freq_max'])
        self.parameter_vars['frequency']['pulse_freq_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum value for final pulse frequency output").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Ceiling of the pulse-frequency output range. Lower this "
            "if aggressive strokes peg the frequency too high and the "
            "signal feels harsh; raise to widen the dynamic range.")

        row += 1

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Frequency Ramp Combine Ratio
        freq_ramp_control = CombineRatioControl(
            frame, "Frequency Combine:",
            "Ramp", "Speed",
            self.config['frequency']['frequency_ramp_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['frequency']['frequency_ramp_combine_ratio'] = freq_ramp_control.var
        self.combine_ratio_controls['frequency_ramp_combine_ratio'] = freq_ramp_control

        row += 1

        # Pulse Frequency Combine Ratio
        pulse_freq_control = CombineRatioControl(
            frame, "Pulse Frequency Combine:",
            "Speed", "Alpha-Frequency",
            self.config['frequency']['pulse_frequency_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['frequency']['pulse_frequency_combine_ratio'] = pulse_freq_control.var
        self.combine_ratio_controls['pulse_frequency_combine_ratio'] = pulse_freq_control

        row += 1

        # Map Pulse Frequency to Position toggle
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3,
                                                       sticky=(tk.W, tk.E), padx=5, pady=10)
        row += 1

        var = tk.BooleanVar(value=self.config['frequency'].get('map_pulse_freq_to_position', False))
        self.parameter_vars['frequency']['map_pulse_freq_to_position'] = var
        ttk.Checkbutton(frame, text="Map Pulse Frequency directly to Position",
                        variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        row += 1
        ttk.Label(frame, text="When enabled, pulse frequency is mapped directly from the input funscript position "
                  "(0-100) to the min/max range, bypassing the Speed/Alpha combine.",
                  wraplength=500, foreground='gray').grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=20, pady=(0, 5))

    def setup_volume_tab(self):
        """Setup the Volume parameters tab."""
        frame = self.volume_frame
        self.parameter_vars['volume'] = {}

        row = 0

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Volume Ramp Combine Ratio
        volume_ramp_control = CombineRatioControl(
            frame, "Volume Combine Ratio (Ramp | Speed):",
            "Ramp", "Speed",
            self.config['volume']['volume_ramp_combine_ratio'],
            min_val=10.0, max_val=40.0, row=row
        )
        self.parameter_vars['volume']['volume_ramp_combine_ratio'] = volume_ramp_control.var
        self.combine_ratio_controls['volume_ramp_combine_ratio'] = volume_ramp_control

        row += 1

        # Prostate Volume Multiplier
        ttk.Label(frame, text="Prostate Volume Multiplier:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['prostate_volume_multiplier'])
        self.parameter_vars['volume']['prostate_volume_multiplier'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(1.0-3.0) Multiplier for prostate volume ratio").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Extra volume gain applied only to the prostate output "
            "files. 1.0 = same as main volume; 1.5 = 50% hotter; "
            "higher if your device needs more energy to drive the "
            "prostate electrodes. Does not affect main alpha/beta.")

        row += 1

        # Prostate Volume Rest Level
        ttk.Label(frame, text="Prostate Volume Rest Level:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['volume']['prostate_rest_level'])
        self.parameter_vars['volume']['prostate_rest_level'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Rest level for prostate volume").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Baseline for the prostate volume channel during quiet "
            "sections. Usually higher than the main rest level (0.7 "
            "default) so the prostate stim stays present even when "
            "the main signal rests.")

        row += 1

        # Ramp Percent Per Hour
        ttk.Label(frame, text="Ramp (% per hour):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=self.config['volume']['ramp_percent_per_hour'])
        self.parameter_vars['volume']['ramp_percent_per_hour'] = var
        ramp_scale = ttk.Scale(frame, from_=0, to=40, variable=var, orient=tk.HORIZONTAL, length=150, command=self._update_ramp_display)
        ramp_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Create label for current value and per-minute calculation
        self.ramp_value_label = ttk.Label(frame, text="",
                                           style='Accent.TLabel')
        self.ramp_value_label.grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)

        # Initial update
        self._update_ramp_display()

    def setup_pulse_tab(self):
        """Setup the Pulse parameters tab."""
        frame = self.pulse_frame
        self.parameter_vars['pulse'] = {}

        row = 0

        # Pulse Width Min
        ttk.Label(frame, text="Pulse Width Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_width_min'])
        self.parameter_vars['pulse']['pulse_width_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum limit for pulse width").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Floor of the pulse-width output. Wider pulses feel "
            "'fuller' and warmer; narrower feel 'sharper' and colder. "
            "This caps how thin the pulses can get.")

        row += 1

        # Pulse Width Max
        ttk.Label(frame, text="Pulse Width Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_width_max'])
        self.parameter_vars['pulse']['pulse_width_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum limit for pulse width").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Ceiling of the pulse-width output. Lower this if peaks "
            "feel overloaded; raise for thicker, bassier sensation "
            "on deep strokes.")

        row += 1

        # Configure grid for the combination controls
        frame.columnconfigure(1, weight=1)

        # Pulse Width Combine Ratio
        pulse_width_control = CombineRatioControl(
            frame, "Pulse Width Combine:",
            "Speed", "Alpha-Limited",
            self.config['pulse']['pulse_width_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['pulse']['pulse_width_combine_ratio'] = pulse_width_control.var
        self.combine_ratio_controls['pulse_width_combine_ratio'] = pulse_width_control

        row += 1

        # Beta Mirror Threshold
        ttk.Label(frame, text="Beta Mirror Threshold:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['beta_mirror_threshold'])
        self.parameter_vars['pulse']['beta_mirror_threshold'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-0.5) Threshold for beta mirroring").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Inflection point where the beta side's pulse-width "
            "mirror flips. Tunes how symmetric the pulse-width shape "
            "feels between up and down strokes. 0.5 = perfectly "
            "mirrored; lower = early flip.")

        row += 1

        # Pulse Rise Time Min
        ttk.Label(frame, text="Pulse Rise Time Min:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_rise_min'])
        self.parameter_vars['pulse']['pulse_rise_min'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Minimum mapping for pulse rise time").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Floor of the pulse-rise (attack) curve. Controls how "
            "sharp the onset of each pulse feels: 0 = instant hit, "
            "higher = softer attack. This caps the fastest attack "
            "restim ever sees.")

        row += 1

        # Pulse Rise Time Max
        ttk.Label(frame, text="Pulse Rise Time Max:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=self.config['pulse']['pulse_rise_max'])
        self.parameter_vars['pulse']['pulse_rise_max'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Maximum mapping for pulse rise time").grid(row=row, column=2, sticky=tk.W, padx=5)
        self._create_entry_tooltip(entry,
            "Ceiling of the pulse-rise (attack) curve. Higher = "
            "softest attack allowed. Lower for consistently sharp "
            "onsets regardless of signal level.")

        row += 1

        # Pulse Rise Combine Ratio
        pulse_rise_control = CombineRatioControl(
            frame, "Pulse Rise Combine:",
            "Beta-Mirrored", "Speed-Inverted",
            self.config['pulse']['pulse_rise_combine_ratio'],
            min_val=1, max_val=10, row=row
        )
        self.parameter_vars['pulse']['pulse_rise_combine_ratio'] = pulse_rise_control.var
        self.combine_ratio_controls['pulse_rise_combine_ratio'] = pulse_rise_control

    def setup_motion_axis_3p_tab(self):
        """Setup the Motion Axis (3P) tab — legacy alpha/beta generation."""
        frame = self.motion_axis_3p_frame
        row = 0

        # Row 0: Generate motion scripts | Generate phase-shifted versions | Delay
        generate_legacy_var = tk.BooleanVar(value=self.config['positional_axes'].get('generate_legacy', True))
        self.parameter_vars['positional_axes']['generate_legacy'] = generate_legacy_var
        ttk.Checkbutton(frame, text="Generate motion scripts",
                        variable=generate_legacy_var).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

        self.parameter_vars['positional_axes']['phase_shift'] = {}
        phase_shift_enabled_var = tk.BooleanVar(value=self.config['positional_axes']['phase_shift']['enabled'])
        self.parameter_vars['positional_axes']['phase_shift']['enabled'] = phase_shift_enabled_var
        ttk.Checkbutton(frame, text="Generate phase-shifted versions (*-2.funscript)",
                        variable=phase_shift_enabled_var).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)

        delay_frame_3p = ttk.Frame(frame)
        delay_frame_3p.grid(row=row, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(delay_frame_3p, text="Delay:").pack(side=tk.LEFT)
        # Migrate from percentage to ms if needed
        ps_cfg = self.config['positional_axes']['phase_shift']
        default_ms = ps_cfg.get('delay_ms', ps_cfg.get('delay_percentage', 10.0) * 10)
        delay_ms_var = tk.DoubleVar(value=default_ms)
        self.parameter_vars['positional_axes']['phase_shift']['delay_ms'] = delay_ms_var
        delay_entry_3p = ttk.Entry(delay_frame_3p, textvariable=delay_ms_var, width=6)
        delay_entry_3p.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(delay_frame_3p, text="ms").pack(side=tk.LEFT)
        self._create_entry_tooltip(delay_entry_3p, "Fixed delay in milliseconds")

        row += 1

        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3,
                                                       sticky=(tk.W, tk.E), padx=5, pady=10)
        row += 1

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(row, weight=1)

        self.content_container = ttk.Frame(frame)
        self.content_container.grid(row=row, column=0, columnspan=3,
                                    sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        self.setup_legacy_section()
        self.legacy_frame.grid()  # always visible in this tab

    def setup_motion_axis_4p_tab(self):
        """Setup the Motion Axis (4P) tab — E1-E4 generation."""
        self._ma_presets_ensure()

        frame = self.motion_axis_4p_frame
        row = 0

        # Row 0: Generate motion scripts | Generate phase-shifted versions | Delay
        generate_motion_axis_var = tk.BooleanVar(
            value=self.config['positional_axes'].get('generate_motion_axis', True))
        self.parameter_vars['positional_axes']['generate_motion_axis'] = generate_motion_axis_var
        ttk.Checkbutton(frame, text="Generate motion scripts",
                        variable=generate_motion_axis_var).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

        self.parameter_vars['positional_axes']['motion_axis_phase_shift'] = {}
        ma_ps_config = self.config['positional_axes'].get(
            'motion_axis_phase_shift', self.config['positional_axes']['phase_shift'])
        ma_phase_enabled_var = tk.BooleanVar(value=ma_ps_config['enabled'])
        self.parameter_vars['positional_axes']['motion_axis_phase_shift']['enabled'] = ma_phase_enabled_var
        ttk.Checkbutton(frame, text="Generate phase-shifted versions (*-2.funscript)",
                        variable=ma_phase_enabled_var).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)

        delay_frame_4p = ttk.Frame(frame)
        delay_frame_4p.grid(row=row, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(delay_frame_4p, text="Delay:").pack(side=tk.LEFT)
        ma_default_ms = ma_ps_config.get('delay_ms', ma_ps_config.get('delay_percentage', 10.0) * 10)
        ma_delay_ms_var = tk.DoubleVar(value=ma_default_ms)
        self.parameter_vars['positional_axes']['motion_axis_phase_shift']['delay_ms'] = ma_delay_ms_var
        delay_entry_4p = ttk.Entry(delay_frame_4p, textvariable=ma_delay_ms_var, width=6)
        delay_entry_4p.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(delay_frame_4p, text="ms").pack(side=tk.LEFT)
        self._create_entry_tooltip(delay_entry_4p, "Fixed delay in milliseconds")

        row += 1

        # Row 1: Physical Model — cascaded per-axis delays for apparent motion
        self._build_physical_model_row(frame, row)
        row += 1

        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3,
                                                       sticky=(tk.W, tk.E), padx=5, pady=10)
        row += 1

        # Row 2: Preset selector
        preset_row = ttk.Frame(frame)
        preset_row.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(2, 6))

        ttk.Label(preset_row, text="Config preset:").pack(side=tk.LEFT, padx=(0, 5))

        self._ma_active_name = tk.StringVar(
            value=self.config['motion_axis_presets'].get('active', 'Default'))
        self._ma_combobox = ttk.Combobox(
            preset_row, textvariable=self._ma_active_name,
            values=list(self.config['motion_axis_presets']['presets'].keys()),
            state='readonly', width=22)
        self._ma_combobox.pack(side=tk.LEFT, padx=(0, 8))
        self._ma_combobox.bind('<<ComboboxSelected>>', self._ma_on_select)

        ttk.Button(preset_row, text="New",    width=6, command=self._ma_new).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_row, text="Delete", width=7, command=self._ma_delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_row, text="Rename", width=7, command=self._ma_rename).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_row, text="Export", width=7, command=self._ma_export).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_row, text="Import", width=7, command=self._ma_import).pack(side=tk.LEFT, padx=2)

        row += 1

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(row, weight=1)

        self.content_container = ttk.Frame(frame)
        self.content_container.grid(row=row, column=0, columnspan=3,
                                    sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        self.setup_motion_axis_section_internal()
        self.motion_config_frame.grid()  # always visible in this tab

        # Angle Manipulation section
        angle_frame = ttk.LabelFrame(self.content_container, text="Angle Manipulation", padding="10")
        angle_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=0, pady=(10, 5))

        for i, axis_name in enumerate(['E1', 'E2', 'E3', 'E4']):
            ttk.Label(angle_frame, text=f"{axis_name} (\u00b0):").grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(angle_frame, width=10)
            entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
            setattr(self, f'angle_{axis_name.lower()}_entry', entry)

        ttk.Button(angle_frame, text="Apply", command=self._apply_angle_4p).grid(
            row=4, column=0, columnspan=2, pady=10)

        # Waveform Preview section
        self._build_preview_section(self.content_container, grid_row=2)

    def _build_preview_section(self, parent, grid_row):
        """Build the inline waveform preview showing input and E1-E4 output."""
        preview_frame = ttk.LabelFrame(parent, text="Waveform Preview", padding="10")
        preview_frame.grid(row=grid_row, column=0, sticky=(tk.W, tk.E), padx=0, pady=(10, 5))
        preview_frame.columnconfigure(0, weight=1)
        self._preview_frame = preview_frame

        # Controls row
        btn_row = ttk.Frame(preview_frame)
        btn_row.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 5))
        ttk.Button(btn_row, text="Refresh Preview", command=self._refresh_preview).pack(side=tk.LEFT)
        self._preview_source_label = ttk.Label(btn_row, text="")
        self._preview_source_label.pack(side=tk.LEFT, padx=(10, 0))

        # Zoom controls
        zoom_frame = ttk.Frame(btn_row)
        zoom_frame.pack(side=tk.RIGHT)
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 5))
        self._preview_zoom_var = tk.IntVar(value=100)
        zoom_combo = ttk.Combobox(
            zoom_frame, textvariable=self._preview_zoom_var,
            values=list(range(100, 8200, 200)),
            width=6)
        zoom_combo.pack(side=tk.LEFT)
        ttk.Label(zoom_frame, text="%").pack(side=tk.LEFT)
        zoom_combo.bind('<<ComboboxSelected>>', lambda e: self._on_zoom_change())
        zoom_combo.bind('<Return>', lambda e: self._on_zoom_change())

        # Scroll position (0.0 = start, 1.0 = end)
        self._preview_scroll_var = tk.DoubleVar(value=0.0)
        self._preview_scrollbar = ttk.Scale(
            preview_frame, from_=0.0, to=1.0,
            orient=tk.HORIZONTAL, variable=self._preview_scroll_var,
            command=lambda v: self._apply_preview_zoom())
        # Hidden by default (shown when zoom > 100%)
        self._preview_scrollbar_visible = False

        self._preview_canvas_frame = ttk.Frame(preview_frame)
        self._preview_canvas_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self._preview_canvas_frame.columnconfigure(0, weight=1)

        # Store full data for zooming without re-computing
        self._preview_data = None

        self._refresh_preview()

    def _refresh_preview(self):
        """Recompute preview data from current curve config, then draw."""
        if getattr(self, '_loading_config', False):
            return
        try:
            import numpy as np
        except ImportError:
            return

        from processing.linear_mapping import apply_linear_response_curve
        from funscript import Funscript
        import os

        # Try to load actual input funscript
        source_label = "Source: synthetic sine wave (no file loaded)"
        t = None
        input_y = None

        mw = getattr(self, 'main_window', None)
        if mw and hasattr(mw, 'input_files') and mw.input_files:
            input_path = mw.input_files[0]
            if os.path.isfile(input_path) and input_path.endswith('.funscript'):
                try:
                    fs = Funscript.from_file(input_path)
                    t = fs.x
                    input_y = fs.y
                    source_label = f"Source: {os.path.basename(input_path)}"
                except Exception:
                    pass

        # Fallback to synthetic sine wave
        if t is None:
            duration = 10.0
            num_points = 200
            t = np.linspace(0, duration, num_points)
            input_y = 0.5 + 0.4 * np.sin(2 * np.pi * 0.5 * t)

        if hasattr(self, '_preview_source_label') and self._preview_source_label.winfo_exists():
            self._preview_source_label.config(text=source_label)

        # Curve quantization preview pass: if enabled, snap input to
        # quantization levels before deriving the E1-E4 outputs. Keep the
        # raw signal around so the input subplot can overlay both.
        input_y_raw = np.asarray(input_y, dtype=float)
        tq_cfg = self.config.get('trochoid_quantization', {})
        tq_enabled = bool(tq_cfg.get('enabled', False))
        tq_levels = None
        if tq_enabled:
            try:
                from processing.trochoid_quantization import (
                    generate_curve_levels, FAMILY_DEFAULTS as _FAMD)
                family = str(tq_cfg.get('family',
                                        tq_cfg.get('curve_type', 'hypo')))
                params_by_family = tq_cfg.get('params_by_family') or {}
                family_params = dict(params_by_family.get(family) or {})
                if not family_params and family in ('hypo', 'epi'):
                    family_params = {
                        'R': float(tq_cfg.get('R', 5.0)),
                        'r': float(tq_cfg.get('r', 3.0)),
                        'd': float(tq_cfg.get('d', 2.0)),
                    }
                if not family_params:
                    family_params = dict(
                        _FAMD.get(family, {}).get('params', {}))
                tq_levels = generate_curve_levels(
                    int(tq_cfg.get('n_points', 23)),
                    family, family_params,
                    str(tq_cfg.get('projection', 'radius')),
                )
                # Snap each input sample to the nearest level
                idx = np.searchsorted(tq_levels, input_y_raw)
                idx = np.clip(idx, 1, len(tq_levels) - 1)
                left = tq_levels[idx - 1]
                right = tq_levels[idx]
                input_y = np.where(
                    np.abs(input_y_raw - left) <= np.abs(input_y_raw - right),
                    left, right)
            except (ValueError, TypeError) as e:
                print(f"[preview] curve quantization skipped: {e}")
                input_y = input_y_raw
                tq_enabled = False
        else:
            input_y = input_y_raw

        # E1-E4 derivation: when trochoid_spatial is enabled it overrides
        # the response-curve path entirely (mirrors the processor wiring).
        # Otherwise: rotate input by signal_angle, apply per-axis response
        # curve.
        ts_cfg = self.config.get('trochoid_spatial', {}) or {}
        ts_enabled = bool(ts_cfg.get('enabled', False))
        axis_outputs = {}
        axis_labels = {}
        if ts_enabled:
            try:
                from processing.trochoid_spatial import (
                    compute_spatial_intensities)
                from processing.trochoid_quantization import (
                    FAMILY_DEFAULTS as _SFAMD)
                ts_family = str(ts_cfg.get('family', 'hypo'))
                ts_pbf = ts_cfg.get('params_by_family') or {}
                ts_params = dict(ts_pbf.get(ts_family) or {})
                if not ts_params:
                    ts_params = dict(
                        _SFAMD.get(ts_family, {}).get('params', {}))
                ts_angles = tuple(
                    float(a) for a in ts_cfg.get(
                        'electrode_angles_deg', [0, 90, 180, 270]))
                spatial = compute_spatial_intensities(
                    input_y, ts_family, ts_params,
                    electrode_angles_deg=ts_angles,
                    mapping=str(ts_cfg.get('mapping', 'directional')),
                    sharpness=float(ts_cfg.get('sharpness', 1.0)),
                    cycles_per_unit=float(
                        ts_cfg.get('cycles_per_unit', 1.0)),
                )
                for i, axis_name in enumerate(['e1', 'e2', 'e3', 'e4']):
                    axis_outputs[axis_name] = np.asarray(spatial[axis_name])
                    axis_labels[axis_name] = (
                        f"{axis_name.upper()}: spatial "
                        f"({ts_family}, {ts_angles[i]:.0f}°)")
                print(f"[preview] trochoid_spatial: family={ts_family} "
                      f"mapping={ts_cfg.get('mapping')} "
                      f"sharpness={ts_cfg.get('sharpness')}")
            except Exception as e:
                print(f"[preview] trochoid_spatial failed, falling back "
                      f"to response curves: {e}")
                ts_enabled = False  # fall through to response-curve path

        if not ts_enabled:
            import math
            axes_config = self.config['positional_axes']
            for axis_name in ['e1', 'e2', 'e3', 'e4']:
                cfg = axes_config.get(axis_name, {})
                enabled = cfg.get('enabled', False)
                curve = cfg.get('curve', {})
                cp = curve.get('control_points', [[0.0, 0.0], [1.0, 1.0]])
                signal_angle = cfg.get('signal_angle', 0)
                label = f"{axis_name.upper()}: {curve.get('name', 'N/A')}"
                if signal_angle:
                    label += f" ({signal_angle:.0f}\u00b0)"
                if enabled:
                    cos_a = math.cos(math.radians(signal_angle))
                    rotated_input = np.clip(
                        0.5 + (input_y - 0.5) * cos_a, 0.0, 1.0)
                    out = np.array([apply_linear_response_curve(v, cp)
                                    for v in rotated_input])
                    axis_outputs[axis_name] = out
                    print(f"[preview] {axis_name}: angle={signal_angle}\u00b0 "
                          f"rotated range={rotated_input.min():.3f}"
                          f"-{rotated_input.max():.3f} "
                          f"output range={out.min():.3f}-{out.max():.3f}")
                else:
                    axis_outputs[axis_name] = None
                    label += ' (disabled)'
                axis_labels[axis_name] = label

        self._preview_data = {
            't': t,
            'input_y': input_y,           # active (possibly quantized)
            'input_y_raw': input_y_raw,   # original
            'tq_enabled': tq_enabled,
            'tq_levels': tq_levels,
            'ts_enabled': ts_enabled,
            'axis_outputs': axis_outputs, 'axis_labels': axis_labels,
        }



        self._apply_preview_zoom()

    def _on_zoom_change(self):
        """Validate zoom input and apply."""
        try:
            val = int(self._preview_zoom_var.get())
        except (ValueError, tk.TclError):
            val = 100
        val = max(100, min(val, 8000))
        self._preview_zoom_var.set(val)
        self._apply_preview_zoom()

    def _apply_preview_zoom(self, *_args):
        """Redraw the preview plots at the current zoom and scroll position."""
        if not self._preview_data:
            return
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np
        except ImportError:
            ttk.Label(self._preview_canvas_frame,
                      text="Matplotlib required for preview (pip install matplotlib)",
                      foreground="red").grid(row=0, column=0)
            return

        # Clear previous plots
        for child in self._preview_canvas_frame.winfo_children():
            child.destroy()

        t = self._preview_data['t']
        input_y = self._preview_data['input_y']
        input_y_raw = self._preview_data.get('input_y_raw', input_y)
        tq_enabled = self._preview_data.get('tq_enabled', False)
        tq_levels = self._preview_data.get('tq_levels', None)
        axis_outputs = self._preview_data['axis_outputs']
        axis_labels = self._preview_data['axis_labels']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        t_full_start, t_full_end = t[0], t[-1]
        full_duration = t_full_end - t_full_start

        # Compute visible window from zoom and scroll
        zoom_pct = self._preview_zoom_var.get()
        visible_duration = full_duration / (zoom_pct / 100.0)
        scroll_pos = self._preview_scroll_var.get()
        view_start = t_full_start + scroll_pos * (full_duration - visible_duration)
        view_end = view_start + visible_duration

        # Show/hide scrollbar
        if zoom_pct > 100:
            if not self._preview_scrollbar_visible:
                self._preview_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=0, pady=(2, 0))
                self._preview_scrollbar_visible = True
        else:
            if self._preview_scrollbar_visible:
                self._preview_scrollbar.grid_remove()
                self._preview_scrollbar_visible = False

        # Filter data to visible window (with small margin for smooth edges)
        mask = (t >= view_start) & (t <= view_end)
        t_vis = t[mask]
        input_vis = input_y[mask]
        input_raw_vis = input_y_raw[mask]

        # Downsample for responsiveness
        max_pts = 2000
        if len(t_vis) > max_pts:
            step = len(t_vis) // max_pts
            t_plot = t_vis[::step]
            input_plot = input_vis[::step]
            input_raw_plot = input_raw_vis[::step]
        else:
            t_plot = t_vis
            input_plot = input_vis
            input_raw_plot = input_raw_vis

        # Thicker lines at high zoom
        lw = 0.8 if zoom_pct <= 200 else 1.2 if zoom_pct <= 400 else 1.6

        # 7 rows: input + 4 axes + spacer + overlay
        fig = Figure(figsize=(7, 8), dpi=85)
        fig.patch.set_facecolor('#f0f0f0')
        gs = fig.add_gridspec(7, 1, height_ratios=[1, 1, 1, 1, 1, 0.15, 1.5], hspace=0.3)

        # Input waveform — overlay raw + quantized when curve quant is enabled.
        # Use linear (not step) plotting because that matches how playback
        # devices linearly interpolate between funscript samples.
        ax_in = fig.add_subplot(gs[0])
        if tq_enabled:
            ax_in.plot(t_plot, input_raw_plot * 100,
                       color='#999999', linewidth=max(0.6, lw * 0.7),
                       alpha=0.55, label='Raw', zorder=1)
            if tq_levels is not None:
                for lv in tq_levels:
                    ax_in.axhline(lv * 100, color='#d94a4a',
                                  linewidth=0.4, alpha=0.35, zorder=0)
            ax_in.plot(t_plot, input_plot * 100,
                       color='#222222', linewidth=lw,
                       label='Quantized (device)', zorder=3)
            ax_in.fill_between(t_plot, 0, input_plot * 100,
                               alpha=0.12, color='#222222', zorder=2)
            ax_in.legend(loc='upper right', fontsize=7, ncol=2,
                         framealpha=0.7)
            in_label = 'Input (curve)'
        else:
            ax_in.plot(t_plot, input_plot * 100,
                       color='#555555', linewidth=lw)
            ax_in.fill_between(t_plot, 0, input_plot * 100,
                               alpha=0.15, color='#555555')
            in_label = 'Input'
        ax_in.set_ylabel(in_label, fontsize=8)
        ax_in.set_ylim(0, 100)
        ax_in.set_xlim(view_start, view_end)
        ax_in.grid(True, alpha=0.3)
        ax_in.tick_params(labelsize=7)
        ax_in.set_xticklabels([])

        # Individual output waveforms
        axis_plot_data = {}
        for idx, (axis_name, color) in enumerate(zip(['e1', 'e2', 'e3', 'e4'], colors)):
            ax = fig.add_subplot(gs[idx + 1])
            output = axis_outputs[axis_name]
            if output is not None:
                out_vis = output[mask]
                out_plot = out_vis[::step] if len(out_vis) > max_pts else out_vis
                ax.plot(t_plot, out_plot * 100, color=color, linewidth=lw)
                ax.fill_between(t_plot, 0, out_plot * 100, alpha=0.15, color=color)
                axis_plot_data[axis_name] = out_plot
            else:
                axis_plot_data[axis_name] = None

            ax.set_ylabel(axis_labels[axis_name], fontsize=7)
            ax.set_ylim(0, 100)
            ax.set_xlim(view_start, view_end)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=7)
            ax.set_xticklabels([])

        # Spacer row (invisible)
        ax_spacer = fig.add_subplot(gs[5])
        ax_spacer.set_visible(False)

        # Overlay: all enabled axes on one plot
        ax_overlay = fig.add_subplot(gs[6])
        for axis_name, color in zip(['e1', 'e2', 'e3', 'e4'], colors):
            out_plot = axis_plot_data.get(axis_name)
            if out_plot is not None:
                ax_overlay.plot(t_plot, out_plot * 100, color=color, linewidth=lw, alpha=0.8,
                                label=axis_name.upper())
                ax_overlay.fill_between(t_plot, 0, out_plot * 100, alpha=0.08, color=color)
        ax_overlay.set_ylabel('E1-E4 Overlay', fontsize=8)
        ax_overlay.set_ylim(0, 100)
        ax_overlay.set_xlim(view_start, view_end)
        ax_overlay.set_xlabel('Time (seconds)', fontsize=8)
        ax_overlay.grid(True, alpha=0.3)
        ax_overlay.tick_params(labelsize=7)
        ax_overlay.legend(loc='upper right', fontsize=7, ncol=4, framealpha=0.7)

        canvas = FigureCanvasTkAgg(fig, self._preview_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E))
        self._preview_canvas = canvas

    def _apply_angle_4p(self):
        """Apply angle values to E1-E4 axes."""
        try:
            angles = []
            for axis_name in ['e1', 'e2', 'e3', 'e4']:
                entry = getattr(self, f'angle_{axis_name}_entry')
                val = entry.get().strip()
                if not val:
                    angles.append(None)
                else:
                    angles.append(float(val))
        except ValueError:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", "Please enter valid numbers")
            return

        if all(a is None for a in angles):
            import tkinter.messagebox as messagebox
            messagebox.showwarning("Warning", "No angle values entered")
            return

        # Store signal rotation angle per axis (applied to input signal before curve)
        for i, (axis_name, angle) in enumerate(zip(['e1', 'e2', 'e3', 'e4'], angles)):
            if angle is None:
                continue
            self.config['positional_axes'][axis_name]['signal_angle'] = angle
            self.config['positional_axes'][axis_name]['enabled'] = True
            if axis_name in self.parameter_vars['positional_axes']:
                enabled_var = self.parameter_vars['positional_axes'][axis_name].get('enabled')
                if enabled_var:
                    enabled_var.set(True)
            print(f"[angle] {axis_name}: signal_angle={angle:.0f}\u00b0")

        # Refresh preview with new signal angles (no curve rebuild needed)
        self._refresh_preview()

        # Save to active preset as well
        self._ma_sync_to_store()

    # ------------------------------------------------------------------
    # Motion Axis preset helpers
    # ------------------------------------------------------------------

    # Default per-axis phase offsets (degrees) so axes wobble out of sync.
    # Mirrors DEFAULT_MODULATION_PHASE_DEG in motion_axis_generation.py.
    _MODULATION_DEFAULT_PHASE = {'e1': 0.0, 'e2': 180.0, 'e3': 90.0, 'e4': 270.0}

    # Physical-model propagation-speed presets (mm/s). These are tuned to
    # the cutaneous apparent-motion sweet spot, NOT to raw nerve conduction
    # velocity — literal nerve conduction produces sub-ms delays for
    # typical electrode spacings, which is invisible at funscript resolution.
    _PHYS_MODEL_PRESETS = [
        ("Slow sweep (100 mm/s)",     100.0),
        ("Natural touch (300 mm/s)",  300.0),
        ("Fast sweep (1000 mm/s)",   1000.0),
        ("Custom",                   None),
    ]

    def _build_physical_model_row(self, parent, row):
        """Physical-model section: a linear e1-e2-e3-e4 electrode array
        with per-axis cascade delays producing apparent motion. All four
        controls (enabled, spacing, speed, direction) live together and
        are applied directly by generate_motion_axes — no button, no
        link to the dual-variant phase-shift delay."""
        phys_cfg = self.config['positional_axes'].setdefault('physical_model', {
            'enabled': False,
            'electrode_spacing_mm': 20.0,
            'propagation_speed_mm_s': 300.0,
            'sweep_direction': 'e1_to_e4',
        })
        # Fill any missing keys so the UI has sane defaults even on old configs
        phys_cfg.setdefault('enabled', False)
        phys_cfg.setdefault('electrode_spacing_mm', 20.0)
        phys_cfg.setdefault('propagation_speed_mm_s', 300.0)
        phys_cfg.setdefault('sweep_direction', 'e1_to_e4')

        default_enabled = bool(phys_cfg['enabled'])
        default_spacing = float(phys_cfg['electrode_spacing_mm'])
        default_speed = float(phys_cfg['propagation_speed_mm_s'])
        default_direction = str(phys_cfg['sweep_direction'])

        phys_frame = ttk.LabelFrame(
            parent,
            text="Physical Model (cascade delay across linear e1\u2013e4 array)",
            padding="5")
        phys_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(0, 2))

        inner = ttk.Frame(phys_frame)
        inner.pack(fill=tk.X)

        self._phys_enabled_var = tk.BooleanVar(value=default_enabled)
        self._phys_spacing_var = tk.DoubleVar(value=default_spacing)
        self._phys_speed_var = tk.DoubleVar(value=default_speed)
        self._phys_direction_var = tk.StringVar(value=default_direction)
        self._phys_preview_var = tk.StringVar(value="")
        self._phys_preset_var = tk.StringVar(
            value=self._phys_preset_name_for_speed(default_speed))

        # Register vars under a new 'physical_model' section in parameter_vars
        # so update_config / update_display round-trip them without special
        # cases in the motion_axis_phase_shift code path.
        self.parameter_vars['positional_axes']['physical_model'] = {
            'enabled': self._phys_enabled_var,
            'electrode_spacing_mm': self._phys_spacing_var,
            'propagation_speed_mm_s': self._phys_speed_var,
            'sweep_direction': self._phys_direction_var,
        }

        # Line 1: Enabled checkbox + spacing + speed
        ttk.Checkbutton(
            inner, text="Enabled", variable=self._phys_enabled_var
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        ttk.Label(inner, text="Spacing:").grid(row=0, column=1, sticky=tk.W)
        spacing_entry = ttk.Entry(inner, textvariable=self._phys_spacing_var, width=6)
        spacing_entry.grid(row=0, column=2, padx=(3, 0))
        ttk.Label(inner, text="mm").grid(row=0, column=3, padx=(0, 10))
        self._create_entry_tooltip(
            spacing_entry,
            "Distance between adjacent electrodes (e1\u2013e2, e2\u2013e3, e3\u2013e4)")

        ttk.Label(inner, text="Speed:").grid(row=0, column=4, sticky=tk.W)
        speed_entry = ttk.Entry(inner, textvariable=self._phys_speed_var, width=7)
        speed_entry.grid(row=0, column=5, padx=(3, 0))
        ttk.Label(inner, text="mm/s").grid(row=0, column=6, padx=(0, 10))
        self._create_entry_tooltip(
            speed_entry,
            "Apparent-motion propagation speed. ~300 mm/s is the perceptual sweet spot.")

        # Line 2: Preset + direction + live preview
        ttk.Label(inner, text="Preset:").grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        preset_combo = ttk.Combobox(
            inner, textvariable=self._phys_preset_var,
            values=[name for name, _ in self._PHYS_MODEL_PRESETS],
            state='readonly', width=24,
        )
        preset_combo.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=(3, 10), pady=(4, 0))
        preset_combo.bind('<<ComboboxSelected>>', self._on_phys_preset_changed)

        ttk.Label(inner, text="Sweep:").grid(row=1, column=4, sticky=tk.W, pady=(4, 0))
        sweep_frame = ttk.Frame(inner)
        sweep_frame.grid(row=1, column=5, columnspan=2, sticky=tk.W, padx=(3, 10), pady=(4, 0))
        ttk.Radiobutton(
            sweep_frame, text="e1\u2192e4", value='e1_to_e4',
            variable=self._phys_direction_var,
            command=self._update_phys_preview,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            sweep_frame, text="e4\u2192e1", value='e4_to_e1',
            variable=self._phys_direction_var,
            command=self._update_phys_preview,
        ).pack(side=tk.LEFT, padx=(6, 0))
        follow_rb = ttk.Radiobutton(
            sweep_frame, text="follow signal", value='signal_direction',
            variable=self._phys_direction_var,
            command=self._update_phys_preview,
        )
        follow_rb.pack(side=tk.LEFT, padx=(6, 0))
        self._create_entry_tooltip(
            follow_rb,
            "Flip sweep direction to match source: e1\u2192e4 on up-strokes, "
            "e4\u2192e1 on down-strokes.")

        ttk.Label(inner, textvariable=self._phys_preview_var,
                  foreground='#666').grid(row=1, column=7, sticky=tk.W, pady=(4, 0))

        # Live preview reacts to every relevant var
        for var in (self._phys_spacing_var, self._phys_speed_var):
            var.trace_add('write', lambda *_: self._update_phys_preview())
        self._update_phys_preview()

    def _phys_preset_name_for_speed(self, speed_mm_s):
        """Pick the matching preset label for a given speed, else 'Custom'."""
        for name, val in self._PHYS_MODEL_PRESETS:
            if val is not None and abs(val - speed_mm_s) < 1e-6:
                return name
        return "Custom"

    def _on_phys_preset_changed(self, *_):
        name = self._phys_preset_var.get()
        for preset_name, val in self._PHYS_MODEL_PRESETS:
            if preset_name == name and val is not None:
                self._phys_speed_var.set(val)
                break
        # "Custom" leaves the current speed entry alone
        self._update_phys_preview()

    def _update_phys_preview(self):
        """Show step delay and total sweep time for the current settings."""
        try:
            spacing = float(self._phys_spacing_var.get())
            speed = float(self._phys_speed_var.get())
        except (tk.TclError, ValueError):
            self._phys_preview_var.set("step \u2014   sweep \u2014")
            return
        if spacing <= 0 or speed <= 0:
            self._phys_preview_var.set("step \u2014   sweep \u2014")
            return
        step_ms = (spacing / speed) * 1000.0
        total_ms = step_ms * 3.0  # e1→e4 is three hops
        direction = self._phys_direction_var.get()
        if direction == 'signal_direction':
            dir_label = "follows signal"
        elif direction == 'e4_to_e1':
            dir_label = "e4\u2192e1"
        else:
            dir_label = "e1\u2192e4"
        self._phys_preview_var.set(
            f"step {step_ms:.1f} ms   sweep {total_ms:.1f} ms ({dir_label})")
        # Keep the preset label honest if the user edits the speed directly
        matched = self._phys_preset_name_for_speed(speed)
        if self._phys_preset_var.get() != matched:
            self._phys_preset_var.set(matched)

    def _default_modulation_for(self, axis_name):
        return {
            'enabled': False,
            'frequency_hz': 0.5,
            'depth': 0.15,
            'phase_deg': self._MODULATION_DEFAULT_PHASE.get(axis_name, 0.0),
            'phase_enabled': True,
        }

    def _ensure_axis_modulation_defaults(self, axis_name):
        """Make sure positional_axes[axis_name]['modulation'] exists."""
        ax_cfg = self.config['positional_axes'].setdefault(axis_name, {})
        mod = ax_cfg.get('modulation')
        if not isinstance(mod, dict):
            ax_cfg['modulation'] = self._default_modulation_for(axis_name)
            return
        defaults = self._default_modulation_for(axis_name)
        for k, v in defaults.items():
            mod.setdefault(k, v)

    def _on_modulation_changed(self, axis_name):
        """Push modulation UI vars back into config when user edits them."""
        try:
            mod_vars = self.parameter_vars['positional_axes'][axis_name]['modulation']
        except KeyError:
            return
        ax_cfg = self.config['positional_axes'].setdefault(axis_name, {})
        mod_cfg = ax_cfg.setdefault('modulation', self._default_modulation_for(axis_name))
        try:
            mod_cfg['enabled'] = bool(mod_vars['enabled'].get())
            mod_cfg['frequency_hz'] = max(0.0, float(mod_vars['frequency_hz'].get()))
            mod_cfg['depth'] = max(0.0, min(1.0, float(mod_vars['depth'].get())))
            if 'phase_enabled' in mod_vars:
                mod_cfg['phase_enabled'] = bool(mod_vars['phase_enabled'].get())
            if 'phase_deg' in mod_vars:
                mod_cfg['phase_deg'] = float(mod_vars['phase_deg'].get())
        except (tk.TclError, ValueError):
            # Ignore mid-edit invalid values
            pass

    def _ma_blank_axis(self, axis_name='e1'):
        return {
            'enabled': False,
            'curve': {
                'name': 'Linear',
                'description': 'Linear response',
                'control_points': [[0.0, 0.0], [1.0, 1.0]],
            },
            'modulation': self._default_modulation_for(axis_name),
        }

    def _ma_blank_preset(self):
        return {
            'motion_axis_phase_shift': {
                'enabled': False,
                'delay_ms': 100.0,
                'min_segment_duration': 0.25,
            },
            'e1': self._ma_blank_axis('e1'),
            'e2': self._ma_blank_axis('e2'),
            'e3': self._ma_blank_axis('e3'),
            'e4': self._ma_blank_axis('e4'),
        }

    def _ma_extract_from_axes(self):
        """Snapshot current positional_axes config into a preset dict."""
        axes = self.config.get('positional_axes', {})
        ma_ps = axes.get('motion_axis_phase_shift', axes.get('phase_shift', {
            'enabled': False, 'delay_ms': 100.0, 'min_segment_duration': 0.25,
        }))
        preset = {'motion_axis_phase_shift': copy.deepcopy(ma_ps)}
        for ax in ['e1', 'e2', 'e3', 'e4']:
            if ax in axes:
                preset[ax] = {
                    'enabled': axes[ax].get('enabled', False),
                    'curve': copy.deepcopy(axes[ax].get('curve', self._ma_blank_axis(ax)['curve'])),
                    'modulation': copy.deepcopy(
                        axes[ax].get('modulation', self._default_modulation_for(ax))),
                }
            else:
                preset[ax] = self._ma_blank_axis(ax)
        return preset

    def _ma_presets_ensure(self):
        """Migrate config to include motion_axis_presets if missing."""
        if 'motion_axis_presets' not in self.config:
            self.config['motion_axis_presets'] = {
                'active': 'Default',
                'presets': {'Default': self._ma_extract_from_axes()},
            }
            return
        presets = self.config['motion_axis_presets'].setdefault('presets', {})
        if not presets:
            presets['Default'] = self._ma_extract_from_axes()
            self.config['motion_axis_presets']['active'] = 'Default'
        active = self.config['motion_axis_presets'].get('active', '')
        if active not in presets:
            self.config['motion_axis_presets']['active'] = next(iter(presets))

    def _ma_sync_to_store(self, config=None):
        """Write current UI state for the active preset back into motion_axis_presets."""
        if config is None:
            config = self.config
        if 'motion_axis_presets' not in config:
            return
        active = config['motion_axis_presets'].get('active')
        if not active or active not in config['motion_axis_presets']['presets']:
            return
        axes = config.get('positional_axes', {})
        ps_vars = self.parameter_vars['positional_axes'].get('motion_axis_phase_shift', {})
        ma_ps_cfg = axes.get('motion_axis_phase_shift', axes.get('phase_shift', {}))
        preset = {
            'motion_axis_phase_shift': {
                'enabled': ps_vars['enabled'].get() if 'enabled' in ps_vars else ma_ps_cfg.get('enabled', False),
                'delay_ms': ps_vars['delay_ms'].get() if 'delay_ms' in ps_vars else ma_ps_cfg.get('delay_ms', 100.0),
                'min_segment_duration': ma_ps_cfg.get('min_segment_duration', 0.25),
            },
        }
        for ax in ['e1', 'e2', 'e3', 'e4']:
            ax_vars = self.parameter_vars['positional_axes'].get(ax, {})
            ax_cfg = axes.get(ax, {})
            # Pull current modulation values from UI vars if available
            mod_vars = ax_vars.get('modulation', {}) if isinstance(ax_vars, dict) else {}
            mod_default = self._default_modulation_for(ax)
            mod_cfg = ax_cfg.get('modulation', mod_default)
            try:
                mod_snapshot = {
                    'enabled': bool(mod_vars['enabled'].get()) if 'enabled' in mod_vars else mod_cfg.get('enabled', False),
                    'frequency_hz': float(mod_vars['frequency_hz'].get()) if 'frequency_hz' in mod_vars else mod_cfg.get('frequency_hz', 0.5),
                    'depth': float(mod_vars['depth'].get()) if 'depth' in mod_vars else mod_cfg.get('depth', 0.15),
                    'phase_deg': float(mod_vars['phase_deg'].get()) if 'phase_deg' in mod_vars else mod_cfg.get('phase_deg', mod_default['phase_deg']),
                    'phase_enabled': bool(mod_vars['phase_enabled'].get()) if 'phase_enabled' in mod_vars else mod_cfg.get('phase_enabled', True),
                }
            except (tk.TclError, ValueError):
                mod_snapshot = copy.deepcopy(mod_cfg)
            preset[ax] = {
                'enabled': ax_vars['enabled'].get() if 'enabled' in ax_vars else ax_cfg.get('enabled', False),
                'curve': copy.deepcopy(ax_cfg.get('curve', self._ma_blank_axis(ax)['curve'])),
                'signal_angle': ax_cfg.get('signal_angle', 0),
                'modulation': mod_snapshot,
            }
        config['motion_axis_presets']['presets'][active] = preset

    def _ma_apply_preset_to_config(self, preset):
        """Copy preset data into positional_axes config."""
        axes = self.config['positional_axes']
        if 'motion_axis_phase_shift' in preset:
            axes['motion_axis_phase_shift'] = copy.deepcopy(preset['motion_axis_phase_shift'])
        for ax in ['e1', 'e2', 'e3', 'e4']:
            if ax in preset:
                axes.setdefault(ax, {})
                axes[ax]['enabled'] = preset[ax].get('enabled', False)
                axes[ax]['curve'] = copy.deepcopy(preset[ax].get('curve', self._ma_blank_axis(ax)['curve']))
                axes[ax]['signal_angle'] = preset[ax].get('signal_angle', 0)
                axes[ax]['modulation'] = copy.deepcopy(
                    preset[ax].get('modulation', self._default_modulation_for(ax)))

    def _ma_apply_preset_to_ui(self):
        """Refresh UI vars and visualizations from positional_axes config."""
        axes = self.config['positional_axes']
        ps_vars = self.parameter_vars['positional_axes'].get('motion_axis_phase_shift', {})
        ma_ps = axes.get('motion_axis_phase_shift', {})
        if 'enabled' in ps_vars and 'enabled' in ma_ps:
            ps_vars['enabled'].set(ma_ps['enabled'])
        if 'delay_ms' in ps_vars and 'delay_ms' in ma_ps:
            ps_vars['delay_ms'].set(ma_ps['delay_ms'])
        for ax in ['e1', 'e2', 'e3', 'e4']:
            ax_cfg = axes.get(ax, {})
            ax_vars = self.parameter_vars['positional_axes'].get(ax, {})
            if 'enabled' in ax_vars and 'enabled' in ax_cfg:
                ax_vars['enabled'].set(ax_cfg['enabled'])
            mod_vars = ax_vars.get('modulation', {}) if isinstance(ax_vars, dict) else {}
            mod_cfg = ax_cfg.get('modulation', self._default_modulation_for(ax))
            mod_default = self._default_modulation_for(ax)
            if 'enabled' in mod_vars:
                mod_vars['enabled'].set(bool(mod_cfg.get('enabled', False)))
            if 'frequency_hz' in mod_vars:
                mod_vars['frequency_hz'].set(float(mod_cfg.get('frequency_hz', 0.5)))
            if 'depth' in mod_vars:
                mod_vars['depth'].set(float(mod_cfg.get('depth', 0.15)))
            if 'phase_deg' in mod_vars:
                mod_vars['phase_deg'].set(float(mod_cfg.get('phase_deg', mod_default['phase_deg'])))
            if 'phase_enabled' in mod_vars:
                mod_vars['phase_enabled'].set(bool(mod_cfg.get('phase_enabled', True)))
        self._update_curve_visualizations()
        for ax in ['e1', 'e2', 'e3', 'e4']:
            self._update_curve_name_display(ax)

    def _ma_refresh_combobox(self):
        """Refresh combobox values from the current presets dict."""
        if not hasattr(self, '_ma_combobox'):
            return
        names = list(self.config['motion_axis_presets']['presets'].keys())
        self._ma_combobox.configure(values=names)
        active = self.config['motion_axis_presets'].get('active', '')
        if active not in names and names:
            active = names[0]
            self.config['motion_axis_presets']['active'] = active
        self._ma_active_name.set(active)

    def _ma_on_select(self, *_):
        """Handle preset combobox selection."""
        new_name = self._ma_active_name.get()
        presets = self.config['motion_axis_presets']['presets']
        if new_name not in presets:
            return
        if new_name == self.config['motion_axis_presets'].get('active'):
            return
        self._ma_sync_to_store()
        self.config['motion_axis_presets']['active'] = new_name
        self._ma_apply_preset_to_config(presets[new_name])
        self._ma_apply_preset_to_ui()

    def _ma_new(self):
        """Create a new preset (blank or cloned from active)."""
        name = simpledialog.askstring("New Config", "Enter name for new config:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        presets = self.config['motion_axis_presets']['presets']
        if name in presets:
            messagebox.showerror("Error", f"Config '{name}' already exists.", parent=self.root)
            return

        # Dialog: blank or clone
        dialog = tk.Toplevel(self.root)
        dialog.title("New Config")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        choice = tk.StringVar(value='clone')
        ttk.Label(dialog, text=f"Create config '{name}':").pack(padx=20, pady=(15, 5))
        ttk.Radiobutton(dialog, text="Clone current config", variable=choice, value='clone').pack(anchor=tk.W, padx=30)
        ttk.Radiobutton(dialog, text="Create blank config",  variable=choice, value='blank').pack(anchor=tk.W, padx=30)

        result: list = [None]

        def _ok():
            result[0] = choice.get()
            dialog.destroy()

        def _cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="OK",     command=_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=_cancel).pack(side=tk.LEFT, padx=5)
        self.root.wait_window(dialog)

        if result[0] is None:
            return

        self._ma_sync_to_store()
        active = self.config['motion_axis_presets']['active']
        if result[0] == 'clone':
            presets[name] = copy.deepcopy(presets[active])
        else:
            presets[name] = self._ma_blank_preset()

        self.config['motion_axis_presets']['active'] = name
        self._ma_apply_preset_to_config(presets[name])
        self._ma_apply_preset_to_ui()
        self._ma_refresh_combobox()
        self._ma_active_name.set(name)

    def _ma_delete(self):
        """Delete the active preset."""
        presets = self.config['motion_axis_presets']['presets']
        if len(presets) <= 1:
            messagebox.showinfo("Cannot Delete", "Cannot delete the only config.", parent=self.root)
            return
        active = self.config['motion_axis_presets']['active']
        if not messagebox.askyesno("Delete Config", f"Delete config '{active}'?", parent=self.root):
            return
        del presets[active]
        new_active = next(iter(presets))
        self.config['motion_axis_presets']['active'] = new_active
        self._ma_apply_preset_to_config(presets[new_active])
        self._ma_apply_preset_to_ui()
        self._ma_refresh_combobox()
        self._ma_active_name.set(new_active)

    def _ma_rename(self):
        """Rename the active preset."""
        active = self.config['motion_axis_presets']['active']
        new_name = simpledialog.askstring("Rename Config", "New name:", initialvalue=active, parent=self.root)
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == active:
            return
        presets = self.config['motion_axis_presets']['presets']
        if new_name in presets:
            messagebox.showerror("Error", f"Config '{new_name}' already exists.", parent=self.root)
            return
        presets[new_name] = presets.pop(active)
        self.config['motion_axis_presets']['active'] = new_name
        self._ma_refresh_combobox()
        self._ma_active_name.set(new_name)

    def _ma_export(self):
        """Export all presets to a JSON file."""
        filepath = filedialog.asksaveasfilename(
            title="Export Motion Axis Configs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="motion_axis_configs.json",
            parent=self.root,
        )
        if not filepath:
            return
        self._ma_sync_to_store()
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config['motion_axis_presets'], f, indent=2)
            messagebox.showinfo("Export Complete", f"Configs exported to:\n{filepath}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}", parent=self.root)

    def _ma_import(self):
        """Import presets from a JSON file."""
        filepath = filedialog.askopenfilename(
            title="Import Motion Axis Configs",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.root,
        )
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'presets' not in data or not isinstance(data['presets'], dict):
                messagebox.showerror("Import Error", "Invalid file: missing 'presets' key.", parent=self.root)
                return
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read file:\n{e}", parent=self.root)
            return

        existing = self.config['motion_axis_presets']['presets']
        conflicts = [n for n in data['presets'] if n in existing]
        import_all = True
        if conflicts:
            msg = f"The following configs already exist:\n{', '.join(conflicts)}\n\nOverwrite them?"
            import_all = messagebox.askyesno("Import Conflict", msg, parent=self.root)

        imported = 0
        for name, preset in data['presets'].items():
            if import_all or name not in existing:
                existing[name] = copy.deepcopy(preset)
                imported += 1

        self._ma_refresh_combobox()
        messagebox.showinfo("Import Complete", f"Imported {imported} config(s).", parent=self.root)

    def setup_legacy_section(self):
        """Setup the legacy 1D to 2D conversion section within Motion Axis tab."""
        self.legacy_frame = ttk.LabelFrame(self.content_container, text="1D to 2D Conversion", padding="10")
        self.legacy_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.legacy_frame.columnconfigure(0, weight=1)
        self.legacy_frame.rowconfigure(0, weight=1)

        # Import ConversionTabs here to avoid circular import
        from ui.conversion_tabs import ConversionTabs

        # Create conversion tabs within the legacy section, passing the live
        # interpolation_interval variable so Points Per Second stays in sync.
        interp_var = self.parameter_vars.get('speed', {}).get('interpolation_interval')
        self.embedded_conversion_tabs = ConversionTabs(self.legacy_frame, self.config, interpolation_interval_var=interp_var)

    def setup_motion_axis_section_internal(self):
        """Setup the Motion Axis configuration section within Motion Axis tab."""
        self.motion_config_frame = ttk.LabelFrame(self.content_container, text="Motion Axis Configuration", padding="10")
        self.motion_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.motion_config_frame.columnconfigure(0, weight=1)

        row = 0

        # Import matplotlib for curve visualization
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import numpy as np
            self.matplotlib_available = True
        except ImportError:
            self.matplotlib_available = False
            # Show error message
            error_label = ttk.Label(self.motion_config_frame, 
                                  text="Matplotlib not available - install with: pip install matplotlib",
                                  foreground="red")
            error_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            row += 1

        # Axis enable/disable and curve visualization
        for axis_name in ['e1', 'e2', 'e3', 'e4']:
            axis_config = self.config['positional_axes'][axis_name]
            # Ensure modulation block exists with sensible per-axis defaults
            self._ensure_axis_modulation_defaults(axis_name)

            # Create frame for this axis
            axis_frame = ttk.LabelFrame(self.motion_config_frame, text=f"Axis {axis_name.upper()}", padding="5")
            axis_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            axis_frame.columnconfigure(1, weight=1)

            # Initialize axis variables
            self.parameter_vars['positional_axes'][axis_name] = {}

            # Enable checkbox
            enabled_var = tk.BooleanVar(value=axis_config['enabled'])
            self.parameter_vars['positional_axes'][axis_name]['enabled'] = enabled_var
            ttk.Checkbutton(axis_frame, text="Enabled", variable=enabled_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

            # Curve name display
            curve_name = axis_config['curve']['name']
            curve_label = ttk.Label(axis_frame, text=f"Curve: {curve_name}")
            curve_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)

            # Edit curve button
            edit_button = ttk.Button(axis_frame, text="Edit Curve",
                                   command=lambda a=axis_name: self._open_curve_editor(a))
            edit_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)

            # Modulation controls row
            mod_cfg = axis_config['modulation']
            default_phase = self._MODULATION_DEFAULT_PHASE.get(axis_name, 0.0)
            mod_row = ttk.Frame(axis_frame)
            mod_row.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(2, 4))

            mod_enabled_var = tk.BooleanVar(value=mod_cfg.get('enabled', False))
            mod_freq_var = tk.DoubleVar(value=mod_cfg.get('frequency_hz', 0.5))
            mod_depth_var = tk.DoubleVar(value=mod_cfg.get('depth', 0.15))
            mod_phase_var = tk.DoubleVar(value=mod_cfg.get('phase_deg', default_phase))
            mod_phase_enabled_var = tk.BooleanVar(
                value=mod_cfg.get('phase_enabled', True))
            self.parameter_vars['positional_axes'][axis_name]['modulation'] = {
                'enabled': mod_enabled_var,
                'frequency_hz': mod_freq_var,
                'depth': mod_depth_var,
                'phase_deg': mod_phase_var,
                'phase_enabled': mod_phase_enabled_var,
            }

            ttk.Checkbutton(
                mod_row, text="Modulation",
                variable=mod_enabled_var,
                command=lambda a=axis_name: self._on_modulation_changed(a),
            ).pack(side=tk.LEFT)
            ttk.Label(mod_row, text="Freq (Hz):").pack(side=tk.LEFT, padx=(10, 2))
            freq_entry = ttk.Entry(mod_row, textvariable=mod_freq_var, width=6)
            freq_entry.pack(side=tk.LEFT)
            freq_entry.bind('<FocusOut>', lambda e, a=axis_name: self._on_modulation_changed(a))
            freq_entry.bind('<Return>', lambda e, a=axis_name: self._on_modulation_changed(a))
            ttk.Label(mod_row, text="Depth:").pack(side=tk.LEFT, padx=(10, 2))
            depth_entry = ttk.Entry(mod_row, textvariable=mod_depth_var, width=6)
            depth_entry.pack(side=tk.LEFT)
            depth_entry.bind('<FocusOut>', lambda e, a=axis_name: self._on_modulation_changed(a))
            depth_entry.bind('<Return>', lambda e, a=axis_name: self._on_modulation_changed(a))
            ttk.Checkbutton(
                mod_row, text="Phase",
                variable=mod_phase_enabled_var,
                command=lambda a=axis_name: self._on_modulation_changed(a),
            ).pack(side=tk.LEFT, padx=(10, 0))
            phase_entry = ttk.Entry(mod_row, textvariable=mod_phase_var, width=6)
            phase_entry.pack(side=tk.LEFT, padx=(2, 0))
            ttk.Label(mod_row, text="\u00b0").pack(side=tk.LEFT)
            phase_entry.bind('<FocusOut>', lambda e, a=axis_name: self._on_modulation_changed(a))
            phase_entry.bind('<Return>', lambda e, a=axis_name: self._on_modulation_changed(a))

            # Curve visualization
            if self.matplotlib_available:
                curve_frame = ttk.Frame(axis_frame)
                curve_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
                
                # Create matplotlib figure for this curve
                fig = Figure(figsize=(5, 2), dpi=80)
                fig.patch.set_facecolor('white')
                ax = fig.add_subplot(111)
                
                # Generate curve data
                control_points = axis_config['curve']['control_points']
                x_vals, y_vals = self._generate_curve_data(control_points)
                
                # Plot the curve
                ax.plot(x_vals, y_vals, 'b-', linewidth=2)
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 100)
                ax.set_xlabel('Input Position', fontsize=8)
                ax.set_ylabel('Output', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                
                # Remove extra margins
                fig.tight_layout(pad=0.5)
                
                # Embed in tkinter
                canvas = FigureCanvasTkAgg(fig, curve_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                
                # Store reference for potential updates
                setattr(self, f'{axis_name}_curve_canvas', canvas)
                setattr(self, f'{axis_name}_curve_ax', ax)

            row += 1

        row += 1

        # Information section
        ttk.Label(self.motion_config_frame, text="Information:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1

        info_text = """Motion Axis Generation creates E1-E4 files using configurable response curves.
Each curve transforms the input position (0-100) to output position (0-100) based on the curve shape.
Enable/disable individual axes and edit curves to customize the motion pattern."""

        info_label = ttk.Label(self.motion_config_frame, text=info_text, wraplength=500, justify=tk.LEFT)
        info_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

    def _generate_curve_data(self, control_points):
        """Generate curve data from control points for visualization."""
        try:
            import numpy as np
            from processing.linear_mapping import apply_linear_response_curve
            
            # Generate input values from 0 to 100
            x_vals = np.linspace(0, 100, 101)  # 101 points for smooth curve
            y_vals = np.zeros_like(x_vals)
            
            # Apply linear interpolation using the same logic as the processing module
            for i, x in enumerate(x_vals):
                normalized_input = x / 100.0  # Convert to 0-1 range
                normalized_output = apply_linear_response_curve(normalized_input, control_points)
                y_vals[i] = normalized_output * 100.0  # Convert back to 0-100 range
            
            return x_vals, y_vals
            
        except Exception as e:
            # Fallback to simple linear curve if there's any error
            x_vals = np.array([0, 100])
            y_vals = np.array([0, 100])
            return x_vals, y_vals

    def _update_curve_visualizations(self):
        """Update all curve visualizations with current config data."""
        if not self.matplotlib_available:
            return
            
        try:
            for axis_name in ['e1', 'e2', 'e3', 'e4']:
                canvas_attr = f'{axis_name}_curve_canvas'
                ax_attr = f'{axis_name}_curve_ax'
                
                if hasattr(self, canvas_attr) and hasattr(self, ax_attr):
                    canvas = getattr(self, canvas_attr)
                    ax = getattr(self, ax_attr)
                    
                    # Get current curve config
                    axis_config = self.config['positional_axes'][axis_name]
                    control_points = axis_config['curve']['control_points']
                    
                    # Clear and redraw
                    ax.clear()
                    
                    # Generate new curve data
                    x_vals, y_vals = self._generate_curve_data(control_points)
                    
                    # Plot the curve
                    ax.plot(x_vals, y_vals, 'b-', linewidth=2)
                    ax.set_xlim(0, 100)
                    ax.set_ylim(0, 100)
                    ax.set_xlabel('Input Position', fontsize=8)
                    ax.set_ylabel('Output', fontsize=8)
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(labelsize=7)
                    
                    # Redraw canvas
                    canvas.draw()
                    
        except Exception as e:
            # Ignore visualization errors
            print(f"Warning: Could not update curve visualization: {e}")

    def _open_curve_editor(self, axis_name):
        """Open curve editor modal dialog."""
        try:
            from .curve_editor_dialog import edit_curve

            # Get current curve configuration
            current_curve = self.config['positional_axes'][axis_name]['curve']

            # Open the curve editor dialog
            result = edit_curve(self.root, axis_name, current_curve)

            if result is not None:
                # User saved changes - update configuration
                self.config['positional_axes'][axis_name]['curve'] = result

                # Update the curve visualization
                self._update_curve_visualizations()

                # Update the curve name display
                self._update_curve_name_display(axis_name)

        except ImportError as e:
            # Fallback if curve editor is not available
            import tkinter.messagebox as msgbox
            msgbox.showerror("Curve Editor Error", f"Curve editor is not available: {str(e)}")
        except Exception as e:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open curve editor: {str(e)}")

    def _update_curve_name_display(self, axis_name):
        """Update the curve name display for a specific axis."""
        try:
            # Find and update the curve name label for this axis
            curve_name = self.config['positional_axes'][axis_name]['curve']['name']

            # The curve name label was created in setup_motion_axis_section_internal
            # We need to find it and update its text
            for child in self.motion_config_frame.winfo_children():
                if isinstance(child, ttk.LabelFrame) and axis_name.upper() in child.cget('text'):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.Label) and 'Curve:' in subchild.cget('text'):
                            subchild.config(text=f"Curve: {curve_name}")
                            break
                    break
        except Exception as e:
            print(f"Error updating curve name display: {e}")

    def _browse_central_folder(self):
        """Open file dialog to browse for central restim folder."""
        # Get current directory if set
        current_dir = self.parameter_vars['file_management']['central_folder_path'].get()
        initial_dir = current_dir if current_dir else None

        # Open directory selection dialog
        selected_dir = filedialog.askdirectory(
            title="Select Central Restim Funscripts Folder",
            initialdir=initial_dir
        )

        # Update the variable if a directory was selected
        if selected_dir:
            self.parameter_vars['file_management']['central_folder_path'].set(selected_dir)

    def _update_mode_description(self):
        """Update the mode description text based on selected mode."""
        mode = self.parameter_vars['file_management']['mode'].get()

        if mode == 'central':
            self.mode_desc_label.config(text="Central mode:")
            self.mode_desc_text.config(text="All outputs are saved to the configured central restim funscripts folder")
            if hasattr(self, 'zip_output_checkbox'):
                self.zip_output_checkbox.state(['!disabled'])
        else:
            self.mode_desc_label.config(text="Local mode:")
            self.mode_desc_text.config(text="All outputs are saved to same folder where the source funscript is found")
            if hasattr(self, 'zip_output_checkbox'):
                self.zip_output_checkbox.state(['disabled'])

    def setup_advanced_tab(self):
        """Setup the Advanced parameters tab."""
        frame = self.advanced_frame
        self.parameter_vars['advanced'] = {}

        row = 0

        # Enable optional inversion files
        ttk.Label(frame, text="Optional Inversion Files:", font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))

        row += 1

        # Pulse Frequency Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_pulse_frequency_inversion'])
        self.parameter_vars['advanced']['enable_pulse_frequency_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Pulse Frequency Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Volume Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_volume_inversion'])
        self.parameter_vars['advanced']['enable_volume_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Volume Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        row += 1

        # Frequency Inversion
        var = tk.BooleanVar(value=self.config['advanced']['enable_frequency_inversion'])
        self.parameter_vars['advanced']['enable_frequency_inversion'] = var
        ttk.Checkbutton(frame, text="Enable Frequency Inversion", variable=var).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

    def setup_trochoid_tab(self):
        """Setup the Curve Quantization parameters tab.

        Snaps each input point to one of N levels derived from a parametric
        curve (hypotrochoid / epitrochoid / rose / lissajous / butterfly /
        superformula / custom). N points are sampled evenly in t over the
        family's natural period, projected to 1D (radius/x/y), normalized
        to [0, 1], and used as quantization levels.
        """
        from processing.trochoid_quantization import list_curve_families
        frame = self.trochoid_frame
        tq_cfg = self.config.get('trochoid_quantization', {})
        self.parameter_vars['trochoid_quantization'] = {}
        pv = self.parameter_vars['trochoid_quantization']

        # Per-family persistent param Vars. The family combobox swaps which
        # set is shown in the dynamic param frame; switching back retains
        # values the user typed for the previous family.
        self._trochoid_family_specs = list_curve_families()
        self._trochoid_param_vars = {}
        cfg_params_by_family = tq_cfg.get('params_by_family', {}) or {}
        for fam_name, spec in self._trochoid_family_specs.items():
            cfg_params = cfg_params_by_family.get(fam_name, {}) or {}
            self._trochoid_param_vars[fam_name] = {}
            for pname, default_val in spec['params'].items():
                cur_val = cfg_params.get(pname, default_val)
                if isinstance(default_val, str):
                    self._trochoid_param_vars[fam_name][pname] = tk.StringVar(
                        value=str(cur_val))
                else:
                    self._trochoid_param_vars[fam_name][pname] = tk.DoubleVar(
                        value=float(cur_val))

        row = 0

        ttk.Label(frame,
                  text="Quantize input positions to N levels derived from a "
                       "parametric curve.",
                  foreground='gray').grid(row=row, column=0, columnspan=3,
                                          sticky=tk.W, padx=5, pady=(5, 10))
        row += 1

        # Enable
        var = tk.BooleanVar(value=tq_cfg.get('enabled', False))
        pv['enabled'] = var
        ttk.Checkbutton(frame, text="Enable curve quantization", variable=var,
                        command=lambda: self._trochoid_changed()
                        ).grid(row=row, column=0, columnspan=3,
                               sticky=tk.W, padx=5, pady=(0, 8))
        row += 1

        # Curve family
        ttk.Label(frame, text="Curve family:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        # Backward-compat: if config has legacy curve_type but no family,
        # use it as the family.
        family_default = str(tq_cfg.get('family',
                                        tq_cfg.get('curve_type', 'hypo')))
        if family_default not in self._trochoid_family_specs:
            family_default = 'hypo'
        var = tk.StringVar(value=family_default)
        pv['family'] = var
        family_combo = ttk.Combobox(
            frame, textvariable=var,
            values=list(self._trochoid_family_specs.keys()),
            state='readonly', width=14)
        family_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        self._trochoid_family_desc_label = ttk.Label(
            frame, text=self._trochoid_family_specs[family_default]['description'],
            foreground='#555555', wraplength=280, justify=tk.LEFT)
        self._trochoid_family_desc_label.grid(row=row, column=2,
                                              sticky=(tk.W, tk.N), padx=5)
        family_combo.bind(
            '<<ComboboxSelected>>',
            lambda e: self._trochoid_on_family_change())
        row += 1

        # Number of points
        ttk.Label(frame, text="Number of points (N):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.IntVar(value=int(tq_cfg.get('n_points', 23)))
        pv['n_points'] = var
        spin = ttk.Spinbox(frame, from_=2, to=256, textvariable=var, width=8,
                           command=lambda: self._trochoid_changed())
        spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(frame, text="Quantization levels (e.g. 15, 17, 23)",
                  wraplength=280, justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        row += 1

        # Projection
        ttk.Label(frame, text="Projection:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.StringVar(value=str(tq_cfg.get('projection', 'radius')))
        pv['projection'] = var
        ttk.Combobox(frame, textvariable=var, values=['radius', 'y', 'x'],
                     state='readonly', width=10).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(frame,
                  text="How 2D curve points reduce to 1D levels",
                  wraplength=280, justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        row += 1

        # Deduplicate holds (output dedup option). Short label on the
        # checkbox itself, longer explanation as a wrapping label below
        # so the checkbox itself stays compact.
        var = tk.BooleanVar(value=bool(tq_cfg.get('deduplicate_holds', False)))
        pv['deduplicate_holds'] = var
        ttk.Checkbutton(
            frame,
            text="Deduplicate consecutive identical samples",
            variable=var, command=lambda: self._trochoid_changed()
        ).grid(row=row, column=0, columnspan=3,
               sticky=tk.W, padx=5, pady=(4, 0))
        row += 1
        ttk.Label(
            frame,
            text=("Removes redundant 'hold' samples; preserves first/last "
                  "of each plateau so device interpolation still holds the "
                  "position correctly."),
            foreground='#555555', wraplength=620, justify=tk.LEFT
        ).grid(row=row, column=0, columnspan=3,
               sticky=tk.W, padx=25, pady=(0, 8))
        row += 1

        # Dynamic family-specific parameter container
        self._trochoid_param_frame = ttk.LabelFrame(
            frame, text="Family parameters", padding=6)
        self._trochoid_param_frame.grid(row=row, column=0, columnspan=3,
                                        sticky=(tk.W, tk.E), padx=5, pady=4)
        self._trochoid_build_param_ui(family_default)
        row += 1

        # Refresh preview button
        ttk.Button(frame, text="Refresh Preview",
                   command=lambda: self._trochoid_changed()
                   ).grid(row=row, column=0, sticky=tk.W, padx=5, pady=(10, 4))
        row += 1

        # Preview canvas (matplotlib): trochoid + sampled points + level rug
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            preview_frame = ttk.LabelFrame(frame, text="Preview")
            preview_frame.grid(row=row, column=0, columnspan=3,
                               sticky=(tk.W, tk.E, tk.N, tk.S),
                               padx=5, pady=8)
            preview_frame.columnconfigure(0, weight=1)

            # Interactive controls row for the signal subplot
            ctl = ttk.Frame(preview_frame)
            ctl.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=4, pady=(2, 4))

            ttk.Label(ctl, text="Signal Zoom:").pack(side=tk.LEFT)
            self._trochoid_sig_zoom_var = tk.IntVar(value=100)
            zoom_combo = ttk.Combobox(
                ctl, textvariable=self._trochoid_sig_zoom_var,
                values=list(range(100, 8200, 200)), width=6)
            zoom_combo.pack(side=tk.LEFT, padx=(4, 0))
            ttk.Label(ctl, text="%").pack(side=tk.LEFT)
            zoom_combo.bind('<<ComboboxSelected>>',
                            lambda e: self._trochoid_redraw_signal())
            zoom_combo.bind('<Return>',
                            lambda e: self._trochoid_redraw_signal())

            ttk.Button(ctl, text="Reset View",
                       command=self._trochoid_reset_view
                       ).pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(ctl, text="Clear Playhead",
                       command=self._trochoid_clear_playhead
                       ).pack(side=tk.LEFT, padx=(4, 0))

            # Show as: Interpolated (matches device) / Step (shows snap edges)
            ttk.Label(ctl, text="Show as:").pack(side=tk.LEFT, padx=(12, 2))
            self._trochoid_render_var = tk.StringVar(value='interp')
            ttk.Radiobutton(ctl, text="Interpolated",
                            variable=self._trochoid_render_var,
                            value='interp',
                            command=self._trochoid_redraw_signal
                            ).pack(side=tk.LEFT)
            ttk.Radiobutton(ctl, text="Step",
                            variable=self._trochoid_render_var,
                            value='step',
                            command=self._trochoid_redraw_signal
                            ).pack(side=tk.LEFT)

            self._trochoid_playhead_label = ttk.Label(
                ctl, text="Playhead: —", foreground='#666666')
            self._trochoid_playhead_label.pack(side=tk.RIGHT, padx=(0, 4))

            # Scroll bar for the signal subplot (visible when zoomed > 100%)
            self._trochoid_sig_scroll_var = tk.DoubleVar(value=0.0)
            self._trochoid_sig_scrollbar = ttk.Scale(
                preview_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                variable=self._trochoid_sig_scroll_var,
                command=lambda v: self._trochoid_redraw_signal())
            self._trochoid_sig_scroll_visible = False

            fig = Figure(figsize=(7.5, 5.0), dpi=80)
            self._trochoid_fig = fig
            # Top row: curve geometry + level rug. Bottom row: interactive
            # signal before/after on a fragment of the loaded input.
            gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.2],
                                  hspace=0.45, wspace=0.3)
            self._trochoid_ax_curve = fig.add_subplot(gs[0, 0])
            self._trochoid_ax_levels = fig.add_subplot(gs[0, 1])
            self._trochoid_ax_signal = fig.add_subplot(gs[1, :])
            canvas = FigureCanvasTkAgg(fig, preview_frame)
            canvas.get_tk_widget().grid(
                row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._trochoid_canvas = canvas

            # Interactive state
            self._trochoid_cache = None
            self._trochoid_playhead_t = None
            self._trochoid_drag = None  # (start_xdata, start_scroll)

            # Hook matplotlib mouse events on the signal axes only
            canvas.mpl_connect('button_press_event',
                               self._trochoid_on_press)
            canvas.mpl_connect('button_release_event',
                               self._trochoid_on_release)
            canvas.mpl_connect('motion_notify_event',
                               self._trochoid_on_motion)
            canvas.mpl_connect('scroll_event',
                               self._trochoid_on_scroll)

            # Update on entry edits too. _trochoid_changed both refreshes
            # this preview and the main signal preview if it exists.
            for k in ('enabled', 'n_points', 'projection', 'family',
                      'deduplicate_holds'):
                if k in pv:
                    pv[k].trace_add('write',
                                    lambda *_a: self._trochoid_changed())
            # Per-family param vars too
            for fam, vars_ in self._trochoid_param_vars.items():
                for v in vars_.values():
                    v.trace_add('write',
                                lambda *_a: self._trochoid_changed())
            self._trochoid_update_preview()
        except Exception as e:
            ttk.Label(frame,
                      text=f"(Preview unavailable: {e})",
                      foreground='gray').grid(row=row, column=0, columnspan=3,
                                              sticky=tk.W, padx=5, pady=4)

    # ----- Curve-family parameter UI ----------------------------------------

    def _trochoid_active_params(self) -> dict:
        """Return the active family's params as a {name: value} dict."""
        pv = self.parameter_vars.get('trochoid_quantization', {})
        family = pv.get('family')
        if family is None:
            return {}
        family = family.get()
        out = {}
        spec = self._trochoid_family_specs.get(family)
        if not spec:
            return {}
        for pname, default_v in spec['params'].items():
            var = self._trochoid_param_vars.get(family, {}).get(pname)
            if var is None:
                out[pname] = default_v
                continue
            try:
                if isinstance(default_v, str):
                    out[pname] = str(var.get())
                else:
                    out[pname] = float(var.get())
            except (tk.TclError, ValueError):
                out[pname] = default_v
        return out

    def _trochoid_build_param_ui(self, family: str):
        """Rebuild the family-parameters frame for the given family."""
        if not hasattr(self, '_trochoid_param_frame'):
            return
        from ui.curve_family_params import build_family_param_grid
        build_family_param_grid(
            self._trochoid_param_frame, family,
            self._trochoid_family_specs, self._trochoid_param_vars)

    def _trochoid_on_family_change(self):
        """Combobox handler — rebuild param UI for the new family."""
        pv = self.parameter_vars.get('trochoid_quantization', {})
        family = pv.get('family').get() if 'family' in pv else 'hypo'
        self._trochoid_build_param_ui(family)
        if hasattr(self, '_trochoid_family_desc_label'):
            spec = self._trochoid_family_specs.get(family)
            if spec:
                self._trochoid_family_desc_label.config(
                    text=spec['description'])
        self._trochoid_changed()

    def _trochoid_sync_params_to_config(self, config: dict):
        """Write the per-family parameter Vars into config['trochoid_quantization']."""
        if not hasattr(self, '_trochoid_param_vars'):
            return
        section = config.setdefault('trochoid_quantization', {})
        target = section.setdefault('params_by_family', {})
        for fam, vars_ in self._trochoid_param_vars.items():
            spec = self._trochoid_family_specs.get(fam, {})
            defaults = spec.get('params', {})
            fam_target = target.setdefault(fam, {})
            for pname, var in vars_.items():
                default_v = defaults.get(pname, 0.0)
                try:
                    if isinstance(default_v, str):
                        fam_target[pname] = str(var.get())
                    else:
                        fam_target[pname] = float(var.get())
                except (tk.TclError, ValueError):
                    fam_target[pname] = default_v

    def _trochoid_load_params_from_config(self, config: dict):
        """Read per-family params from config back into the Vars + rebuild the UI."""
        if not hasattr(self, '_trochoid_param_vars'):
            return
        tq = config.get('trochoid_quantization', {}) or {}
        params_by_family = tq.get('params_by_family', {}) or {}
        for fam, vars_ in self._trochoid_param_vars.items():
            cfg_p = params_by_family.get(fam, {}) or {}
            spec = self._trochoid_family_specs.get(fam, {})
            defaults = spec.get('params', {})
            for pname, var in vars_.items():
                v = cfg_p.get(pname, defaults.get(pname, 0.0))
                try:
                    if isinstance(defaults.get(pname), str):
                        var.set(str(v))
                    else:
                        var.set(float(v))
                except (tk.TclError, ValueError):
                    pass
        # Rebuild the visible parameter pane for the currently selected family
        pv = self.parameter_vars.get('trochoid_quantization', {})
        if 'family' in pv:
            try:
                self._trochoid_build_param_ui(str(pv['family'].get()))
            except Exception:
                pass

    def _trochoid_changed(self):
        """Refresh curve tab preview AND main signal preview."""
        if getattr(self, '_loading_config', False):
            return
        self._trochoid_update_preview()
        # If the main parameter preview exists, refresh it so the input
        # subplot reflects the current quantization settings.
        if hasattr(self, '_preview_canvas_frame'):
            try:
                self._refresh_preview()
            except Exception as e:
                print(f"main preview refresh failed: {e}")

    def _trochoid_update_preview(self):
        """Recompute and redraw the curve preview (curve / levels / signal)."""
        if not hasattr(self, '_trochoid_canvas'):
            return
        try:
            import numpy as np
            from processing.trochoid_quantization import (
                generate_curve_levels, curve_xy, get_family_theta_max,
                deduplicate_holds as _dedup_holds)
            from funscript import Funscript

            pv = self.parameter_vars['trochoid_quantization']
            n = int(pv['n_points'].get())
            projection = str(pv['projection'].get())
            family = str(pv['family'].get())
            params = self._trochoid_active_params()
            dedup = bool(pv.get('deduplicate_holds',
                                tk.BooleanVar(value=False)).get())
            if n < 2:
                return

            # Update family description label
            if hasattr(self, '_trochoid_family_desc_label'):
                spec = self._trochoid_family_specs.get(family)
                if spec:
                    self._trochoid_family_desc_label.config(
                        text=spec['description'])

            # Dense curve for visualization
            theta_max = get_family_theta_max(family)
            theta_dense = np.linspace(0.0, theta_max, 1500)
            xc, yc = curve_xy(theta_dense, family, params)

            # Sampled N points
            theta_n = np.linspace(0.0, theta_max, n, endpoint=False)
            xn, yn = curve_xy(theta_n, family, params)

            ax1 = self._trochoid_ax_curve
            ax1.clear()
            finite = np.isfinite(xc) & np.isfinite(yc)
            ax1.plot(xc[finite], yc[finite], color='#4a90d9',
                     linewidth=0.8, alpha=0.7)
            finite_n = np.isfinite(xn) & np.isfinite(yn)
            ax1.scatter(xn[finite_n], yn[finite_n], s=14,
                        color='#d94a4a', zorder=3)
            ax1.set_aspect('equal', adjustable='datalim')
            ax1.set_title(f"{family.capitalize()} curve (N={n})", fontsize=9)
            ax1.tick_params(labelsize=7)
            ax1.grid(True, alpha=0.3)

            # Levels rug
            levels = generate_curve_levels(n, family, params, projection)
            ax2 = self._trochoid_ax_levels
            ax2.clear()
            for lv in levels:
                ax2.axhline(lv, color='#d94a4a', linewidth=0.8, alpha=0.85)
            ax2.set_ylim(-0.05, 1.05)
            ax2.set_xticks([])
            ax2.set_title(
                f"Quantization levels [{projection}] — {len(levels)} unique",
                fontsize=9)
            ax2.tick_params(labelsize=7)
            ax2.grid(True, axis='y', alpha=0.3)

            # Signal before/after panel — load a fragment of the input,
            # snap to levels, optionally dedup, cache for interactive redraws.
            t_seg, y_seg, src_label = self._trochoid_load_signal_fragment()
            if t_seg is not None and len(t_seg) > 0:
                idx = np.searchsorted(levels, y_seg)
                idx = np.clip(idx, 1, len(levels) - 1)
                left = levels[idx - 1]
                right = levels[idx]
                snapped = np.where(
                    np.abs(y_seg - left) <= np.abs(y_seg - right),
                    left, right)
                if dedup:
                    fs_q = Funscript(t_seg, snapped, metadata={})
                    fs_q = _dedup_holds(fs_q)
                    t_snap = np.asarray(fs_q.x, dtype=float)
                    y_snap_dedup = np.asarray(fs_q.y, dtype=float)
                else:
                    t_snap = t_seg
                    y_snap_dedup = snapped
                self._trochoid_cache = {
                    't': t_seg, 'y_raw': y_seg,
                    't_snapped': t_snap, 'y_snapped': y_snap_dedup,
                    'levels': levels, 'src_label': src_label,
                    't_start': float(t_seg[0]), 't_end': float(t_seg[-1]),
                    'dedup': dedup,
                    'sample_count_raw': int(len(snapped)),
                    'sample_count_dedup': int(len(y_snap_dedup)),
                }
            else:
                self._trochoid_cache = None
            self._trochoid_redraw_signal()

            self._trochoid_fig.tight_layout()
            self._trochoid_canvas.draw_idle()
        except Exception as e:
            print(f"Curve preview update failed: {e}")

    # ----- Interactive signal subplot ---------------------------------------

    def _trochoid_redraw_signal(self, *_a):
        """Redraw only the bottom signal subplot using current zoom/scroll/playhead."""
        if not hasattr(self, '_trochoid_canvas'):
            return
        ax = self._trochoid_ax_signal
        ax.clear()
        cache = self._trochoid_cache
        if not cache:
            ax.text(0.5, 0.5, "No input signal available",
                    ha='center', va='center', fontsize=9,
                    transform=ax.transAxes, color='#888888')
            ax.set_xticks([])
            ax.set_yticks([])
            self._trochoid_canvas.draw_idle()
            return

        t = cache['t']
        y_raw = cache['y_raw']
        # The snapped track may be deduplicated, in which case its t-array
        # differs from the raw signal's t-array. Pull both.
        t_snap = cache.get('t_snapped', cache['t'])
        y_snap = cache['y_snapped']
        levels = cache['levels']
        t_start = cache['t_start']
        t_end = cache['t_end']
        full_dur = max(1e-9, t_end - t_start)

        # Compute visible window from zoom + scroll
        zoom_pct = max(100, int(self._trochoid_sig_zoom_var.get()))
        visible_dur = full_dur / (zoom_pct / 100.0)
        scroll = float(self._trochoid_sig_scroll_var.get())
        scroll = min(1.0, max(0.0, scroll))
        view_start = t_start + scroll * (full_dur - visible_dur)
        view_end = view_start + visible_dur

        # Show/hide scrollbar when zoomed
        if zoom_pct > 100:
            if not self._trochoid_sig_scroll_visible:
                self._trochoid_sig_scrollbar.grid(
                    row=1, column=0, sticky=(tk.W, tk.E),
                    padx=4, pady=(0, 2))
                self._trochoid_sig_scroll_visible = True
        else:
            if self._trochoid_sig_scroll_visible:
                self._trochoid_sig_scrollbar.grid_remove()
                self._trochoid_sig_scroll_visible = False

        # Level reference lines
        for lv in levels:
            ax.axhline(lv * 100, color='#d94a4a',
                       linewidth=0.4, alpha=0.3, zorder=0)
        # Raw + snapped signals (full series; matplotlib will clip to xlim).
        # Default to "Interpolated" rendering — that's what the playback
        # device actually does between samples. "Step" rendering shows the
        # snap edges but is not how the device will reproduce the signal.
        render_mode = getattr(self, '_trochoid_render_var', None)
        render_mode = render_mode.get() if render_mode is not None else 'interp'
        ax.plot(t, y_raw * 100, color='#999999',
                linewidth=0.9, alpha=0.7, label='Raw', zorder=2)
        if render_mode == 'step':
            ax.step(t_snap, y_snap * 100, where='post',
                    color='#222222', linewidth=1.1,
                    label='Quantized (step)', zorder=3)
        else:
            ax.plot(t_snap, y_snap * 100,
                    color='#222222', linewidth=1.1,
                    label='Quantized (device)', zorder=3)
            # Mark the actual sample points for clarity
            ax.scatter(t_snap, y_snap * 100, s=10,
                       color='#222222', zorder=4)

        # Playhead
        if self._trochoid_playhead_t is not None:
            ph = float(self._trochoid_playhead_t)
            ax.axvline(ph, color='#1f8a3a', linewidth=1.2,
                       alpha=0.85, zorder=5)

        ax.set_ylabel('Position', fontsize=8)
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_ylim(-2, 102)
        ax.set_xlim(view_start, view_end)
        ax.legend(loc='upper right', fontsize=7, ncol=2, framealpha=0.7)
        dedup_note = ""
        if cache.get('dedup'):
            dedup_note = (f"  dedup {cache.get('sample_count_raw', 0)}"
                          f"\u2192{cache.get('sample_count_dedup', 0)}")
        ax.set_title(
            f"Signal before/after — {cache['src_label']}  "
            f"(zoom {zoom_pct}%, render={render_mode}{dedup_note}; "
            f"click=playhead, drag=pan, wheel=zoom)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.25)
        self._trochoid_canvas.draw_idle()

    def _trochoid_reset_view(self):
        self._trochoid_sig_zoom_var.set(100)
        self._trochoid_sig_scroll_var.set(0.0)
        self._trochoid_redraw_signal()

    def _trochoid_clear_playhead(self):
        self._trochoid_playhead_t = None
        if hasattr(self, '_trochoid_playhead_label'):
            self._trochoid_playhead_label.config(text="Playhead: —")
        self._trochoid_redraw_signal()

    def _trochoid_set_playhead(self, t_val):
        cache = self._trochoid_cache
        if not cache:
            return
        t_val = max(cache['t_start'], min(cache['t_end'], float(t_val)))
        self._trochoid_playhead_t = t_val
        if hasattr(self, '_trochoid_playhead_label'):
            import numpy as np
            i_raw = int(np.argmin(np.abs(cache['t'] - t_val)))
            raw_v = float(cache['y_raw'][i_raw]) * 100
            t_snap_arr = cache.get('t_snapped', cache['t'])
            i_snap = int(np.argmin(np.abs(t_snap_arr - t_val)))
            snap_v = float(cache['y_snapped'][i_snap]) * 100
            self._trochoid_playhead_label.config(
                text=f"Playhead: {t_val:.3f}s   "
                     f"raw={raw_v:.1f}  snap={snap_v:.1f}")
        self._trochoid_redraw_signal()

    def _trochoid_on_press(self, event):
        if event.inaxes is not getattr(self, '_trochoid_ax_signal', None):
            return
        # Left-click drags to pan; double-click sets playhead immediately.
        if event.button == 1:
            cache = self._trochoid_cache
            if not cache or event.xdata is None:
                return
            self._trochoid_drag = {
                'start_x': float(event.xdata),
                'start_scroll': float(self._trochoid_sig_scroll_var.get()),
                'moved': False,
            }
        elif event.button == 3:
            # Right-click clears playhead
            self._trochoid_clear_playhead()

    def _trochoid_on_motion(self, event):
        if event.inaxes is not getattr(self, '_trochoid_ax_signal', None):
            return
        drag = self._trochoid_drag
        if not drag or event.xdata is None:
            return
        cache = self._trochoid_cache
        if not cache:
            return
        full_dur = max(1e-9, cache['t_end'] - cache['t_start'])
        zoom_pct = max(100, int(self._trochoid_sig_zoom_var.get()))
        visible_dur = full_dur / (zoom_pct / 100.0)
        scrollable = max(1e-9, full_dur - visible_dur)
        # Convert pixel delta (in data units) to scroll delta. Dragging
        # right should move the view left (i.e. reveal earlier content),
        # so subtract the dx.
        dx = float(event.xdata) - drag['start_x']
        # When zoom == 100, scrollable is 0 — nothing to pan.
        if scrollable <= 0:
            return
        new_scroll = drag['start_scroll'] - (dx / scrollable)
        new_scroll = min(1.0, max(0.0, new_scroll))
        if abs(new_scroll - self._trochoid_sig_scroll_var.get()) > 1e-6:
            drag['moved'] = True
            self._trochoid_sig_scroll_var.set(new_scroll)
            self._trochoid_redraw_signal()

    def _trochoid_on_release(self, event):
        if event.inaxes is not getattr(self, '_trochoid_ax_signal', None):
            self._trochoid_drag = None
            return
        drag = self._trochoid_drag
        self._trochoid_drag = None
        # If left-click released without dragging, treat as playhead set.
        if event.button == 1 and drag is not None and not drag['moved']:
            if event.xdata is not None:
                self._trochoid_set_playhead(event.xdata)

    def _trochoid_on_scroll(self, event):
        if event.inaxes is not getattr(self, '_trochoid_ax_signal', None):
            return
        cache = self._trochoid_cache
        if not cache or event.xdata is None:
            return
        # Wheel up = zoom in, wheel down = zoom out. Anchor on cursor.
        zoom_pct = max(100, int(self._trochoid_sig_zoom_var.get()))
        factor = 1.25 if event.button == 'up' else 1 / 1.25
        new_zoom = int(round(zoom_pct * factor))
        new_zoom = max(100, min(8000, new_zoom))
        if new_zoom == zoom_pct:
            return
        full_dur = max(1e-9, cache['t_end'] - cache['t_start'])
        old_visible = full_dur / (zoom_pct / 100.0)
        new_visible = full_dur / (new_zoom / 100.0)
        # Anchor: keep event.xdata at the same fraction of the visible window.
        scroll = float(self._trochoid_sig_scroll_var.get())
        old_view_start = cache['t_start'] + scroll * (full_dur - old_visible)
        cursor_frac = (float(event.xdata) - old_view_start) / max(
            1e-9, old_visible)
        new_view_start = float(event.xdata) - cursor_frac * new_visible
        new_scrollable = max(1e-9, full_dur - new_visible)
        new_scroll = (new_view_start - cache['t_start']) / new_scrollable
        new_scroll = min(1.0, max(0.0, new_scroll))

        self._trochoid_sig_zoom_var.set(new_zoom)
        self._trochoid_sig_scroll_var.set(new_scroll)
        self._trochoid_redraw_signal()

    def _trochoid_load_signal_fragment(self, max_seconds: float = 10.0):
        """Load a short fragment of the input signal for the before/after view.

        Falls back to a synthetic sine wave if no input file is loaded.
        Returns (t, y, source_label) with t and y as numpy arrays in seconds
        and [0, 1] respectively.
        """
        import os
        import numpy as np
        try:
            from funscript import Funscript
        except ImportError:
            return None, None, ''

        mw = getattr(self, 'main_window', None)
        if mw and getattr(mw, 'input_files', None):
            input_path = mw.input_files[0]
            if os.path.isfile(input_path) and input_path.endswith('.funscript'):
                try:
                    fs = Funscript.from_file(input_path)
                    t = np.asarray(fs.x, dtype=float)
                    y = np.asarray(fs.y, dtype=float)
                    if len(t) > 1:
                        # Take the first max_seconds so the preview is
                        # responsive even on long scripts.
                        end_t = min(float(t[-1]), float(t[0]) + max_seconds)
                        mask = t <= end_t
                        return t[mask], y[mask], os.path.basename(input_path)
                except Exception:
                    pass

        # Synthetic fallback
        t = np.linspace(0.0, max_seconds, 400)
        y = 0.5 + 0.4 * np.sin(2.0 * np.pi * 0.5 * t)
        return t, y, "synthetic sine"

    # ====================================================================
    # Trochoid Spatial tab
    # ====================================================================

    def setup_trochoid_spatial_tab(self):
        """Setup the Trochoid Spatial parameters tab.

        Drives E1-E4 by parameterizing a 2D curve with the input position
        and projecting each (x, y) onto N electrode directions. This is
        an alternative to the response-curve-based motion-axis generation:
        when enabled in the processor pipeline, it replaces the curve-based
        E1-E4 generation entirely.
        """
        from processing.trochoid_quantization import list_curve_families
        frame = self.trochoid_spatial_frame
        ts_cfg = self.config.get('trochoid_spatial', {})
        self.parameter_vars['trochoid_spatial'] = {}
        pv = self.parameter_vars['trochoid_spatial']

        # Per-family persistent param Vars (shared schema with the
        # trochoid quantization tab).
        self._ts_family_specs = list_curve_families()
        self._ts_param_vars = {}
        cfg_params_by_family = ts_cfg.get('params_by_family', {}) or {}
        for fam_name, spec in self._ts_family_specs.items():
            cfg_params = cfg_params_by_family.get(fam_name, {}) or {}
            self._ts_param_vars[fam_name] = {}
            for pname, default_val in spec['params'].items():
                cur_val = cfg_params.get(pname, default_val)
                if isinstance(default_val, str):
                    self._ts_param_vars[fam_name][pname] = tk.StringVar(
                        value=str(cur_val))
                else:
                    self._ts_param_vars[fam_name][pname] = tk.DoubleVar(
                        value=float(cur_val))

        row = 0
        ttk.Label(frame,
                  text="Drive E1-E4 from a 2D curve. Each electrode "
                       "represents a compass direction; intensity comes "
                       "from how the curve point relates to that direction.",
                  foreground='gray', wraplength=620,
                  justify=tk.LEFT).grid(
            row=row, column=0, columnspan=3,
            sticky=tk.W, padx=5, pady=(5, 10))
        row += 1

        # Enable
        var = tk.BooleanVar(value=ts_cfg.get('enabled', False))
        pv['enabled'] = var
        ttk.Checkbutton(
            frame,
            text="Enable trochoid-spatial E1-E4 generation "
                 "(overrides the response-curve E1-E4 in Motion Axis 4P)",
            variable=var,
            command=lambda: self._ts_changed()
        ).grid(row=row, column=0, columnspan=3,
               sticky=tk.W, padx=5, pady=(0, 8))
        row += 1

        # Curve family
        ttk.Label(frame, text="Curve family:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        family_default = str(ts_cfg.get('family', 'hypo'))
        if family_default not in self._ts_family_specs:
            family_default = 'hypo'
        var = tk.StringVar(value=family_default)
        pv['family'] = var
        family_combo = ttk.Combobox(
            frame, textvariable=var,
            values=list(self._ts_family_specs.keys()),
            state='readonly', width=14)
        family_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        self._ts_family_desc_label = ttk.Label(
            frame,
            text=self._ts_family_specs[family_default]['description'],
            foreground='#555555', wraplength=320, justify=tk.LEFT)
        self._ts_family_desc_label.grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        family_combo.bind('<<ComboboxSelected>>',
                          lambda e: self._ts_on_family_change())
        row += 1

        # Mapping mode
        ttk.Label(frame, text="Mapping:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.StringVar(value=str(ts_cfg.get('mapping', 'directional')))
        pv['mapping'] = var
        ttk.Combobox(frame, textvariable=var,
                     values=['directional', 'distance', 'amplitude'],
                     state='readonly', width=14).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="directional = cosine of angle to electrode; "
                 "distance = proximity to electrode point on unit circle; "
                 "amplitude = directional × radius.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        row += 1

        # Sharpness
        ttk.Label(frame, text="Sharpness:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(ts_cfg.get('sharpness', 1.0)))
        pv['sharpness'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(frame,
                  text="Cosine exponent. 1=soft (broad activation), "
                       "4=sharp (only fires when path points right at it).",
                  foreground='#555555', wraplength=320,
                  justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "How selective each electrode is about the curve's "
            "direction/proximity. 1 = soft, all four electrodes "
            "contribute broadly; 4 = sharp, an electrode only fires "
            "when the curve is pointed almost exactly at it. Pairs "
            "well with 'directional' and 'amplitude' mapping modes.")
        row += 1

        # Cycles per unit
        ttk.Label(frame, text="Cycles per stroke:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(ts_cfg.get('cycles_per_unit', 1.0)))
        pv['cycles_per_unit'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(frame,
                  text="How many full curve traversals per 0→1 input "
                       "change. Higher = faster electrode flicker.",
                  foreground='#555555', wraplength=320,
                  justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "How many times the pen wraps around the full trochoid "
            "curve per 0→1 input sweep. 1 = one trace per stroke; "
            "5-10 = busy rotation, electrodes flicker fast; 0.25 = "
            "slow drift. Pair with dense multi-lobe families (rose, "
            "superformula) for buzz; simple curves + low cycles for "
            "slow sweep.")
        row += 1

        # Electrode angles (4 entries)
        ttk.Label(frame, text="Electrode angles (°):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        angles_frame = ttk.Frame(frame)
        angles_frame.grid(row=row, column=1, columnspan=2,
                          sticky=tk.W, padx=5, pady=4)
        defaults = ts_cfg.get('electrode_angles_deg',
                              [0.0, 90.0, 180.0, 270.0])
        self._ts_angle_vars = []
        for i, label in enumerate(['E1', 'E2', 'E3', 'E4']):
            ttk.Label(angles_frame, text=f"{label}:").grid(
                row=0, column=i * 2, padx=(0, 2))
            v = tk.DoubleVar(value=float(defaults[i] if i < len(defaults)
                                         else (i * 90.0)))
            self._ts_angle_vars.append(v)
            ttk.Entry(angles_frame, textvariable=v, width=6).grid(
                row=0, column=i * 2 + 1, padx=(0, 12))
        row += 1

        # Family parameters (dynamic)
        self._ts_param_frame = ttk.LabelFrame(
            frame, text="Family parameters", padding=6)
        self._ts_param_frame.grid(row=row, column=0, columnspan=3,
                                  sticky=(tk.W, tk.E), padx=5, pady=4)
        self._ts_build_param_ui(family_default)
        row += 1

        # Refresh preview
        ttk.Button(frame, text="Refresh Preview",
                   command=lambda: self._ts_changed()
                   ).grid(row=row, column=0, sticky=tk.W,
                          padx=5, pady=(10, 4))
        row += 1

        # Preview canvas
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            preview_frame = ttk.LabelFrame(frame, text="Preview")
            preview_frame.grid(row=row, column=0, columnspan=3,
                               sticky=(tk.W, tk.E, tk.N, tk.S),
                               padx=5, pady=8)
            preview_frame.columnconfigure(0, weight=1)

            fig = Figure(figsize=(8.0, 5.0), dpi=80)
            self._ts_fig = fig
            gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0],
                                  hspace=0.45, wspace=0.25)
            self._ts_ax_curve = fig.add_subplot(gs[0, 0])
            self._ts_ax_per_input = fig.add_subplot(gs[0, 1])
            self._ts_ax_e1234 = fig.add_subplot(gs[1, :])
            canvas = FigureCanvasTkAgg(fig, preview_frame)
            canvas.get_tk_widget().grid(
                row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._ts_canvas = canvas

            # Live updates on every change
            for k in ('enabled', 'family', 'mapping',
                      'sharpness', 'cycles_per_unit'):
                if k in pv:
                    pv[k].trace_add('write',
                                    lambda *_a: self._ts_changed())
            for v in self._ts_angle_vars:
                v.trace_add('write', lambda *_a: self._ts_changed())
            for fam, vars_ in self._ts_param_vars.items():
                for v in vars_.values():
                    v.trace_add('write', lambda *_a: self._ts_changed())
            self._ts_update_preview()
        except Exception as e:
            ttk.Label(frame, text=f"(Preview unavailable: {e})",
                      foreground='gray').grid(
                row=row, column=0, columnspan=3,
                sticky=tk.W, padx=5, pady=4)

    # ----- Trochoid Spatial helpers -----------------------------------------

    def _ts_active_params(self) -> dict:
        pv = self.parameter_vars.get('trochoid_spatial', {})
        family = pv.get('family')
        if family is None:
            return {}
        family = family.get()
        out = {}
        spec = self._ts_family_specs.get(family)
        if not spec:
            return {}
        for pname, default_v in spec['params'].items():
            var = self._ts_param_vars.get(family, {}).get(pname)
            if var is None:
                out[pname] = default_v
                continue
            try:
                if isinstance(default_v, str):
                    out[pname] = str(var.get())
                else:
                    out[pname] = float(var.get())
            except (tk.TclError, ValueError):
                out[pname] = default_v
        return out

    def _ts_active_angles(self):
        out = []
        for v in self._ts_angle_vars:
            try:
                out.append(float(v.get()))
            except (tk.TclError, ValueError):
                out.append(0.0)
        return tuple(out)

    def _ts_build_param_ui(self, family: str):
        """Rebuild the family-parameters frame for the given family."""
        if not hasattr(self, '_ts_param_frame'):
            return
        from ui.curve_family_params import build_family_param_grid
        build_family_param_grid(
            self._ts_param_frame, family,
            self._ts_family_specs, self._ts_param_vars)

    def _ts_on_family_change(self):
        pv = self.parameter_vars.get('trochoid_spatial', {})
        family = pv.get('family').get() if 'family' in pv else 'hypo'
        self._ts_build_param_ui(family)
        if hasattr(self, '_ts_family_desc_label'):
            spec = self._ts_family_specs.get(family)
            if spec:
                self._ts_family_desc_label.config(text=spec['description'])
        self._ts_changed()

    def _ts_changed(self):
        if getattr(self, '_loading_config', False):
            return
        self._ts_update_preview()
        # Refresh the main 4P Waveform Preview too so the override is
        # visible there as well.
        if hasattr(self, '_preview_canvas_frame'):
            try:
                self._refresh_preview()
            except Exception as e:
                print(f"main preview refresh failed: {e}")

    def _ts_update_preview(self):
        if not hasattr(self, '_ts_canvas'):
            return
        try:
            import numpy as np
            from processing.trochoid_quantization import (
                curve_xy, get_family_theta_max)
            from processing.trochoid_spatial import compute_spatial_intensities

            pv = self.parameter_vars['trochoid_spatial']
            family = str(pv['family'].get())
            mapping = str(pv['mapping'].get())
            try:
                sharpness = float(pv['sharpness'].get())
            except (tk.TclError, ValueError):
                sharpness = 1.0
            try:
                cpu = float(pv['cycles_per_unit'].get())
            except (tk.TclError, ValueError):
                cpu = 1.0
            params = self._ts_active_params()
            angles = self._ts_active_angles()

            # 1) Curve geometry (top-left): the path + electrode positions
            theta_max = get_family_theta_max(family)
            theta_dense = np.linspace(0.0, theta_max, 1500)
            xc, yc = curve_xy(theta_dense, family, params)
            finite = np.isfinite(xc) & np.isfinite(yc)
            xc, yc = xc[finite], yc[finite]
            rmax = float(np.max(np.sqrt(xc * xc + yc * yc))) if len(xc) else 1.0
            if rmax < 1e-12:
                rmax = 1.0
            ax1 = self._ts_ax_curve
            ax1.clear()
            ax1.plot(xc / rmax, yc / rmax, color='#4a90d9',
                     linewidth=0.8, alpha=0.7)
            # Electrode dots on unit circle
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            for i, ang in enumerate(angles):
                a = np.radians(ang)
                ax1.scatter([np.cos(a)], [np.sin(a)],
                            s=80, color=colors[i % 4], zorder=4,
                            edgecolors='black', linewidths=0.7)
                ax1.text(np.cos(a) * 1.15, np.sin(a) * 1.15,
                         f"E{i + 1}", ha='center', va='center',
                         fontsize=8, color=colors[i % 4],
                         fontweight='bold')
            # Unit circle reference
            tt = np.linspace(0, 2 * np.pi, 200)
            ax1.plot(np.cos(tt), np.sin(tt),
                     color='#bbbbbb', linewidth=0.5, linestyle='--')
            ax1.set_aspect('equal', adjustable='datalim')
            ax1.set_title(f"{family.capitalize()} curve + electrodes",
                          fontsize=9)
            ax1.tick_params(labelsize=7)
            ax1.grid(True, alpha=0.3)
            lim = 1.3
            ax1.set_xlim(-lim, lim)
            ax1.set_ylim(-lim, lim)

            # 2) Per-input intensity curves (top-right): for input
            # sweeping 0→1, plot each electrode's intensity.
            input_y = np.linspace(0.0, 1.0, 400)
            intensities = compute_spatial_intensities(
                input_y, family, params,
                electrode_angles_deg=angles,
                mapping=mapping, sharpness=sharpness,
                cycles_per_unit=cpu)
            ax2 = self._ts_ax_per_input
            ax2.clear()
            for i, key in enumerate(['e1', 'e2', 'e3', 'e4']):
                ax2.plot(input_y, intensities[key],
                         color=colors[i], linewidth=1.2,
                         label=key.upper())
            ax2.set_xlabel('Input position', fontsize=8)
            ax2.set_ylabel('Intensity', fontsize=8)
            ax2.set_title(
                f"Intensity vs input ({mapping}, sharp={sharpness:.1f}, "
                f"cycles={cpu:.1f})", fontsize=9)
            ax2.set_ylim(-0.05, 1.05)
            ax2.tick_params(labelsize=7)
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper right', fontsize=7, ncol=2,
                       framealpha=0.85)

            # 3) Time-domain preview using the loaded input fragment
            ax3 = self._ts_ax_e1234
            ax3.clear()
            t_seg, y_seg, src_label = self._trochoid_load_signal_fragment()
            if t_seg is not None and len(t_seg) > 0:
                e_seg = compute_spatial_intensities(
                    y_seg, family, params,
                    electrode_angles_deg=angles,
                    mapping=mapping, sharpness=sharpness,
                    cycles_per_unit=cpu)
                # Plot input as faint ref
                ax3.plot(t_seg, np.asarray(y_seg) * 100,
                         color='#888888', linewidth=0.7, alpha=0.5,
                         label='Input')
                for i, key in enumerate(['e1', 'e2', 'e3', 'e4']):
                    ax3.plot(t_seg, e_seg[key] * 100,
                             color=colors[i], linewidth=1.0,
                             label=key.upper(), alpha=0.9)
                ax3.set_ylabel('Position / Intensity', fontsize=8)
                ax3.set_xlabel('Time (s)', fontsize=8)
                ax3.set_ylim(-2, 102)
                ax3.set_xlim(float(t_seg[0]), float(t_seg[-1]))
                ax3.set_title(f"E1-E4 over time — {src_label}",
                              fontsize=9)
                ax3.legend(loc='upper right', fontsize=7, ncol=5,
                           framealpha=0.85)
            else:
                ax3.text(0.5, 0.5, "No input signal available",
                         ha='center', va='center', fontsize=9,
                         transform=ax3.transAxes, color='#888888')
                ax3.set_xticks([]); ax3.set_yticks([])
            ax3.tick_params(labelsize=7)
            ax3.grid(True, alpha=0.25)

            self._ts_fig.tight_layout()
            self._ts_canvas.draw_idle()
        except Exception as e:
            print(f"Trochoid spatial preview failed: {e}")

    def _ts_sync_params_to_config(self, config: dict):
        """Persist per-family params to config['trochoid_spatial']."""
        if not hasattr(self, '_ts_param_vars'):
            return
        section = config.setdefault('trochoid_spatial', {})
        target = section.setdefault('params_by_family', {})
        for fam, vars_ in self._ts_param_vars.items():
            spec = self._ts_family_specs.get(fam, {})
            defaults = spec.get('params', {})
            fam_target = target.setdefault(fam, {})
            for pname, var in vars_.items():
                default_v = defaults.get(pname, 0.0)
                try:
                    if isinstance(default_v, str):
                        fam_target[pname] = str(var.get())
                    else:
                        fam_target[pname] = float(var.get())
                except (tk.TclError, ValueError):
                    fam_target[pname] = default_v
        # Also persist electrode angles
        if hasattr(self, '_ts_angle_vars'):
            try:
                section['electrode_angles_deg'] = [
                    float(v.get()) for v in self._ts_angle_vars]
            except (tk.TclError, ValueError):
                pass

    def _ts_load_params_from_config(self, config: dict):
        """Pull per-family params + electrode angles from config back into Vars."""
        if not hasattr(self, '_ts_param_vars'):
            return
        ts = config.get('trochoid_spatial', {}) or {}
        params_by_family = ts.get('params_by_family', {}) or {}
        for fam, vars_ in self._ts_param_vars.items():
            cfg_p = params_by_family.get(fam, {}) or {}
            spec = self._ts_family_specs.get(fam, {})
            defaults = spec.get('params', {})
            for pname, var in vars_.items():
                v = cfg_p.get(pname, defaults.get(pname, 0.0))
                try:
                    if isinstance(defaults.get(pname), str):
                        var.set(str(v))
                    else:
                        var.set(float(v))
                except (tk.TclError, ValueError):
                    pass
        if hasattr(self, '_ts_angle_vars'):
            angles = ts.get('electrode_angles_deg',
                            [0.0, 90.0, 180.0, 270.0])
            for i, var in enumerate(self._ts_angle_vars):
                if i < len(angles):
                    try:
                        var.set(float(angles[i]))
                    except (tk.TclError, ValueError):
                        pass
        # Rebuild the visible parameter pane for the current family
        pv = self.parameter_vars.get('trochoid_spatial', {})
        if 'family' in pv:
            try:
                self._ts_build_param_ui(str(pv['family'].get()))
            except Exception:
                pass

    # ============================================================
    # Traveling Wave tab — linear/axial E1-E4 driver.
    # ============================================================

    def setup_traveling_wave_tab(self):
        """Setup the Traveling Wave parameters tab.

        Drives E1-E4 by running a crest along the shaft at its own
        clock. Each electrode fires when the crest passes its shaft
        position. When enabled, OVERRIDES both trochoid-spatial and
        the response-curve motion-axis E1-E4 generation.
        """
        frame = self.traveling_wave_frame
        tw_cfg = self.config.get('traveling_wave', {})
        self.parameter_vars['traveling_wave'] = {}
        pv = self.parameter_vars['traveling_wave']

        row = 0
        ttk.Label(
            frame,
            text="Drive E1-E4 by running a wave crest along the shaft. "
                 "The crest advances on its own clock; the input "
                 "modulates the envelope (and optionally the speed). "
                 "Each electrode fires when the crest passes its "
                 "shaft position.",
            foreground='gray', wraplength=620,
            justify=tk.LEFT).grid(
            row=row, column=0, columnspan=3,
            sticky=tk.W, padx=5, pady=(5, 10))
        row += 1

        # Enable
        var = tk.BooleanVar(value=bool(tw_cfg.get('enabled', False)))
        pv['enabled'] = var
        ttk.Checkbutton(
            frame,
            text="Enable traveling-wave E1-E4 generation "
                 "(overrides Trochoid Spatial and Motion Axis 4P curves)",
            variable=var,
            command=lambda: self._tw_changed()
        ).grid(row=row, column=0, columnspan=3,
               sticky=tk.W, padx=5, pady=(0, 8))
        row += 1

        # Direction
        ttk.Label(frame, text="Direction:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.StringVar(value=str(tw_cfg.get('direction', 'bounce')))
        pv['direction'] = var
        ttk.Combobox(
            frame, textvariable=var,
            values=['one_way_up', 'one_way_down',
                    'bounce', 'signal_direction',
                    'signal_position'],
            state='readonly', width=18).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="one_way_up/down = fixed direction; bounce = "
                 "back-and-forth; signal_direction = follows input's "
                 "up/down direction; signal_position = crest IS the "
                 "signal (tightest funscript sync, ignores speed/mod).",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        row += 1

        # Envelope mode
        ttk.Label(frame, text="Envelope:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.StringVar(value=str(tw_cfg.get('envelope_mode', 'input')))
        pv['envelope_mode'] = var
        ttk.Combobox(
            frame, textvariable=var,
            values=['constant', 'input', 'input_speed', 'abs_center'],
            state='readonly', width=18).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="constant = pure wave; input = amplitude tracks y; "
                 "input_speed = tracks |dy/dt|; abs_center = peaks "
                 "at extremes, silent at mid.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        row += 1

        # Wave speed
        ttk.Label(frame, text="Wave speed (Hz):").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(tw_cfg.get('wave_speed_hz', 1.0)))
        pv['wave_speed_hz'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="Full-shaft traversals per second.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "How fast the crest travels. 1 Hz = one base-to-tip trip "
            "per second. 3 Hz = three per second (buzzy). Ignored in "
            "signal_position direction (crest just follows the input).")
        row += 1

        # Wave width
        ttk.Label(frame, text="Wave width:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(tw_cfg.get('wave_width', 0.18)))
        pv['wave_width'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="Triangular kernel half-width in shaft units [0..1]. "
                 "Smaller = sharper peak.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "How wide the 'spotlight' is around the crest. 0.05 = "
            "very focused, only one electrode at a time. 0.25 = "
            "broad, multiple electrodes overlap. Combines with "
            "sharpness — smaller width + higher sharpness = tightest "
            "peak.")
        row += 1

        # Speed mod
        ttk.Label(frame, text="Speed modulation:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(tw_cfg.get('speed_mod', 0.0)))
        pv['speed_mod'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="How much input modulates speed. 0 = constant speed; "
                 "1.0 = half at y=0, 1.5x at y=1.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "Links the input signal to the wave's speed. 0 = wave "
            "speed is fixed. Positive = faster on high strokes, "
            "slower on low strokes. Negative = the reverse. Ignored "
            "in signal_position direction.")
        row += 1

        # Sharpness
        ttk.Label(frame, text="Sharpness:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(tw_cfg.get('sharpness', 1.0)))
        pv['sharpness'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="Exponent on the kernel. 1 = linear; higher = "
                 "narrower peak with softer skirts.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "Shapes the kernel's peak. 1 = linear triangle. Higher "
            "(2-4) narrows the peak and flattens the skirts — each "
            "electrode fires only when the crest is directly on it. "
            "Very high (5+) = almost step-function.")
        row += 1

        # Noise gate
        ttk.Label(frame, text="Noise gate:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.DoubleVar(value=float(tw_cfg.get('noise_gate', 0.10)))
        pv['noise_gate'] = var
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=4)
        ttk.Label(
            frame,
            text="Threshold [0, 0.5]. Values at/below the gate are "
                 "zeroed; the rest is rescaled so peaks still hit 1.0. "
                 "0.10 kills fuzz; 0.25 gives crisp on/off edges.",
            foreground='#555555', wraplength=320,
            justify=tk.LEFT).grid(
            row=row, column=2, sticky=(tk.W, tk.N), padx=5)
        self._create_entry_tooltip(entry,
            "Cleans the noise floor. Intensities below this value "
            "are forced to 0, then the remaining range is linearly "
            "rescaled to [0,1] so peaks still hit max. 0.0 disabled; "
            "0.10 kills skirt fuzz; 0.25 = crisp edges; 0.40+ = only "
            "direct-hit pulses survive.")
        row += 1

        # Exclusive mode
        ttk.Label(frame, text="Exclusive:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        var = tk.BooleanVar(value=bool(tw_cfg.get('exclusive', False)))
        pv['exclusive'] = var
        ttk.Checkbutton(
            frame, text="Only the strongest electrode fires "
                        "(winner-take-all)",
            variable=var,
            command=lambda: self._tw_changed()).grid(
            row=row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=4)
        row += 1

        # Electrode positions (4 entries)
        ttk.Label(frame, text="Electrode positions:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=4)
        pos_frame = ttk.Frame(frame)
        pos_frame.grid(row=row, column=1, columnspan=2,
                       sticky=tk.W, padx=5, pady=4)
        defaults = tw_cfg.get('electrode_positions',
                              [0.85, 0.65, 0.45, 0.25])
        self._tw_pos_vars = []
        for i, label in enumerate(['E1', 'E2', 'E3', 'E4']):
            ttk.Label(pos_frame, text=f"{label}:").grid(
                row=0, column=i * 2, padx=(0, 2))
            v = tk.DoubleVar(value=float(defaults[i] if i < len(defaults)
                                         else (0.85 - 0.20 * i)))
            self._tw_pos_vars.append(v)
            ttk.Entry(pos_frame, textvariable=v, width=6).grid(
                row=0, column=i * 2 + 1, padx=(0, 12))
        row += 1
        ttk.Label(
            frame,
            text="Positions along the shaft in [0, 1] "
                 "(0 = base, 1 = tip).",
            foreground='#555555', wraplength=620,
            justify=tk.LEFT).grid(
            row=row, column=0, columnspan=3,
            sticky=tk.W, padx=5, pady=(0, 4))
        row += 1

        # Refresh preview
        ttk.Button(frame, text="Refresh Preview",
                   command=lambda: self._tw_changed()
                   ).grid(row=row, column=0, sticky=tk.W,
                          padx=5, pady=(10, 4))
        row += 1

        # Preview canvas
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            preview_frame = ttk.LabelFrame(frame, text="Preview")
            preview_frame.grid(row=row, column=0, columnspan=3,
                               sticky=(tk.W, tk.E, tk.N, tk.S),
                               padx=5, pady=8)
            preview_frame.columnconfigure(0, weight=1)

            fig = Figure(figsize=(8.0, 5.0), dpi=80)
            self._tw_fig = fig
            gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.2],
                                  hspace=0.45)
            self._tw_ax_crest = fig.add_subplot(gs[0, 0])
            self._tw_ax_e1234 = fig.add_subplot(gs[1, 0])
            canvas = FigureCanvasTkAgg(fig, preview_frame)
            canvas.get_tk_widget().grid(
                row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._tw_canvas = canvas

            for k in ('enabled', 'direction', 'envelope_mode',
                      'wave_speed_hz', 'wave_width', 'speed_mod',
                      'sharpness'):
                if k in pv:
                    pv[k].trace_add('write',
                                    lambda *_a: self._tw_changed())
            for v in self._tw_pos_vars:
                v.trace_add('write', lambda *_a: self._tw_changed())
            self._tw_update_preview()
        except Exception as e:
            ttk.Label(frame, text=f"(Preview unavailable: {e})",
                      foreground='gray').grid(
                row=row, column=0, columnspan=3,
                sticky=tk.W, padx=5, pady=4)

    # ----- Traveling Wave helpers -----------------------------------

    def _tw_active_positions(self):
        out = []
        for v in self._tw_pos_vars:
            try:
                out.append(float(v.get()))
            except (tk.TclError, ValueError):
                out.append(0.5)
        return tuple(out)

    def _tw_changed(self):
        if getattr(self, '_loading_config', False):
            return
        self._tw_update_preview()
        if hasattr(self, '_preview_canvas_frame'):
            try:
                self._refresh_preview()
            except Exception as e:
                print(f"main preview refresh failed: {e}")

    def _tw_update_preview(self):
        if not hasattr(self, '_tw_canvas'):
            return
        try:
            import numpy as np
            from processing.traveling_wave import compute_wave_intensities
            from funscript import Funscript

            pv = self.parameter_vars['traveling_wave']
            direction = str(pv['direction'].get())
            envelope = str(pv['envelope_mode'].get())
            try:
                wave_speed = float(pv['wave_speed_hz'].get())
            except (tk.TclError, ValueError):
                wave_speed = 1.0
            try:
                wave_width = float(pv['wave_width'].get())
            except (tk.TclError, ValueError):
                wave_width = 0.18
            try:
                speed_mod = float(pv['speed_mod'].get())
            except (tk.TclError, ValueError):
                speed_mod = 0.0
            try:
                sharpness = float(pv['sharpness'].get())
            except (tk.TclError, ValueError):
                sharpness = 1.0
            try:
                noise_gate = float(pv.get('noise_gate').get()) \
                    if 'noise_gate' in pv else 0.0
            except (tk.TclError, ValueError):
                noise_gate = 0.0
            try:
                exclusive = bool(pv.get('exclusive').get()) \
                    if 'exclusive' in pv else False
            except (tk.TclError, ValueError):
                exclusive = False
            positions = self._tw_active_positions()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

            ax1 = self._tw_ax_crest
            ax2 = self._tw_ax_e1234
            ax1.clear()
            ax2.clear()

            t_seg, y_seg, src_label = self._trochoid_load_signal_fragment()
            if t_seg is None or len(t_seg) == 0:
                # Synthesize a demo 8-second sine sweep so the user can
                # still see the wave behavior before loading a signal.
                t_seg = np.linspace(0.0, 8.0, 400)
                y_seg = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t_seg)
                src_label = "(demo sine — load a file for real preview)"

            fs = Funscript(np.asarray(t_seg, dtype=float),
                           np.asarray(y_seg, dtype=float))
            intens = compute_wave_intensities(
                fs,
                electrode_positions=positions,
                wave_speed_hz=wave_speed,
                wave_width=wave_width,
                direction=direction,
                envelope_mode=envelope,
                speed_mod=speed_mod,
                sharpness=sharpness,
                noise_gate=noise_gate,
                exclusive=exclusive,
            )

            # Top: shaft crest position + electrode markers
            from processing.traveling_wave import _crest_positions
            crest = _crest_positions(
                np.asarray(t_seg, dtype=float),
                np.asarray(y_seg, dtype=float),
                wave_speed, direction, speed_mod)
            ax1.plot(t_seg, crest, color='#4a90d9',
                     linewidth=1.0, label='Crest pos')
            for i, p in enumerate(positions):
                ax1.axhline(p, color=colors[i], linewidth=0.6,
                            alpha=0.45)
                ax1.text(float(t_seg[-1]), p, f" E{i+1}",
                         color=colors[i], va='center',
                         fontsize=8, fontweight='bold')
            ax1.set_ylim(-0.05, 1.1)
            ax1.set_xlim(float(t_seg[0]), float(t_seg[-1]))
            ax1.set_ylabel('Shaft pos', fontsize=8)
            ax1.set_title(
                f"Crest trajectory — dir={direction}, "
                f"speed={wave_speed:.2f} Hz, width={wave_width:.2f}",
                fontsize=9)
            ax1.tick_params(labelsize=7)
            ax1.grid(True, alpha=0.3)

            # Bottom: input + per-electrode intensities
            ax2.plot(t_seg, np.asarray(y_seg) * 100,
                     color='#888888', linewidth=0.7, alpha=0.5,
                     label='Input')
            for i, key in enumerate(['e1', 'e2', 'e3', 'e4']):
                ax2.plot(t_seg, intens[key] * 100,
                         color=colors[i], linewidth=1.0,
                         label=key.upper(), alpha=0.9)
            ax2.set_ylabel('Position / Intensity', fontsize=8)
            ax2.set_xlabel('Time (s)', fontsize=8)
            ax2.set_ylim(-2, 102)
            ax2.set_xlim(float(t_seg[0]), float(t_seg[-1]))
            ax2.set_title(f"E1-E4 over time — {src_label}",
                          fontsize=9)
            ax2.tick_params(labelsize=7)
            ax2.grid(True, alpha=0.25)
            ax2.legend(loc='upper right', fontsize=7, ncol=5,
                       framealpha=0.85)

            self._tw_fig.tight_layout()
            self._tw_canvas.draw_idle()
        except Exception as e:
            print(f"Traveling wave preview failed: {e}")

    def _tw_sync_params_to_config(self, config: dict):
        """Persist traveling-wave positions to config (positions are not
        in the generic parameter_vars loop because they are a list)."""
        if not hasattr(self, '_tw_pos_vars'):
            return
        section = config.setdefault('traveling_wave', {})
        try:
            section['electrode_positions'] = [
                float(v.get()) for v in self._tw_pos_vars]
        except (tk.TclError, ValueError):
            pass

    def _tw_load_params_from_config(self, config: dict):
        if not hasattr(self, '_tw_pos_vars'):
            return
        tw = config.get('traveling_wave', {}) or {}
        positions = tw.get('electrode_positions',
                           [0.85, 0.65, 0.45, 0.25])
        for i, var in enumerate(self._tw_pos_vars):
            if i < len(positions):
                try:
                    var.set(float(positions[i]))
                except (tk.TclError, ValueError):
                    pass

    def setup_signal_gen_tab(self):
        """Setup the Signal Generator tab."""
        frame = self.signal_gen_frame

        row = 0

        ttk.Label(frame, text="Generate standalone signal funscripts from waveform parameters.",
                  foreground='gray').grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 10))
        row += 1

        # Waveform Type
        ttk.Label(frame, text="Waveform:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_waveform_var = tk.StringVar(value="sine")
        waveform_combo = ttk.Combobox(frame, textvariable=self._siggen_waveform_var,
                                       values=["sine", "square", "triangle", "sawtooth"],
                                       state='readonly', width=12)
        waveform_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # Frequency (Hz)
        ttk.Label(frame, text="Frequency (Hz):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_freq_var = tk.DoubleVar(value=8.0)
        ttk.Entry(frame, textvariable=self._siggen_freq_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="Cycles per second (e.g., 8 = 8 Hz)").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Amplitude
        ttk.Label(frame, text="Amplitude:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_amplitude_var = tk.DoubleVar(value=1.0)
        ttk.Entry(frame, textvariable=self._siggen_amplitude_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Peak-to-peak range, 1.0 = full 0-100").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Offset
        ttk.Label(frame, text="Offset:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_offset_var = tk.DoubleVar(value=0.5)
        ttk.Entry(frame, textvariable=self._siggen_offset_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="(0.0-1.0) Center point of the waveform").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Duration (seconds)
        ttk.Label(frame, text="Duration (sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_duration_var = tk.DoubleVar(value=60.0)
        ttk.Entry(frame, textvariable=self._siggen_duration_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="Length of generated signal in seconds").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Sample Rate (points per second)
        ttk.Label(frame, text="Sample Rate (pts/sec):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_samplerate_var = tk.IntVar(value=100)
        ttk.Entry(frame, textvariable=self._siggen_samplerate_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="Points per second (min: 2x frequency for accuracy)").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # Phase (degrees)
        ttk.Label(frame, text="Phase (\u00b0):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self._siggen_phase_var = tk.DoubleVar(value=0.0)
        ttk.Entry(frame, textvariable=self._siggen_phase_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text="(0-360) Starting phase offset in degrees").grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3,
                                                       sticky=(tk.W, tk.E), padx=5, pady=10)
        row += 1

        # Generate button
        ttk.Button(frame, text="Generate Signal", command=self._generate_signal).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1

        # Preview area
        self._siggen_preview_frame = ttk.Frame(frame)
        self._siggen_preview_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self._siggen_preview_frame.columnconfigure(0, weight=1)

    def _generate_signal(self):
        """Generate a signal funscript from the current parameters."""
        import math
        import numpy as np
        from funscript import Funscript
        from tkinter import filedialog, messagebox

        waveform = self._siggen_waveform_var.get()
        freq = self._siggen_freq_var.get()
        amplitude = max(0.0, min(1.0, self._siggen_amplitude_var.get()))
        offset = max(0.0, min(1.0, self._siggen_offset_var.get()))
        duration = max(0.1, self._siggen_duration_var.get())
        sample_rate = max(1, self._siggen_samplerate_var.get())
        phase_deg = self._siggen_phase_var.get()
        phase_rad = math.radians(phase_deg)

        if freq <= 0:
            messagebox.showerror("Error", "Frequency must be greater than 0")
            return

        # Generate time array
        num_points = int(duration * sample_rate)
        t = np.linspace(0, duration, num_points, endpoint=False)

        # Generate waveform
        phase = 2 * np.pi * freq * t + phase_rad
        if waveform == "sine":
            y = np.sin(phase)
        elif waveform == "square":
            y = np.sign(np.sin(phase))
        elif waveform == "triangle":
            y = 2 * np.abs(2 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))) - 1
        elif waveform == "sawtooth":
            y = 2 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))
        else:
            y = np.sin(phase)

        # Scale: y is -1 to 1, map to offset ± amplitude/2, clamp to 0-1
        y = np.clip(offset + y * (amplitude / 2.0), 0.0, 1.0)

        # Preview
        self._siggen_preview(t, y, waveform, freq)

        # Save
        path = filedialog.asksaveasfilename(
            title="Save Generated Signal",
            defaultextension=".funscript",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")],
            initialfile=f"signal_{waveform}_{freq}hz.funscript"
        )
        if not path:
            return

        fs = Funscript(t, y)
        from version import __version__, __app_name__, __url__
        fs.metadata = {
            "creator": __app_name__,
            "title": f"Generated {waveform} {freq}Hz",
            "description": f"Generated by {__app_name__} v{__version__} - {waveform} signal at {freq}Hz",
            "url": __url__,
            "metadata": {
                "generator": __app_name__,
                "waveform": waveform,
                "frequency_hz": freq,
                "amplitude": amplitude,
                "offset": offset,
                "duration_sec": duration,
                "phase_deg": phase_deg,
            }
        }
        fs.save_to_path(path)
        messagebox.showinfo("Signal Generated", f"Saved: {path}\n\n"
                            f"{waveform} at {freq} Hz\n"
                            f"Duration: {duration}s, {num_points} points")

    def _siggen_preview(self, t, y, waveform, freq):
        """Show a preview of the generated signal."""
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            return

        for child in self._siggen_preview_frame.winfo_children():
            child.destroy()

        # Show first 2 seconds or full duration if shorter
        preview_end = min(t[-1], 2.0)
        mask = t <= preview_end

        fig = Figure(figsize=(7, 2.5), dpi=85)
        fig.patch.set_facecolor('#f0f0f0')
        ax = fig.add_subplot(111)
        ax.plot(t[mask], y[mask] * 100, color='#1f77b4', linewidth=1.2)
        ax.fill_between(t[mask], 0, y[mask] * 100, alpha=0.15, color='#1f77b4')
        ax.set_ylim(0, 100)
        ax.set_xlim(0, preview_end)
        ax.set_xlabel('Time (seconds)', fontsize=8)
        ax.set_ylabel('Position (0-100)', fontsize=8)
        ax.set_title(f'{waveform.capitalize()} — {freq} Hz (first {preview_end:.1f}s)', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self._siggen_preview_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E))

    def update_config(self, config: Dict[str, Any]):
        """Update configuration dictionary with current UI values."""
        for section, variables in self.parameter_vars.items():
            if section not in config:
                config[section] = {}
            
            if section == 'positional_axes':
                # Handle nested positional_axes structure
                for param, var in variables.items():
                    if param in ('generate_legacy', 'generate_motion_axis'):
                        config[section][param] = var.get()
                    elif param == 'physical_model':
                        # Flat nested dict of BooleanVar/DoubleVar/StringVar
                        pm_target = config[section].setdefault('physical_model', {})
                        for pm_key, pm_var in var.items():
                            try:
                                pm_target[pm_key] = pm_var.get()
                            except (tk.TclError, ValueError):
                                pass
                    elif param in ('phase_shift', 'motion_axis_phase_shift'):
                        if param not in config[section]:
                            config[section][param] = {}
                        for phase_param, phase_var in var.items():
                            config[section][param][phase_param] = phase_var.get()
                    elif param in ['e1', 'e2', 'e3', 'e4']:
                        # Handle axis-specific parameters
                        if param not in config[section]:
                            config[section][param] = {}
                        for axis_param, axis_var in var.items():
                            if axis_param == 'enabled':
                                config[section][param][axis_param] = axis_var.get()
                            elif axis_param == 'modulation' and isinstance(axis_var, dict):
                                mod_default = self._default_modulation_for(param)
                                mod_target = config[section][param].setdefault(
                                    'modulation', mod_default)
                                try:
                                    mod_target['enabled'] = bool(axis_var['enabled'].get())
                                    mod_target['frequency_hz'] = max(0.0, float(axis_var['frequency_hz'].get()))
                                    mod_target['depth'] = max(0.0, min(1.0, float(axis_var['depth'].get())))
                                    if 'phase_deg' in axis_var:
                                        mod_target['phase_deg'] = float(axis_var['phase_deg'].get())
                                    if 'phase_enabled' in axis_var:
                                        mod_target['phase_enabled'] = bool(axis_var['phase_enabled'].get())
                                except (tk.TclError, ValueError, KeyError):
                                    pass
                                mod_target.setdefault('phase_deg', mod_default['phase_deg'])
                                mod_target.setdefault('phase_enabled', mod_default['phase_enabled'])
                # Derive mode for backward compat with processor
                if config[section].get('generate_motion_axis', False):
                    config[section]['mode'] = 'motion_axis'
                elif config[section].get('generate_legacy', False):
                    config[section]['mode'] = 'legacy'
                # Sync active preset into the preset store
                if 'motion_axis_presets' in config and hasattr(self, '_ma_active_name'):
                    self._ma_sync_to_store(config)
            else:
                # Handle regular flat structure
                for param, var in variables.items():
                    if isinstance(var, dict):
                        # Nested dict of tk vars (e.g. savgol_options)
                        target = config[section].setdefault(param, {})
                        for k, v in var.items():
                            try:
                                target[k] = v.get()
                            except (tk.TclError, ValueError):
                                pass
                    else:
                        config[section][param] = var.get()

        # Update custom combine ratio controls
        for control_name, control in self.combine_ratio_controls.items():
            control._update_percentage_display()

        # Sync trochoid per-family params (not handled by the generic loop)
        self._trochoid_sync_params_to_config(config)
        if hasattr(self, '_ts_sync_params_to_config'):
            self._ts_sync_params_to_config(config)
        if hasattr(self, '_tw_sync_params_to_config'):
            self._tw_sync_params_to_config(config)

        # Update embedded conversion tabs if they exist
        if hasattr(self, 'embedded_conversion_tabs'):
            try:
                # Update 1D to 2D conversion settings from embedded conversion tabs
                basic_config = self.embedded_conversion_tabs.get_basic_config()
                config['alpha_beta_generation']['algorithm'] = basic_config['algorithm']
                config['alpha_beta_generation']['points_per_second'] = basic_config['points_per_second']
                config['alpha_beta_generation']['min_distance_from_center'] = round(basic_config['min_distance_from_center'], 1)
                config['alpha_beta_generation']['speed_threshold_percent'] = basic_config['speed_threshold_percent']
                config['alpha_beta_generation']['direction_change_probability'] = round(basic_config['direction_change_probability'], 2)

                # Update prostate conversion settings
                prostate_config = self.embedded_conversion_tabs.get_prostate_config()
                if 'prostate_generation' not in config:
                    config['prostate_generation'] = {}
                config['prostate_generation']['generate_prostate_files'] = prostate_config['generate_prostate_files']
                config['prostate_generation']['generate_from_inverted'] = prostate_config['generate_from_inverted']
                config['prostate_generation']['algorithm'] = prostate_config['algorithm']
                config['prostate_generation']['points_per_second'] = prostate_config['points_per_second']
                config['prostate_generation']['min_distance_from_center'] = round(prostate_config['min_distance_from_center'], 1)
            except Exception as e:
                # Log errors if conversion tabs not properly initialized
                print(f"Error updating conversion tabs config: {e}")
                import traceback
                traceback.print_exc()

    def update_display(self, config: Dict[str, Any]):
        """Update UI display with configuration values.

        This runs in "batch mode": preview-refresh callbacks fired by
        tk-var traces bail out while `_loading_config` is True, so a
        single config swap doesn't trigger dozens of matplotlib redraws
        (one per var). A single refresh pass runs at the end. Cuts a
        whole-config variant switch from ~5 s to ~0.1 s.
        """
        self._loading_config = True
        try:
            self._update_display_impl(config)
        finally:
            self._loading_config = False
            # One consolidated refresh pass for all active previews.
            for name in ('_refresh_preview', '_ts_update_preview',
                         '_trochoid_update_preview', '_tw_update_preview'):
                fn = getattr(self, name, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception as e:
                        print(f"preview {name} failed after load: {e}")

    def _update_display_impl(self, config: Dict[str, Any]):
        """Core tk-var update loop. Don't call directly — use update_display()."""
        self.config = config
        # Migrate / refresh preset selector when loading a new config
        self._ma_presets_ensure()
        if hasattr(self, '_ma_combobox'):
            self._ma_refresh_combobox()
        for section, variables in self.parameter_vars.items():
            if section in config:
                if section == 'positional_axes':
                    # Handle nested positional_axes structure
                    for param, var in variables.items():
                        if param in ('generate_legacy', 'generate_motion_axis') and param in config[section]:
                            var.set(config[section][param])
                        elif param == 'physical_model' and param in config[section]:
                            pm_cfg = config[section][param]
                            for pm_key, pm_var in var.items():
                                if pm_key in pm_cfg:
                                    try:
                                        pm_var.set(pm_cfg[pm_key])
                                    except (tk.TclError, ValueError):
                                        pass
                        elif param in ('phase_shift', 'motion_axis_phase_shift') and param in config[section]:
                            phase_config = config[section][param]
                            for phase_param, phase_var in var.items():
                                if phase_param in phase_config:
                                    phase_var.set(phase_config[phase_param])
                        elif param in ['e1', 'e2', 'e3', 'e4'] and param in config[section]:
                            axis_config = config[section][param]
                            mod_cfg = axis_config.get(
                                'modulation', self._default_modulation_for(param))
                            for axis_param, axis_var in var.items():
                                if axis_param == 'enabled' and axis_param in axis_config:
                                    axis_var.set(axis_config[axis_param])
                                elif axis_param == 'modulation' and isinstance(axis_var, dict):
                                    mod_default = self._default_modulation_for(param)
                                    if 'enabled' in axis_var:
                                        axis_var['enabled'].set(bool(mod_cfg.get('enabled', False)))
                                    if 'frequency_hz' in axis_var:
                                        axis_var['frequency_hz'].set(float(mod_cfg.get('frequency_hz', 0.5)))
                                    if 'depth' in axis_var:
                                        axis_var['depth'].set(float(mod_cfg.get('depth', 0.15)))
                                    if 'phase_deg' in axis_var:
                                        axis_var['phase_deg'].set(float(mod_cfg.get('phase_deg', mod_default['phase_deg'])))
                                    if 'phase_enabled' in axis_var:
                                        axis_var['phase_enabled'].set(bool(mod_cfg.get('phase_enabled', True)))
                else:
                    # Handle regular flat structure
                    for param, var in variables.items():
                        if param in config[section]:
                            if isinstance(var, dict):
                                # Nested dict of tk vars (e.g. savgol_options)
                                nested_cfg = config[section][param]
                                if isinstance(nested_cfg, dict):
                                    for k, v in var.items():
                                        if k in nested_cfg:
                                            try:
                                                v.set(nested_cfg[k])
                                            except (tk.TclError, ValueError):
                                                pass
                            else:
                                var.set(config[section][param])

        # Update custom combine ratio controls display
        for control_name, control in self.combine_ratio_controls.items():
            control._update_percentage_display()

        # Update ramp display if it exists
        if hasattr(self, 'ramp_value_label'):
            self._update_ramp_display()

        # Update embedded conversion tabs if they exist
        if hasattr(self, 'embedded_conversion_tabs'):
            try:
                # The conversion tabs will update themselves based on the config
                # when they access the config values
                pass
            except Exception:
                # Ignore errors if conversion tabs not properly initialized
                pass

        # Update Motion Axis display after config changes
        if hasattr(self, '_update_motion_axis_display'):
            self._update_motion_axis_display()

        # Update curve visualizations if they exist
        self._update_curve_visualizations()

        # Refresh trochoid per-family param Vars from config and rebuild
        # the active family's parameter UI so loaded values appear.
        self._trochoid_load_params_from_config(config)
        if hasattr(self, '_ts_load_params_from_config'):
            self._ts_load_params_from_config(config)
        if hasattr(self, '_tw_load_params_from_config'):
            self._tw_load_params_from_config(config)

    def _update_ramp_display(self, value=None):
        """Update the ramp value display with current value and per-minute calculation."""
        try:
            # Get current ramp value
            ramp_per_hour = int(self.parameter_vars['volume']['ramp_percent_per_hour'].get())

            # Calculate per-minute value
            ramp_per_minute = round(ramp_per_hour / 60.0, 2)

            # Update label text
            display_text = f"{ramp_per_hour}% per hour ({ramp_per_minute}% per minute)"
            self.ramp_value_label.config(text=display_text)
        except (KeyError, ValueError, AttributeError):
            # Handle case where variables aren't initialized yet
            pass