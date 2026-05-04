"""
Shaft Viewer — horizontal shaft with E1-E4 in a line, optional synced
video playback.

Layout:

    ┌──────────────────────────────────────────────┐
    │                                              │
    │            VIDEO  (drag a file in,           │
    │            or click Browse)                  │
    │                                              │
    ├──────────────────────────────────────────────┤
    │ E1▓▓           E2▓▓           E3▓▓    E4▓▓   │   ← horizontal shaft
    │  ●────── position dot slides left⇄right      │     view (rotated 90°
    │                                              │     counter-clockwise
    │                                              │     from vertical: high
    │                                              │     position = LEFT)
    ├──────────────────────────────────────────────┤
    │ ▶ Play  ════●═══ 12.34 / 45.67s  Speed: 1.0x │
    │ Intensity mode: [auto ▾]  ☐ Apply trochoid   │
    │ [E1 slider] [E2 slider] [E3 slider] [E4 ..]  │
    │ Video: [ file.mp4 ]  [Browse] [Clear]        │
    └──────────────────────────────────────────────┘

Intensity source, default orientation, and Refresh behavior are
unchanged from the previous iteration. The rotation just swaps the
drawing axes — shaft configuration values are still "position along the
shaft" in [0, 1].
"""

import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from funscript import Funscript


DOT_COLOR = '#e53935'
SHAFT_COLOR = '#bfbfbf'
BORDER_COLOR = '#444444'
ELEC_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']  # E1 E2 E3 E4
ELEC_LABELS = ['E1', 'E2', 'E3', 'E4']


# ---------------------------------------------------------- optional libs

try:
    import cv2  # noqa: F401
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False

try:
    from PIL import Image, ImageTk  # noqa: F401
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False

try:
    import tkinterdnd2  # noqa: F401
    _HAVE_DND = True
except ImportError:
    _HAVE_DND = False


from ui.video_player_helper import VideoPlaybackMixin


class ShaftViewer(tk.Toplevel, VideoPlaybackMixin):
    """Horizontal shaft visualization + optional synced video."""

    _log_prefix = '[shaft]'

    _FPS = 30

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.title("Shaft Viewer")
        self.geometry("1100x800")
        self.minsize(820, 620)
        self.main_window = main_window

        # Ensure tkinterdnd2's DnD extension is registered on this
        # interpreter even if the root window was plain tk.Tk() (e.g.
        # when launched from the main app). Does nothing if tkinterdnd2
        # isn't installed or the extension is already loaded.
        if _HAVE_DND:
            try:
                import tkinterdnd2
                try:
                    tkinterdnd2.TkinterDnD._require(self)
                except Exception:
                    pass
            except ImportError:
                pass

        self._funscript = None
        self._e_files = {}
        self._source_label = "(no file)"

        # Electrode positions (shaft-space: 0 = base, 1 = tip).
        # Default orientation: E1 closest to the tip (= LEFT in the
        # horizontal view after the 90° CCW rotation), E4 at the base.
        self._elec_pos_vars = [tk.DoubleVar(value=p)
                               for p in (0.85, 0.65, 0.45, 0.25)]
        self._reach_var = tk.DoubleVar(value=0.18)

        # Intensity-mode state
        self._mode_var = tk.StringVar(value='auto')
        tq_default = bool(main_window.current_config
                          .get('trochoid_quantization', {})
                          .get('enabled', False))
        self._apply_tq_var = tk.BooleanVar(value=tq_default)

        # Video playback state
        self._video_path = None
        self._video_cap = None
        self._video_fps = 0.0
        self._video_duration = 0.0
        self._video_offset_var = tk.DoubleVar(value=0.0)  # seconds
        self._video_last_frame_time = -1.0
        self._video_widget = None  # PIL-backed tk.Label
        self._video_photo = None   # keeps a reference alive

        # Playback
        self._playing = False
        self._play_speed_var = tk.DoubleVar(value=1.0)
        self._last_tick_wall = None
        self._after_id = None

        # Show/hide video panel
        self._show_video_var = tk.BooleanVar(value=True)

        self._t_arr = None
        self._y_arr = None
        self._playhead_t = 0.0

        self._fig = None
        self._canvas = None
        self._ax = None
        self._dot_artist = None
        self._trail_artist = None
        self._elec_band_artists = []
        self._elec_label_artists = []
        self._intensity_bar_artists = []
        self._intensity_text_artists = []

        self._precomputed_e = {}
        self._active_source_desc = ""

        self._build_ui()
        self._load_data()
        self._build_figure()
        self._update_frame(force=True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═════════════════════════════════════════════════════════ UI

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        # Rows: 0=source, 1=mode, 2=video panel (weight=2), 3=shaft canvas (weight=3),
        # 4=playback, 5=electrode sliders, 6=reach, 7=video browse
        self.rowconfigure(2, weight=2)
        self.rowconfigure(3, weight=3)

        # --- Row 0: source + intensity summary -------------------------
        top = ttk.Frame(self, padding=(8, 6))
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Source:").grid(row=0, column=0, padx=(0, 4))
        self._source_lbl = ttk.Label(top, text="(loading)",
                                     foreground='#222')
        self._source_lbl.grid(row=0, column=1, sticky='w')
        self._intensity_src_lbl = ttk.Label(top, text="",
                                            foreground='#555')
        self._intensity_src_lbl.grid(row=0, column=2, padx=(12, 0))

        # --- Row 1: intensity-mode + refresh -------------------------
        mode_row = ttk.Frame(self, padding=(8, 0, 8, 4))
        mode_row.grid(row=1, column=0, sticky='ew')
        ttk.Label(mode_row, text="Intensity mode:").grid(
            row=0, column=0, padx=(0, 4))
        mode_cb = ttk.Combobox(
            mode_row, textvariable=self._mode_var,
            values=['auto', 'wave', 'spatial', 'curves',
                    'files', 'proximity'],
            state='readonly', width=12)
        mode_cb.grid(row=0, column=1, padx=(0, 12))
        mode_cb.bind('<<ComboboxSelected>>',
                     lambda e: self._refresh_compute())
        ttk.Checkbutton(
            mode_row, text="Apply trochoid quantization",
            variable=self._apply_tq_var,
            command=self._refresh_compute
        ).grid(row=0, column=2, padx=(0, 12))
        ttk.Button(mode_row, text="Refresh",
                   command=self._refresh_compute
                   ).grid(row=0, column=3, padx=(0, 4))
        ttk.Checkbutton(
            mode_row, text="Show video",
            variable=self._show_video_var,
            command=self._toggle_video_panel
        ).grid(row=0, column=4, padx=(12, 0))
        ttk.Label(
            mode_row, foreground='#888',
            text=("'auto' = wave → spatial → curves → files → proximity "
                  "(based on config). 'Refresh' re-reads settings.")
        ).grid(row=0, column=5, padx=(12, 0), sticky='w')

        # --- Row 2: video canvas (Label-based for drag-drop) ----------
        video_frame = ttk.LabelFrame(self, text="Video (drop a video file here or click Browse)",
                                      padding=4)
        self._video_frame = video_frame
        video_frame.grid(row=2, column=0, sticky='nsew', padx=8, pady=(2, 2))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        placeholder = ("Drop a video file here  (.mp4 / .mov / .mkv / ...)"
                       if _HAVE_CV2 and _HAVE_PIL
                       else "Video playback unavailable — install opencv-python + Pillow")
        self._video_widget = tk.Label(
            video_frame, text=placeholder,
            background='#111', foreground='#bbbbbb', anchor='center',
            font=('TkDefaultFont', 11))
        self._video_widget.grid(row=0, column=0, sticky='nsew')
        # Drag-and-drop binding
        if _HAVE_DND:
            try:
                self._video_widget.drop_target_register('DND_Files')
                self._video_widget.dnd_bind('<<Drop>>', self._on_video_drop)
            except Exception as e:
                print(f"[shaft] DnD init failed: {e}")

        # --- Row 3: shaft matplotlib canvas --------------------------
        self._canvas_frame = ttk.Frame(self, padding=(6, 0, 6, 0))
        self._canvas_frame.grid(row=3, column=0, sticky='nsew')
        self._canvas_frame.columnconfigure(0, weight=1)
        self._canvas_frame.rowconfigure(0, weight=1)

        # --- Row 4: playback bar ------------------------------------
        play_row = ttk.Frame(self, padding=(8, 4))
        play_row.grid(row=4, column=0, sticky='ew')
        play_row.columnconfigure(1, weight=1)
        self._play_btn = ttk.Button(play_row, text="▶ Play", width=9,
                                    command=self._toggle_play)
        self._play_btn.grid(row=0, column=0, padx=(0, 6))
        self._scrub_var = tk.DoubleVar(value=0.0)
        self._scrubber = ttk.Scale(play_row, from_=0.0, to=1.0,
                                   orient=tk.HORIZONTAL,
                                   variable=self._scrub_var,
                                   command=self._on_scrub)
        self._scrubber.grid(row=0, column=1, sticky='ew')
        self._time_lbl = ttk.Label(play_row, text="0.00 / 0.00 s",
                                   foreground='#444', width=18)
        self._time_lbl.grid(row=0, column=2, padx=(8, 0))
        ttk.Label(play_row, text="Speed:").grid(row=0, column=3,
                                                 padx=(12, 2))
        speed = ttk.Combobox(play_row, textvariable=self._play_speed_var,
                              values=['0.25', '0.5', '1.0', '2.0', '4.0'],
                              width=6, state='readonly')
        speed.grid(row=0, column=4)
        speed.set('1.0')

        # --- Row 5: electrode position sliders ----------------------
        elec_row = ttk.LabelFrame(
            self, text="Electrode positions (0 = base/left, 1 = tip/right)",
            padding=(8, 4))
        elec_row.grid(row=5, column=0, sticky='ew', padx=8, pady=(2, 2))
        for i, label in enumerate(ELEC_LABELS):
            ttk.Label(elec_row, text=label, foreground=ELEC_COLORS[i],
                      width=3).grid(row=0, column=i * 3, padx=(0, 4))
            sc = ttk.Scale(elec_row, from_=0.0, to=1.0,
                           orient=tk.HORIZONTAL,
                           variable=self._elec_pos_vars[i],
                           length=150,
                           command=lambda v, idx=i: self._on_elec_pos_change(idx))
            sc.grid(row=0, column=i * 3 + 1, padx=(0, 4))
            ent = ttk.Entry(elec_row, textvariable=self._elec_pos_vars[i],
                            width=6)
            ent.grid(row=0, column=i * 3 + 2, padx=(0, 12))
            ent.bind('<Return>', lambda e, idx=i: self._on_elec_pos_change(idx))

        # --- Row 6: reach + video controls --------------------------
        aux_row = ttk.Frame(self, padding=(8, 2, 8, 8))
        aux_row.grid(row=6, column=0, sticky='ew')
        aux_row.columnconfigure(6, weight=1)
        ttk.Label(aux_row, text="Proximity reach:").grid(
            row=0, column=0, padx=(0, 4))
        sc = ttk.Scale(aux_row, from_=0.02, to=0.5, orient=tk.HORIZONTAL,
                       variable=self._reach_var, length=140,
                       command=lambda v: self._update_frame(force=True))
        sc.grid(row=0, column=1, padx=(0, 4))
        ttk.Label(aux_row, textvariable=self._reach_var, width=5).grid(
            row=0, column=2)

        # Video controls
        ttk.Separator(aux_row, orient='vertical').grid(
            row=0, column=3, sticky='ns', padx=8)
        ttk.Label(aux_row, text="Video:").grid(
            row=0, column=4, padx=(0, 4))
        self._video_path_lbl = ttk.Label(aux_row, text="(none)",
                                         foreground='#666', width=24,
                                         anchor='w')
        self._video_path_lbl.grid(row=0, column=5, sticky='w')
        ttk.Button(aux_row, text="Browse…",
                   command=self._browse_video).grid(row=0, column=6,
                                                     sticky='e', padx=(4, 4))
        ttk.Button(aux_row, text="Clear",
                   command=self._clear_video).grid(row=0, column=7)
        ttk.Label(aux_row, text="Offset (s):").grid(
            row=0, column=8, padx=(12, 2))
        # Spinbox with 0.05 s resolution; still accepts typed values.
        offs = ttk.Spinbox(aux_row, from_=-3600.0, to=3600.0,
                           increment=0.05,
                           textvariable=self._video_offset_var, width=8,
                           command=lambda: self._update_video_frame(force=True))
        offs.grid(row=0, column=9)
        offs.bind('<Return>',
                  lambda e: self._update_video_frame(force=True))
        # Sync here: set the offset so that the CURRENT signal playhead
        # time aligns to the CURRENT video frame (i.e. drop the dt into
        # the offset so subsequent video_t calls match).
        ttk.Button(aux_row, text="Sync here",
                   command=self._sync_here).grid(row=0, column=10,
                                                  padx=(8, 0))

    # ═════════════════════════════════════════════════════════ data

    def _load_data(self):
        path = None
        mw = self.main_window
        if hasattr(mw, 'input_files') and mw.input_files:
            cand = mw.input_files[0]
            if os.path.isfile(cand) and cand.endswith('.funscript'):
                path = cand
        if path:
            try:
                self._funscript = Funscript.from_file(path)
                self._source_label = os.path.basename(path)
            except Exception as e:
                print(f"[shaft] load failed: {e}")
                self._funscript = None
                self._source_label = f"(load failed: {e})"
            base = path[:-len('.funscript')] if path.endswith('.funscript') else path
            for axis in ('e1', 'e2', 'e3', 'e4'):
                ep = f"{base}.{axis}.funscript"
                if os.path.isfile(ep):
                    try:
                        self._e_files[axis] = Funscript.from_file(ep)
                    except Exception:
                        pass
        else:
            t = np.linspace(0, 20, 1200)
            y = 0.5 + 0.4 * np.sin(2 * np.pi * 0.8 * t)
            self._funscript = Funscript(t, y)
            self._source_label = "Demo (synthetic 20 s)"
        self._source_lbl.config(text=self._source_label)
        if self._funscript is not None and len(self._funscript.x) > 0:
            self._t_arr = np.asarray(self._funscript.x, dtype=float)
            self._y_arr = np.asarray(self._funscript.y, dtype=float)
            t0, t1 = float(self._t_arr[0]), float(self._t_arr[-1])
            if t1 <= t0:
                t1 = t0 + 1.0
            self._scrubber.configure(from_=t0, to=t1)
            self._scrub_var.set(t0)
            self._playhead_t = t0
        # Auto-detect matching video file alongside the funscript
        if path and _HAVE_CV2 and _HAVE_PIL:
            base2 = path[:-len('.funscript')] if path.endswith('.funscript') else path
            for ext in ('.mp4', '.mov', '.mkv', '.m4v', '.avi', '.webm'):
                vp = base2 + ext
                if os.path.isfile(vp):
                    self._open_video(vp)
                    break
        self._refresh_compute(silent=True)

    # ═════════════════════════════════════════════ live compute / refresh

    def _refresh_compute(self, silent=False):
        self._precomputed_e = {}
        if self._funscript is None or self._t_arr is None:
            self._intensity_src_lbl.config(text="(no funscript)",
                                            foreground='#777')
            if self._canvas is not None:
                self._update_frame(force=True)
            return
        cfg = self.main_window.current_config or {}
        mode = self._mode_var.get()
        apply_tq = bool(self._apply_tq_var.get())
        main_y = self._y_arr.copy()
        if apply_tq:
            tq_cfg = cfg.get('trochoid_quantization', {}) or {}
            try:
                from processing.trochoid_quantization import (
                    generate_curve_levels,
                    FAMILY_DEFAULTS as _TFAMD,
                )
                family = str(tq_cfg.get('family',
                                        tq_cfg.get('curve_type', 'hypo')))
                pbf = tq_cfg.get('params_by_family') or {}
                fparams = dict(pbf.get(family) or {})
                if not fparams and family in ('hypo', 'epi'):
                    fparams = {'R': float(tq_cfg.get('R', 5.0)),
                               'r': float(tq_cfg.get('r', 3.0)),
                               'd': float(tq_cfg.get('d', 2.0))}
                if not fparams:
                    fparams = dict(_TFAMD.get(family, {}).get('params', {}))
                levels = generate_curve_levels(
                    int(tq_cfg.get('n_points', 23)), family, fparams,
                    str(tq_cfg.get('projection', 'radius')))
                idx = np.searchsorted(levels, main_y)
                idx = np.clip(idx, 1, len(levels) - 1)
                left = levels[idx - 1]; right = levels[idx]
                main_y = np.where(np.abs(main_y - left) <= np.abs(main_y - right),
                                  left, right)
            except Exception as e:
                print(f"[shaft] trochoid-quantization skipped: {e}")

        if mode == 'auto':
            if (cfg.get('traveling_wave', {}) or {}).get('enabled', False):
                resolved = 'wave'
            elif (cfg.get('trochoid_spatial', {}) or {}).get('enabled', False):
                resolved = 'spatial'
            elif cfg.get('positional_axes', {}).get('generate_motion_axis',
                                                    False):
                resolved = 'curves'
            elif self._e_files:
                resolved = 'files'
            else:
                resolved = 'proximity'
        else:
            resolved = mode
        desc = ""
        try:
            if resolved == 'wave':
                from processing.traveling_wave import (
                    compute_wave_intensities)
                from funscript import Funscript
                tw_cfg = cfg.get('traveling_wave', {}) or {}
                positions = tuple(
                    float(p) for p in tw_cfg.get(
                        'electrode_positions',
                        [0.85, 0.65, 0.45, 0.25]))
                # Build a Funscript from the (possibly quantized) main_y.
                wave_fs = Funscript(
                    np.asarray(self._t_arr, dtype=float),
                    np.asarray(main_y, dtype=float))
                intens = compute_wave_intensities(
                    wave_fs,
                    electrode_positions=positions,
                    wave_speed_hz=float(tw_cfg.get('wave_speed_hz', 1.0)),
                    wave_width=float(tw_cfg.get('wave_width', 0.18)),
                    direction=str(tw_cfg.get('direction', 'bounce')),
                    envelope_mode=str(tw_cfg.get(
                        'envelope_mode', 'input')),
                    speed_mod=float(tw_cfg.get('speed_mod', 0.0)),
                    sharpness=float(tw_cfg.get('sharpness', 1.0)),
                    velocity_window_s=float(tw_cfg.get(
                        'velocity_window_s', 0.10)),
                )
                for k in ('e1', 'e2', 'e3', 'e4'):
                    self._precomputed_e[k] = (self._t_arr,
                                               np.asarray(intens[k]))
                desc = (f"Traveling Wave ("
                        f"{tw_cfg.get('direction', 'bounce')}, "
                        f"{tw_cfg.get('envelope_mode', 'input')})")
            elif resolved == 'spatial':
                from processing.trochoid_spatial import (
                    compute_spatial_intensities)
                from processing.trochoid_quantization import (
                    FAMILY_DEFAULTS as _SFAMD)
                ts_cfg = cfg.get('trochoid_spatial', {}) or {}
                family = str(ts_cfg.get('family', 'hypo'))
                pbf = ts_cfg.get('params_by_family') or {}
                fparams = dict(pbf.get(family) or {})
                if not fparams:
                    fparams = dict(_SFAMD.get(family, {}).get('params', {}))
                angles = tuple(float(a) for a in ts_cfg.get(
                    'electrode_angles_deg', [0, 90, 180, 270]))
                intens = compute_spatial_intensities(
                    main_y, family, fparams,
                    electrode_angles_deg=angles,
                    mapping=str(ts_cfg.get('mapping', 'directional')),
                    sharpness=float(ts_cfg.get('sharpness', 1.0)),
                    cycles_per_unit=float(ts_cfg.get('cycles_per_unit', 1.0)))
                for k in ('e1', 'e2', 'e3', 'e4'):
                    self._precomputed_e[k] = (self._t_arr,
                                               np.asarray(intens[k]))
                desc = (f"Trochoid Spatial ({family}, "
                        f"{ts_cfg.get('mapping', 'directional')})")
            elif resolved == 'curves':
                import math
                from processing.linear_mapping import (
                    apply_linear_response_curve)
                axes_cfg = cfg.get('positional_axes', {}) or {}
                for i, axis in enumerate(['e1', 'e2', 'e3', 'e4']):
                    ax_cfg = axes_cfg.get(axis, {}) or {}
                    cp = ax_cfg.get('curve', {}).get(
                        'control_points', [[0, 0], [1, 1]])
                    signal_angle = float(ax_cfg.get('signal_angle', 0))
                    cos_a = math.cos(math.radians(signal_angle))
                    rotated = np.clip(0.5 + (main_y - 0.5) * cos_a,
                                       0.0, 1.0)
                    arr = np.array([apply_linear_response_curve(float(v), cp)
                                    for v in rotated])
                    self._precomputed_e[axis] = (self._t_arr, arr)
                desc = "Response curves (Motion Axis 4P)"
            elif resolved == 'files':
                if not self._e_files:
                    desc = "No .e1-.e4 files — proximity fallback"
                else:
                    for k, fs in self._e_files.items():
                        self._precomputed_e[k] = (
                            np.asarray(fs.x, dtype=float),
                            np.asarray(fs.y, dtype=float))
                    desc = f"From .{'/'.join(sorted(self._e_files.keys()))} files"
            else:
                desc = "Proximity model (geometric)"
        except Exception as e:
            print(f"[shaft] compute failed ({resolved}): {e}")
            self._precomputed_e = {}
            desc = f"Compute failed ({resolved}); proximity fallback"
        if apply_tq:
            desc = f"{desc}  +  trochoid quantization"
        self._active_source_desc = desc
        self._intensity_src_lbl.config(
            text=f"Intensity: {desc}",
            foreground=('#1a7e2e' if self._precomputed_e else '#777'))
        if not silent and self._canvas is not None:
            self._update_frame(force=True)

    # ═════════════════════════════════════════════ figure construction

    def _build_figure(self):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.patches import Rectangle
            import matplotlib.patches as mpatches
        except ImportError:
            ttk.Label(self._canvas_frame,
                      text="matplotlib required.",
                      foreground='red').grid(row=0, column=0,
                                              padx=20, pady=20)
            return

        fig = Figure(figsize=(9.5, 2.4), dpi=90)
        fig.patch.set_facecolor('#fafafa')
        ax = fig.add_subplot(111)

        # Horizontal shaft: 0 = base/LEFT, 1 = tip/RIGHT. E1 (default
        # position 0.85) lands near the right end as requested.
        shaft_h = 0.30
        shaft_y0 = 0.50 - shaft_h / 2
        ax.add_patch(Rectangle(
            (0.0, shaft_y0), 1.0, shaft_h,
            facecolor=SHAFT_COLOR, edgecolor=BORDER_COLOR, linewidth=1.2,
            zorder=1))
        # Rounded cap at the RIGHT end (the tip)
        ax.add_patch(mpatches.Ellipse(
            (1.0, 0.50), shaft_h * 0.45, shaft_h,
            facecolor=SHAFT_COLOR, edgecolor=BORDER_COLOR, linewidth=1.2,
            zorder=1))
        self._shaft_y0 = shaft_y0
        self._shaft_h = shaft_h

        # Electrode bands (vertical rectangles, updated live)
        band_w = 0.05
        for i in range(4):
            pos = float(self._elec_pos_vars[i].get())
            rect = Rectangle(
                (pos - band_w / 2, shaft_y0), band_w, shaft_h,
                facecolor=ELEC_COLORS[i], edgecolor='black',
                linewidth=0.7, alpha=0.35, zorder=2)
            ax.add_patch(rect)
            self._elec_band_artists.append(rect)
            txt = ax.text(pos, shaft_y0 - 0.05, ELEC_LABELS[i],
                          ha='center', va='top',
                          fontsize=10, color=ELEC_COLORS[i],
                          fontweight='bold', zorder=3)
            self._elec_label_artists.append(txt)

        # Intensity bars ABOVE each electrode band, growing upward
        bar_base_y = shaft_y0 + shaft_h + 0.03
        bar_max_h = 0.35
        for i in range(4):
            pos = float(self._elec_pos_vars[i].get())
            rect = Rectangle(
                (pos - 0.02, bar_base_y), 0.04, 0.0,
                facecolor=ELEC_COLORS[i], edgecolor=ELEC_COLORS[i],
                linewidth=0.6, alpha=0.85, zorder=4)
            ax.add_patch(rect)
            self._intensity_bar_artists.append(rect)
            txt = ax.text(pos, bar_base_y + bar_max_h + 0.03,
                          "0.00", ha='center', va='bottom',
                          fontsize=9, color=ELEC_COLORS[i], zorder=4)
            self._intensity_text_artists.append(txt)
        self._bar_base_y = bar_base_y
        self._bar_max_h = bar_max_h

        # Moving dot + trail
        self._trail_artist, = ax.plot(
            [], [], color='#888888', linewidth=1.2, alpha=0.35, zorder=5)
        self._dot_artist, = ax.plot(
            [0.5], [0.5], marker='o', color=DOT_COLOR,
            markersize=12, markeredgecolor='black', markeredgewidth=1.0,
            zorder=6)

        ax.set_xlim(-0.05, 1.05)  # normal: position 1 on RIGHT (tip)
        ax.set_ylim(-0.05, 1.10)
        ax.set_yticks([])
        ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xlabel('Shaft position  (0 = base/left,  1 = tip/right)',
                      fontsize=9)
        ax.set_title("Shaft — horizontal view (E1 toward tip/right)",
                     fontsize=10)
        ax.set_aspect('auto')

        fig.tight_layout(pad=0.6)
        canvas = FigureCanvasTkAgg(fig, self._canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        self._fig = fig
        self._canvas = canvas
        self._ax = ax

    # ═════════════════════════════════════════════ frame updates

    def _position_at(self, t):
        if self._t_arr is None or self._y_arr is None:
            return 0.5
        return float(np.interp(t, self._t_arr, self._y_arr))

    def _intensities_at(self, t, pos):
        out = {}
        if self._precomputed_e:
            for axis in ('e1', 'e2', 'e3', 'e4'):
                pair = self._precomputed_e.get(axis)
                if pair is None:
                    out[axis] = 0.0
                    continue
                tx, ty = pair
                out[axis] = float(np.interp(t, tx, ty)) if len(tx) else 0.0
            return out
        try:
            reach = max(1e-3, float(self._reach_var.get()))
        except (tk.TclError, ValueError):
            reach = 0.15
        for i, axis in enumerate(('e1', 'e2', 'e3', 'e4')):
            try:
                ep = float(self._elec_pos_vars[i].get())
            except (tk.TclError, ValueError):
                ep = [0.85, 0.65, 0.45, 0.25][i]
            d = abs(pos - ep)
            out[axis] = float(max(0.0, 1.0 - d / reach))
        return out

    def _update_frame(self, force=False):
        if self._fig is None or self._canvas is None:
            return
        t = self._playhead_t
        pos = self._position_at(t)

        # Moving dot (dot's x = position, y = vertical center of shaft)
        self._dot_artist.set_data([pos], [0.5])

        # Trail: recent 0.8s (position samples drawn at shaft vertical center)
        if self._t_arr is not None and len(self._t_arr) > 1:
            t_trail = np.linspace(max(self._t_arr[0], t - 0.8), t, 30)
            y_trail = np.interp(t_trail, self._t_arr, self._y_arr)
            self._trail_artist.set_data(y_trail, np.full_like(y_trail, 0.5))

        # Electrode bands (pick up slider changes)
        bw = 0.05
        for i, rect in enumerate(self._elec_band_artists):
            try:
                ep = float(self._elec_pos_vars[i].get())
            except (tk.TclError, ValueError):
                ep = [0.85, 0.65, 0.45, 0.25][i]
            rect.set_x(ep - bw / 2)
            self._elec_label_artists[i].set_position(
                (ep, self._shaft_y0 - 0.05))

        # Intensities & bars
        intens = self._intensities_at(t, pos)
        for i, axis in enumerate(('e1', 'e2', 'e3', 'e4')):
            v = max(0.0, min(1.0, float(intens.get(axis, 0.0))))
            try:
                ep = float(self._elec_pos_vars[i].get())
            except (tk.TclError, ValueError):
                ep = [0.85, 0.65, 0.45, 0.25][i]
            bar = self._intensity_bar_artists[i]
            bar.set_x(ep - 0.02)
            bar.set_y(self._bar_base_y)
            bar.set_height(v * self._bar_max_h)
            self._intensity_text_artists[i].set_position(
                (ep, self._bar_base_y + self._bar_max_h + 0.03))
            self._intensity_text_artists[i].set_text(f"{v:.2f}")

        if self._t_arr is not None and len(self._t_arr):
            self._time_lbl.config(
                text=f"{t:.2f} / {float(self._t_arr[-1]):.2f} s")

        self._canvas.draw_idle()
        # Also keep the video frame in sync
        self._update_video_frame()

    # Video handlers (_open_video, _clear_video, _browse_video,
    # _on_video_drop, _update_video_frame, _sync_here) come from
    # VideoPlaybackMixin.

    # ═════════════════════════════════════════════ handlers

    def _on_scrub(self, value=None):
        try:
            t = float(self._scrub_var.get())
        except (tk.TclError, ValueError):
            return
        self._playhead_t = t
        self._update_frame()

    def _on_elec_pos_change(self, idx):
        self._update_frame(force=True)

    def _toggle_play(self):
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        # Prime a video frame BEFORE starting the tick loop, so the dot
        # and the video are visually aligned at the playhead's starting
        # time rather than the video lagging a scrubbing seek into the
        # first few animation frames.
        self._update_video_frame(force=True)
        self._playing = True
        self._play_btn.config(text="⏸ Pause")
        self._last_tick_wall = time.monotonic()
        self._tick()

    def _stop_playback(self):
        self._playing = False
        self._play_btn.config(text="▶ Play")
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        if not self._playing:
            return
        if self._t_arr is None or len(self._t_arr) < 2:
            self._stop_playback()
            return
        now = time.monotonic()
        dt_wall = now - (self._last_tick_wall or now)
        self._last_tick_wall = now
        try:
            speed = float(self._play_speed_var.get())
        except (tk.TclError, ValueError):
            speed = 1.0
        self._playhead_t += dt_wall * speed
        if self._playhead_t >= float(self._t_arr[-1]):
            self._playhead_t = float(self._t_arr[0])
        try:
            self._scrub_var.set(self._playhead_t)
        except tk.TclError:
            pass
        self._update_frame()
        self._after_id = self.after(int(1000 / self._FPS), self._tick)

    def _toggle_video_panel(self):
        """Show or hide the video panel without disturbing video state.

        Hiding the panel keeps the loaded video and playhead — toggling
        back on resumes from where it was.
        """
        if not hasattr(self, '_video_frame'):
            return
        if bool(self._show_video_var.get()):
            self._video_frame.grid()
            self.rowconfigure(2, weight=2)
            self._update_video_frame(force=True)
        else:
            self._video_frame.grid_remove()
            self.rowconfigure(2, weight=0)

    def _on_close(self):
        self._stop_playback()
        if self._video_cap is not None:
            try:
                self._video_cap.release()
            except Exception:
                pass
        self.destroy()


def main():
    # Prefer tkinterdnd2's Tk if available — it enables drag-drop on the
    # standalone runner too.
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except Exception:
        root = tk.Tk()
    root.withdraw()
    class _Stub:
        input_files = sys.argv[1:]
    ShaftViewer(root, _Stub())
    root.mainloop()


if __name__ == '__main__':
    main()
