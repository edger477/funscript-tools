"""
Animated visualization of 2D electrode trajectory + E1-E4 electrode
intensity bars. Launched as a popup window from the main UI.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import math
import os
import warnings


class AnimationViewer(tk.Toplevel):
    """Popup window: animated 2D trajectory (alpha/beta) + E1-E4 bars."""

    # Animation timing
    _FPS = 20
    _TRAIL_LENGTH = 40  # number of past points to show as trail

    # Colors
    _TRAJECTORY_COLOR = '#aaaaaa'
    _DOT_COLOR = '#e53935'
    _TRAIL_COLOR = '#1976D2'
    _BAR_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    _BAR_LABELS = ['E1', 'E2', 'E3', 'E4']

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.title("Animation Viewer")
        self.geometry("950x800")
        self.minsize(700, 550)
        self.main_window = main_window
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._playing = False
        self._after_id = None
        self._frame_index = 0
        self._data = None
        self._playback_speed = 1.0

        self._build_ui()
        self._prepare_and_draw()

    # ── Data Preparation ─────────────────────────────────────────────

    def _prepare_data(self):
        """Compute alpha/beta trajectory and E1-E4 intensities."""
        from funscript import Funscript
        from processing.speed_processing import convert_to_speed
        from processing.funscript_1d_to_2d import generate_alpha_beta_from_main
        from processing.linear_mapping import apply_linear_response_curve

        config = self.main_window.current_config

        # Load or synthesize main funscript
        main_fs = None
        source_label = "Demo mode (synthetic sine wave)"
        if hasattr(self.main_window, 'input_files') and self.main_window.input_files:
            path = self.main_window.input_files[0]
            if os.path.isfile(path) and path.endswith('.funscript'):
                try:
                    main_fs = Funscript.from_file(path)
                    source_label = os.path.basename(path)
                except Exception:
                    pass

        if main_fs is None:
            t = np.linspace(0, 10.0, 500)
            y = 0.5 + 0.4 * np.sin(2 * np.pi * 0.5 * t)
            main_fs = Funscript(t, y)

        # Optional trochoid quantization. Toggled by the viewer's own
        # checkbox (defaults to whatever the global config says, but the
        # user can flip it here for A/B without touching the Trochoid tab).
        # When applied, this snaps the input signal to N curve-derived
        # levels BEFORE speed/alpha/beta/E1-E4 are derived — same order
        # the processor uses, so the trajectory and bars in this viewer
        # match what the processor will produce.
        tq_cfg = config.get('trochoid_quantization', {}) or {}
        apply_tq = (hasattr(self, '_tq_apply_var')
                    and bool(self._tq_apply_var.get()))
        if apply_tq:
            try:
                from processing.trochoid_quantization import (
                    quantize_to_curve, deduplicate_holds,
                    FAMILY_DEFAULTS as _FD)
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
                        _FD.get(family, {}).get('params', {}))
                main_fs = quantize_to_curve(
                    main_fs, int(tq_cfg.get('n_points', 23)),
                    family, family_params,
                    str(tq_cfg.get('projection', 'radius')))
                if tq_cfg.get('deduplicate_holds', False):
                    main_fs = deduplicate_holds(main_fs)
                source_label = (f"{source_label}  "
                                f"[trochoid: {family}, "
                                f"N={int(tq_cfg.get('n_points', 23))}]")
            except (ValueError, TypeError) as e:
                print(f"[viewer] trochoid quantization skipped: {e}")

        # Generate speed
        speed_window = float(config.get('general', {}).get('speed_window_size', 2))
        interp_interval = float(config.get('speed', {}).get('interpolation_interval', 0.02))
        speed_method = config.get('speed', {}).get('method', 'rolling_average')
        savgol_opts = config.get('speed', {}).get('savgol_options', {})
        speed_fs = convert_to_speed(main_fs, speed_window, interp_interval,
                                    method=speed_method, savgol_options=savgol_opts)

        # Generate alpha/beta
        ab_config = config.get('alpha_beta_generation', {})
        pps = ab_config.get('points_per_second', 25)
        algorithm = ab_config.get('algorithm', 'circular')
        min_dist = ab_config.get('min_distance_from_center', 0.1)
        speed_thresh = ab_config.get('speed_threshold_percent', 50)
        dir_prob = ab_config.get('direction_change_probability', 0.1)

        alpha_fs, beta_fs = generate_alpha_beta_from_main(
            main_fs, speed_fs, pps, algorithm, min_dist, speed_thresh, dir_prob)

        # Common time grid from alpha (alpha/beta share the same grid)
        t_common = np.asarray(alpha_fs.x, dtype=float)
        alpha = np.asarray(alpha_fs.y, dtype=float)
        beta = np.asarray(beta_fs.y, dtype=float)

        # Compute E1-E4 by interpolating main onto t_common and applying curves.
        # Two interpolation modes for the resampling:
        #   - 'device': linear interpolation between samples — matches what the
        #               playback hardware actually does. With sparse input,
        #               quantization is visible only AT sample points; the
        #               curves smoothly sweep through intermediate values
        #               between samples.
        #   - 'snap':   zero-order hold — bars show the most-recent snapped
        #               value, so you see discrete jumps. Honest about snap,
        #               misleading about device behavior.
        # Toggled by the "Snap-honest view" checkbox in the controls bar.
        axes_config = config.get('positional_axes', {})
        snap_view = (hasattr(self, '_tq_snap_view_var')
                     and bool(self._tq_snap_view_var.get()))
        if apply_tq and snap_view:
            mfs_x = np.asarray(main_fs.x, dtype=float)
            mfs_y = np.asarray(main_fs.y, dtype=float)
            idx = np.searchsorted(mfs_x, t_common, side='right') - 1
            idx = np.clip(idx, 0, len(mfs_y) - 1)
            main_interp = mfs_y[idx]
        else:
            main_interp = np.interp(t_common, main_fs.x, main_fs.y)
        e_values = {}

        # Trochoid-spatial override: when on, derive E1-E4 from the
        # spatial projection (curve parameterized by input, projected
        # onto electrode angles) instead of per-axis response curves.
        # Mirrors the processor's behavior so the Animation Viewer shows
        # what the device will actually receive.
        apply_ts = (hasattr(self, '_ts_apply_var')
                    and bool(self._ts_apply_var.get()))
        if apply_ts:
            try:
                from processing.trochoid_spatial import (
                    compute_spatial_intensities)
                from processing.trochoid_quantization import (
                    FAMILY_DEFAULTS as _SFAMD)
                ts_cfg = config.get('trochoid_spatial', {}) or {}
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
                    main_interp, ts_family, ts_params,
                    electrode_angles_deg=ts_angles,
                    mapping=str(ts_cfg.get('mapping', 'directional')),
                    sharpness=float(ts_cfg.get('sharpness', 1.0)),
                    cycles_per_unit=float(
                        ts_cfg.get('cycles_per_unit', 1.0)),
                )
                for axis_name in ['e1', 'e2', 'e3', 'e4']:
                    e_values[axis_name] = np.asarray(spatial[axis_name])
                source_label = (f"{source_label}  [spatial: {ts_family}, "
                                f"mapping={ts_cfg.get('mapping')}]")
            except Exception as e:
                print(f"[viewer] trochoid_spatial fallback to curves: {e}")
                apply_ts = False  # fall through to response-curve path

        if not apply_ts:
            for axis_name in ['e1', 'e2', 'e3', 'e4']:
                cfg = axes_config.get(axis_name, {})
                if cfg.get('enabled', False):
                    signal_angle = cfg.get('signal_angle', 0)
                    cos_a = math.cos(math.radians(signal_angle))
                    rotated = np.clip(0.5 + (main_interp - 0.5) * cos_a,
                                      0.0, 1.0)
                    cp = cfg.get('curve', {}).get(
                        'control_points', [[0, 0], [1, 1]])
                    e_values[axis_name] = np.array(
                        [apply_linear_response_curve(v, cp) for v in rotated])
                else:
                    e_values[axis_name] = np.zeros_like(t_common)

        return {
            'source_label': source_label,
            't': t_common,
            'alpha': alpha,
            'beta': beta,
            'e1': e_values['e1'],
            'e2': e_values['e2'],
            'e3': e_values['e3'],
            'e4': e_values['e4'],
        }

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main content frame
        content = ttk.Frame(self)
        content.grid(row=0, column=0, sticky='nsew')
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        # Canvas placeholder (filled by _prepare_and_draw)
        self._canvas_frame = ttk.Frame(content)
        self._canvas_frame.grid(row=0, column=0, sticky='nsew')
        self._canvas_frame.columnconfigure(0, weight=1)
        self._canvas_frame.rowconfigure(0, weight=1)

        # Controls row 1: play, scrubber, time entry, speed, 3D toggle
        ctrl = ttk.Frame(content, padding="5")
        ctrl.grid(row=1, column=0, sticky='ew')
        ctrl.columnconfigure(1, weight=1)

        self._play_btn = ttk.Button(ctrl, text="\u25b6 Play", width=8,
                                    command=self._toggle_play)
        self._play_btn.grid(row=0, column=0, padx=(0, 5))

        self._scrubber_var = tk.IntVar(value=0)
        self._scrubber = ttk.Scale(ctrl, from_=0, to=100,
                                   orient=tk.HORIZONTAL,
                                   variable=self._scrubber_var,
                                   command=self._on_scrub)
        self._scrubber.grid(row=0, column=1, sticky='ew', padx=5)

        # Time entry: type a number in seconds and press Enter to jump
        time_frame = ttk.Frame(ctrl)
        time_frame.grid(row=0, column=2, padx=(5, 0))
        self._time_entry_var = tk.StringVar(value="0.00")
        time_entry = ttk.Entry(time_frame, textvariable=self._time_entry_var, width=7)
        time_entry.pack(side=tk.LEFT)
        time_entry.bind('<Return>', self._on_time_entry)
        ttk.Label(time_frame, text="s").pack(side=tk.LEFT)

        self._time_label = ttk.Label(ctrl, text="/ 0.00s", width=10)
        self._time_label.grid(row=0, column=3, padx=(2, 0))

        # Speed controls
        speed_frame = ttk.Frame(ctrl)
        speed_frame.grid(row=0, column=4, padx=(10, 0))
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        self._speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(speed_frame, textvariable=self._speed_var,
                                   values=["0.25", "0.5", "1.0", "2.0", "4.0"],
                                   width=5, state='readonly')
        speed_combo.pack(side=tk.LEFT, padx=(3, 0))
        speed_combo.set("1.0")
        ttk.Label(speed_frame, text="x").pack(side=tk.LEFT)

        # Panel visibility toggles. Placed on its own row (row 1 of the
        # ctrl frame) so adding more checkboxes here doesn't squeeze the
        # scrubber on row 0 down to invisible width.
        toggle_frame = ttk.LabelFrame(ctrl, text="Show", padding="2")
        toggle_frame.grid(row=1, column=0, columnspan=5,
                          sticky='w', padx=(0, 0), pady=(4, 0))

        self._show_trajectory_var = tk.BooleanVar(value=True)
        self._show_bars_var = tk.BooleanVar(value=True)
        self._show_dimmer_var = tk.BooleanVar(value=True)
        self._view_3d_var = tk.BooleanVar(value=False)
        self._waterfall_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(toggle_frame, text="Trajectory",
                        variable=self._show_trajectory_var,
                        command=self._on_view_toggle).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toggle_frame, text="Bars",
                        variable=self._show_bars_var,
                        command=self._on_view_toggle).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toggle_frame, text="Dimmer",
                        variable=self._show_dimmer_var,
                        command=self._on_view_toggle).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toggle_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Checkbutton(toggle_frame, text="3D",
                        variable=self._view_3d_var,
                        command=self._on_view_toggle).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toggle_frame, text="Waterfall",
                        variable=self._waterfall_var,
                        command=self._on_view_toggle).pack(side=tk.LEFT, padx=2)

        # Trochoid quantization toggle. Defaults to the global config
        # setting; the user can flip it independently here for A/B.
        # Uses _on_data_toggle (not _on_view_toggle) because changing
        # quantization changes the actual data, not just rendering.
        ttk.Separator(toggle_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)
        tq_default = bool(self.main_window.current_config
                          .get('trochoid_quantization', {})
                          .get('enabled', False))
        self._tq_apply_var = tk.BooleanVar(value=tq_default)
        ttk.Checkbutton(toggle_frame, text="Trochoid",
                        variable=self._tq_apply_var,
                        command=self._on_data_toggle).pack(side=tk.LEFT, padx=2)

        # Snap-honest vs device-honest view (only meaningful when Trochoid
        # is on). Off (default) = linear interpolation between funscript
        # samples — matches what the playback device actually does. On =
        # zero-order hold — bars/dimmer jump between snapped levels so the
        # quantization is visually obvious, but doesn't match playback.
        self._tq_snap_view_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toggle_frame, text="Snap-honest",
                        variable=self._tq_snap_view_var,
                        command=self._on_data_toggle).pack(side=tk.LEFT, padx=2)

        # Trochoid-spatial toggle. When on, E1-E4 come from the spatial
        # projection (curve parameterized by input, projected onto N
        # electrode angles) instead of per-axis response curves. Defaults
        # to whatever the global config has, can be flipped here for A/B.
        ts_default = bool(self.main_window.current_config
                          .get('trochoid_spatial', {})
                          .get('enabled', False))
        self._ts_apply_var = tk.BooleanVar(value=ts_default)
        ttk.Checkbutton(toggle_frame, text="Spatial",
                        variable=self._ts_apply_var,
                        command=self._on_data_toggle).pack(side=tk.LEFT, padx=2)

        # Controls row 2: zoom + scroll + follow for the dimmer strip
        zoom_ctrl = ttk.Frame(content, padding="2")
        zoom_ctrl.grid(row=2, column=0, sticky='ew')
        zoom_ctrl.columnconfigure(4, weight=1)

        ttk.Label(zoom_ctrl, text="Zoom:").grid(row=0, column=0, padx=(5, 2))
        self._dimmer_zoom_var = tk.IntVar(value=100)
        zoom_combo = ttk.Combobox(
            zoom_ctrl, textvariable=self._dimmer_zoom_var,
            values=[100, 200, 400, 800, 1600, 3200, 6400, 8000],
            width=6)
        zoom_combo.grid(row=0, column=1, padx=(0, 2))
        ttk.Label(zoom_ctrl, text="%").grid(row=0, column=2, sticky='w')
        zoom_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_dimmer_zoom())
        zoom_combo.bind('<Return>', lambda e: self._apply_dimmer_zoom())

        # Follow playhead: auto-zoom to a time window around the playhead
        self._follow_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(zoom_ctrl, text="Follow",
                        variable=self._follow_var).grid(
            row=0, column=3, padx=(10, 2))
        ttk.Label(zoom_ctrl, text="Window:").grid(row=0, column=4, sticky='e', padx=(5, 2))
        self._follow_window_var = tk.DoubleVar(value=10.0)
        win_entry = ttk.Entry(zoom_ctrl, textvariable=self._follow_window_var, width=5)
        win_entry.grid(row=0, column=5, padx=(0, 0))
        ttk.Label(zoom_ctrl, text="s").grid(row=0, column=6, padx=(0, 5))

        self._dimmer_scroll_var = tk.DoubleVar(value=0.0)
        self._dimmer_scrollbar = ttk.Scale(
            zoom_ctrl, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
            variable=self._dimmer_scroll_var,
            command=lambda v: self._apply_dimmer_zoom())
        self._dimmer_scrollbar.grid(row=0, column=7, sticky='ew', padx=5)
        zoom_ctrl.columnconfigure(7, weight=1)
        # Hidden until zoom > 100 and follow is off
        self._dimmer_scrollbar.grid_remove()

        # Source label
        self._source_label = ttk.Label(content, text="", foreground='#666')
        self._source_label.grid(row=3, column=0, sticky='w', padx=10, pady=(0, 5))

    def _prepare_and_draw(self):
        """Compute data and set up the matplotlib figure."""
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.gridspec as gridspec
        except ImportError:
            ttk.Label(self._canvas_frame,
                      text="matplotlib is required for the animation viewer.",
                      foreground='red').pack(padx=20, pady=20)
            return

        # Only recompute data on first call or explicit refresh
        if self._data is None:
            self._data = self._prepare_data()
        n = len(self._data['t'])
        self._n_frames = n
        self._scrubber.configure(to=max(0, n - 1))
        self._source_label.config(text=f"Source: {self._data['source_label']}")
        total_time = float(self._data['t'][-1]) if n > 0 else 0
        self._time_label.config(text=f"/ {total_time:.2f}s")

        # Clear old canvas
        for w in self._canvas_frame.winfo_children():
            w.destroy()

        use_3d = self._view_3d_var.get()

        # Determine which panels are active
        show_traj = self._show_trajectory_var.get()
        show_bars = self._show_bars_var.get()
        show_dimmer = self._show_dimmer_var.get()

        # At least one panel must be on
        if not show_traj and not show_bars and not show_dimmer:
            show_dimmer = True
            self._show_dimmer_var.set(True)

        # Build adaptive grid layout based on which panels are visible
        top_panels = []
        if show_traj:
            top_panels.append('traj')
        if show_bars:
            top_panels.append('bars')

        has_top = len(top_panels) > 0
        has_bottom = show_dimmer

        if has_top and has_bottom:
            n_rows, height_ratios = 2, [1, 1]
            fig_h = 7.5
        elif has_top:
            n_rows, height_ratios = 1, [1]
            fig_h = 4.0
        else:
            n_rows, height_ratios = 1, [1]
            fig_h = 4.0

        n_top_cols = max(len(top_panels), 1)
        width_ratios = [1.3 if p == 'traj' else 1 for p in top_panels] or [1]

        fig = Figure(figsize=(9, fig_h), dpi=90)
        fig.patch.set_facecolor('#f5f5f5')
        gs = gridspec.GridSpec(n_rows, n_top_cols,
                               width_ratios=width_ratios,
                               height_ratios=height_ratios,
                               wspace=0.25, hspace=0.35)

        # Reset optional artist references
        self._dot = None
        self._trail_line = None
        self._bars = None
        self._playhead = None
        self._time_plane = None
        self._dimmer_is_waterfall = False

        # Top row panels
        if has_top:
            col = 0
            for panel in top_panels:
                if panel == 'traj':
                    if use_3d:
                        self._build_3d_trajectory(fig, gs[0, col])
                    else:
                        self._build_2d_trajectory(fig, gs[0, col])
                elif panel == 'bars':
                    self._build_bars(fig, gs[0, col])
                col += 1

        # Bottom row
        if has_bottom:
            bottom_row = 1 if has_top else 0
            self._build_dimmer_strip(fig, gs[bottom_row, :])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                fig.tight_layout(pad=1.0)
            except Exception:
                pass

        # Embed in tkinter
        self._canvas = FigureCanvasTkAgg(fig, self._canvas_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._fig = fig
        self._is_3d = use_3d

        # Draw current frame
        self._update_frame()

    def _build_2d_trajectory(self, fig, subplot_spec):
        """Set up the 2D XY trajectory subplot."""
        ax = fig.add_subplot(subplot_spec)
        ax.set_aspect('equal')
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel('Alpha', fontsize=8)
        ax.set_ylabel('Beta', fontsize=8)
        ax.set_title('2D Trajectory', fontsize=9)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.15)

        # Unit circle
        theta = np.linspace(0, 2 * np.pi, 100)
        ax.plot(0.5 + 0.5 * np.cos(theta), 0.5 + 0.5 * np.sin(theta),
                color='#ccc', linewidth=1, linestyle='--', zorder=1)
        ax.plot(0.5, 0.5, '+', color='#999', markersize=8, zorder=1)

        # Full trajectory (static, faint)
        ax.plot(self._data['alpha'], self._data['beta'],
                color=self._TRAJECTORY_COLOR, linewidth=0.4, alpha=0.5, zorder=2)

        # Trail (animated)
        self._trail_line, = ax.plot([], [], color=self._TRAIL_COLOR,
                                    linewidth=1.5, alpha=0.6, zorder=3)
        # Dot (animated)
        self._dot = ax.scatter([0.5], [0.5], s=60, c=self._DOT_COLOR,
                               edgecolors='white', linewidths=0.5, zorder=4)
        self._ax_traj = ax

    def _build_3d_trajectory(self, fig, subplot_spec):
        """Set up the 3D (alpha, beta, time) trajectory subplot."""
        ax = fig.add_subplot(subplot_spec, projection='3d')
        d = self._data
        t = d['t']
        t_norm = (t - t[0]) / max(t[-1] - t[0], 1e-6)  # 0..1 for color mapping

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_zlim(float(t[0]), float(t[-1]))
        ax.set_xlabel('Alpha', fontsize=7, labelpad=2)
        ax.set_ylabel('Beta', fontsize=7, labelpad=2)
        ax.set_zlabel('Time (s)', fontsize=7, labelpad=2)
        ax.set_title('3D Trajectory', fontsize=9)
        ax.tick_params(labelsize=5)

        # Full trajectory — color-coded by time (blue→red)
        # Plot as segments for color gradient
        from matplotlib.collections import LineCollection
        from mpl_toolkits.mplot3d.art3d import Line3DCollection
        alpha = d['alpha']
        beta = d['beta']

        # Build segments: each is a pair of consecutive points
        points = np.array([alpha, beta, t]).T.reshape(-1, 1, 3)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Use a colormap based on time
        import matplotlib.cm as cm
        colors = cm.coolwarm(t_norm[:-1])
        lc = Line3DCollection(segments, colors=colors, linewidth=0.6, alpha=0.5)
        ax.add_collection3d(lc)

        # Trail (animated) — simple 3D line
        self._trail_line, = ax.plot([], [], [], color=self._TRAIL_COLOR,
                                    linewidth=2.0, alpha=0.7)
        # Dot (animated)
        self._dot, = ax.plot([0.5], [0.5], [0], 'o', color=self._DOT_COLOR,
                             markersize=6, markeredgecolor='white',
                             markeredgewidth=0.5, zorder=10)

        # Time plane indicator (horizontal line at current time)
        self._time_plane, = ax.plot([0, 1], [0.5, 0.5], [0, 0],
                                    color='#999', linewidth=0.5,
                                    linestyle=':', alpha=0.4)
        self._ax_traj = ax

    def _build_bars(self, fig, subplot_spec):
        """Set up the E1-E4 electrode intensity bar subplot."""
        ax = fig.add_subplot(subplot_spec)
        ax.set_xlim(-0.5, 3.5)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel('Intensity', fontsize=8)
        ax.set_title('Electrode Intensity', fontsize=9)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(self._BAR_LABELS, fontsize=8)
        ax.tick_params(labelsize=6)
        ax.grid(True, axis='y', alpha=0.15)

        self._bars = ax.bar([0, 1, 2, 3], [0, 0, 0, 0],
                            color=self._BAR_COLORS, width=0.6, zorder=3)

    def _build_dimmer_strip(self, fig, subplot_spec):
        """Build the E1-E4 intensity view: heatmap or waterfall."""
        d = self._data
        t = d['t']
        use_waterfall = self._waterfall_var.get()

        if use_waterfall:
            self._build_waterfall(fig, subplot_spec)
            return

        # ── Heatmap mode ─────────────────────────────────────────
        ax = fig.add_subplot(subplot_spec)
        # Reversed so E1 is at the top (origin='lower' puts row 0 at bottom)
        matrix = np.array([d['e4'], d['e3'], d['e2'], d['e1']],
                          dtype=float)

        # Sanitize: NaN/inf in any electrode channel would be rendered with
        # the inferno colormap's "bad" color, producing a stray magenta-ish
        # vertical column. Replace with 0.0 and clamp into [0, 1].
        n_bad = int(np.sum(~np.isfinite(matrix)))
        if n_bad:
            print(f"[dimmer] {n_bad} non-finite samples in E1-E4 matrix "
                  f"— replacing with 0")
        matrix = np.nan_to_num(matrix, nan=0.0,
                               posinf=1.0, neginf=0.0)
        np.clip(matrix, 0.0, 1.0, out=matrix)

        # Detect non-monotonic time samples (alpha/beta generation should
        # always produce monotonically increasing t — if not, imshow's
        # uniform column layout will misrepresent the data).
        if len(t) > 1:
            dt = np.diff(t)
            if not np.all(dt > 0):
                n_bad_t = int(np.sum(dt <= 0))
                print(f"[dimmer] WARNING: {n_bad_t} non-monotonic time "
                      f"samples in t array (alpha/beta grid issue)")

        # Anti-aliasing for long signals: when the matrix has far more
        # columns than the display can show (especially with quantized
        # signals that change every sample), the GPU's downsampling
        # produces a forest of thin vertical lines that obscures the
        # pattern. Pre-downsample by max-pooling so each output column
        # represents a fixed time slice — peaks survive, noise smooths
        # out. Cap output width at MAX_DIMMER_COLS columns.
        MAX_DIMMER_COLS = 2400
        n_cols = matrix.shape[1]
        if n_cols > MAX_DIMMER_COLS:
            chunk = int(np.ceil(n_cols / MAX_DIMMER_COLS))
            new_cols = int(np.ceil(n_cols / chunk))
            pad = new_cols * chunk - n_cols
            if pad > 0:
                matrix = np.pad(matrix, ((0, 0), (0, pad)),
                                mode='edge')
            # Reshape to (4, new_cols, chunk) and reduce along the
            # chunk axis with max so peak intensities survive.
            matrix = matrix.reshape(4, new_cols, chunk).max(axis=2)
            print(f"[dimmer] downsampled {n_cols} -> {new_cols} cols "
                  f"(chunk={chunk}) for display anti-aliasing")

        extent = [float(t[0]), float(t[-1]), -0.5, 3.5]
        self._dimmer_img = ax.imshow(
            matrix, aspect='auto', origin='lower', extent=extent,
            cmap='inferno', vmin=0.0, vmax=1.0, interpolation='nearest')

        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels(['E4', 'E3', 'E2', 'E1'], fontsize=8)
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_title('Electrode Intensity Over Time', fontsize=9)
        ax.tick_params(labelsize=6)

        # Playhead (animated vertical line). Cyan with explicit zorder so
        # it stays visible above the heatmap regardless of where the cursor
        # lands on the inferno colormap (white was hard to see against
        # bright orange/yellow regions).
        self._playhead = ax.axvline(x=float(t[0]), color='#00e5ff',
                                    linewidth=1.8, alpha=0.95,
                                    linestyle='-', zorder=10)
        self._ax_dimmer = ax
        self._dimmer_is_waterfall = False

        # Store full range for zoom
        self._dimmer_t_range = (float(t[0]), float(t[-1]))

    def _build_waterfall(self, fig, subplot_spec):
        """Build a 2D ridge/waterfall plot — stacked filled line plots.

        Each electrode gets its own horizontal band. The signal is drawn
        as a filled area within that band. This is purely 2D (no 3D
        renderer) so it renders at full speed even on long signals.
        """
        ax = fig.add_subplot(subplot_spec)
        d = self._data
        t = np.asarray(d['t'], dtype=float)

        # Each electrode gets a vertical band of height 1.0, stacked:
        #   E1: 0.0 – 1.0
        #   E2: 1.2 – 2.2   (0.2 gap between bands)
        #   E3: 2.4 – 3.4
        #   E4: 3.6 – 4.6
        band_height = 1.0
        gap = 0.2
        colors = self._BAR_COLORS
        ytick_pos = []
        ytick_labels = []

        # Reversed: E1 at top (idx 3), E4 at bottom (idx 0)
        for idx, (axis_name, color) in enumerate(
                zip(['e4', 'e3', 'e2', 'e1'],
                    [colors[3], colors[2], colors[1], colors[0]])):
            baseline = idx * (band_height + gap)
            y_val = np.asarray(d[axis_name], dtype=float)
            # Scale signal into the band: baseline + y_val * band_height
            y_plot = baseline + y_val * band_height

            ax.fill_between(t, baseline, y_plot,
                            color=color, alpha=0.6, linewidth=0)
            ax.plot(t, y_plot, color=color, linewidth=1.2, alpha=1.0,
                    label=axis_name.upper())
            # Baseline reference line
            ax.axhline(y=baseline, color=color, linewidth=0.5, alpha=0.4)

            ytick_pos.append(baseline + band_height / 2)
            ytick_labels.append(axis_name.upper())

        ax.set_yticks(ytick_pos)
        ax.set_yticklabels(ytick_labels, fontsize=8)
        ax.set_ylim(-0.1, 4 * (band_height + gap) - gap + 0.1)
        ax.set_xlim(float(t[0]), float(t[-1]))
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_title('Waterfall — Electrode Intensity', fontsize=9)
        ax.tick_params(labelsize=6)
        ax.legend(fontsize=6, loc='upper right', ncol=4)

        # Playhead (2D vertical line — fast). Explicit zorder so it stays
        # above the filled bands regardless of plotting order.
        self._playhead = ax.axvline(x=float(t[0]), color='#e53935',
                                    linewidth=1.8, alpha=0.95, zorder=10)
        self._ax_dimmer = ax
        self._dimmer_is_waterfall = True
        self._dimmer_t_range = (float(t[0]), float(t[-1]))

    def _apply_dimmer_zoom(self):
        """Apply zoom and scroll to the dimmer heatmap's time axis."""
        if not hasattr(self, '_ax_dimmer') or not hasattr(self, '_dimmer_t_range'):
            return
        if getattr(self, '_dimmer_is_waterfall', False):
            # Zoom applies to the X axis of the waterfall too
            pass

        try:
            zoom_pct = max(100, int(self._dimmer_zoom_var.get()))
        except (tk.TclError, ValueError):
            zoom_pct = 100

        t_start, t_end = self._dimmer_t_range
        full_duration = t_end - t_start
        if full_duration <= 0:
            return

        visible_duration = full_duration / (zoom_pct / 100.0)

        if zoom_pct > 100:
            # Show scrollbar
            if not self._dimmer_scrollbar.winfo_viewable():
                self._dimmer_scrollbar.grid()
            scroll_pos = self._dimmer_scroll_var.get()
            max_offset = full_duration - visible_duration
            offset = scroll_pos * max_offset
            view_start = t_start + offset
            view_end = view_start + visible_duration
        else:
            self._dimmer_scrollbar.grid_remove()
            view_start = t_start
            view_end = t_end

        ax = self._ax_dimmer
        if getattr(self, '_dimmer_is_waterfall', False):
            ax.set_xlim(view_start, view_end)
        else:
            ax.set_xlim(view_start, view_end)

        if hasattr(self, '_canvas'):
            self._canvas.draw_idle()

    def _on_view_toggle(self):
        """Render-only toggle (panels, 3D, waterfall) — keeps cached data."""
        saved_idx = self._frame_index
        was_playing = self._playing
        if was_playing:
            self._toggle_play()  # pause
        self._prepare_and_draw()
        self._frame_index = min(saved_idx, self._n_frames - 1)
        self._scrubber_var.set(self._frame_index)
        self._update_frame()
        if was_playing:
            self._toggle_play()  # resume

    def _on_data_toggle(self):
        """Data-changing toggle (e.g. trochoid) — invalidates cached data
        so _prepare_and_draw recomputes the trajectory and electrode signals."""
        self._data = None
        self._on_view_toggle()

    def _on_time_entry(self, event=None):
        """Jump to a specific time when user presses Enter in the time entry."""
        if self._data is None or self._n_frames == 0:
            return
        try:
            target_s = float(self._time_entry_var.get())
        except ValueError:
            return
        # Find nearest frame index
        t = self._data['t']
        idx = int(np.searchsorted(t, target_s))
        idx = max(0, min(idx, self._n_frames - 1))
        self._frame_index = idx
        self._scrubber_var.set(idx)
        self._update_frame()

    # ── Animation ────────────────────────────────────────────────────

    def _tick(self):
        """Advance one frame and schedule next tick."""
        if not self._playing or self._data is None:
            return

        # Advance by playback speed (skip frames for >1x)
        speed = max(0.25, float(self._speed_var.get()))
        self._frame_index += max(1, int(speed))
        if self._frame_index >= self._n_frames:
            self._frame_index = 0  # loop

        self._scrubber_var.set(self._frame_index)
        self._update_frame()
        self._after_id = self.after(int(1000 / self._FPS), self._tick)

    def _update_frame(self):
        """Redraw only the active artists for the current frame index."""
        if self._data is None or self._n_frames == 0:
            return

        i = self._frame_index
        d = self._data
        trail_start = max(0, i - self._TRAIL_LENGTH)

        # Trajectory (only if panel is visible and artists exist)
        if self._dot is not None:
            if getattr(self, '_is_3d', False):
                self._dot.set_data_3d(
                    [d['alpha'][i]], [d['beta'][i]], [d['t'][i]])
                if self._trail_line is not None:
                    self._trail_line.set_data_3d(
                        d['alpha'][trail_start:i + 1],
                        d['beta'][trail_start:i + 1],
                        d['t'][trail_start:i + 1])
                if self._time_plane is not None:
                    ct = float(d['t'][i])
                    self._time_plane.set_data_3d([0, 1], [0.5, 0.5], [ct, ct])
            else:
                self._dot.set_offsets([[d['alpha'][i], d['beta'][i]]])
                if self._trail_line is not None:
                    self._trail_line.set_data(
                        d['alpha'][trail_start:i + 1],
                        d['beta'][trail_start:i + 1])

        # Bars (only if panel is visible)
        if self._bars is not None:
            for idx, axis in enumerate(['e1', 'e2', 'e3', 'e4']):
                self._bars[idx].set_height(d[axis][i])

        # Dimmer playhead + follow-scroll (only if panel is visible)
        current_t = float(d['t'][i])
        if self._playhead is not None:
            try:
                # axvline stores a 2-element x array; pass an explicit
                # numpy array so newer matplotlib versions are happy.
                self._playhead.set_xdata(np.array([current_t, current_t]))
            except Exception as e:
                # Fallback — some matplotlib versions accept set_data
                try:
                    self._playhead.set_data(
                        [current_t, current_t], [0.0, 1.0])
                except Exception:
                    print(f"[viewer] playhead update failed: {e}")

        # Follow mode: keep a window centered on the playhead
        if (hasattr(self, '_dimmer_t_range') and hasattr(self, '_ax_dimmer')
                and self._follow_var.get()):
            t_start, t_end = self._dimmer_t_range
            try:
                window_s = max(0.5, float(self._follow_window_var.get()))
            except (tk.TclError, ValueError):
                window_s = 10.0
            half = window_s / 2.0
            view_start = max(t_start, current_t - half)
            view_end = min(t_end, current_t + half)
            # Keep the window width constant even at edges
            if view_end - view_start < window_s:
                if view_start == t_start:
                    view_end = min(t_end, t_start + window_s)
                else:
                    view_start = max(t_start, t_end - window_s)
            self._ax_dimmer.set_xlim(view_start, view_end)
        elif hasattr(self, '_dimmer_t_range') and self._playhead is not None:
            # Manual zoom/scroll (non-follow mode) — auto-scroll only during play
            if self._playing:
                try:
                    zoom_pct = max(100, int(self._dimmer_zoom_var.get()))
                except (tk.TclError, ValueError):
                    zoom_pct = 100
                if zoom_pct > 100:
                    t_start, t_end = self._dimmer_t_range
                    full = t_end - t_start
                    visible = full / (zoom_pct / 100.0)
                    desired_offset = current_t - t_start - visible / 2
                    max_offset = full - visible
                    if max_offset > 0:
                        self._dimmer_scroll_var.set(
                            max(0.0, min(1.0, desired_offset / max_offset)))

        # Time display (always update — cheap)
        self._time_entry_var.set(f"{current_t:.2f}")
        self._time_label.config(text=f"/ {float(d['t'][-1]):.2f}s")

        self._canvas.draw_idle()

    def _on_scrub(self, value):
        """Handle timeline scrubber drag."""
        try:
            idx = int(float(value))
        except (ValueError, TypeError):
            return
        idx = max(0, min(idx, self._n_frames - 1))
        self._frame_index = idx
        self._update_frame()

    def _toggle_play(self):
        """Play / pause toggle."""
        self._playing = not self._playing
        if self._playing:
            self._play_btn.config(text="\u23f8 Pause")
            self._tick()
        else:
            self._play_btn.config(text="\u25b6 Play")
            if self._after_id is not None:
                self.after_cancel(self._after_id)
                self._after_id = None

    def _on_close(self):
        """Clean up and close."""
        self._playing = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.destroy()
