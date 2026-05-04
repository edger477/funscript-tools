"""
Trochoid Viewer — split panel showing the 2D trochoid curve and its
"shadow" projected onto the horizontal shaft.

Left panel:
    Full 2D trochoid / hypo / epi / rose / lissajous / butterfly /
    superformula curve, drawn as a dim reference. A pen dot traces
    along the curve driven by the current funscript value y(t):
    parameter theta = y * theta_max * cycles_per_unit.

Right panel:
    Horizontal shaft with E1-E4 electrodes. A "shadow" marker
    slides along the shaft at the normalized projection of the
    pen's (x, y) coordinate onto the selected axis (x / y / radius).
    Electrodes light up via proximity — whichever is closest to
    the shadow.

This makes the relationship between "trochoid as a shape" and
"signal on the shaft" visible: you watch the pen explore the
lobes on the left, and its shadow sweep the shaft on the right.
Optional synced video playback.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from funscript import Funscript
from processing.trochoid_quantization import (
    curve_xy, get_family_theta_max, FAMILY_DEFAULTS, CURVE_FAMILIES,
)

ELEC_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
ELEC_LABELS = ['E1', 'E2', 'E3', 'E4']

PROJECTIONS = ('radius', 'x', 'y')
SHAFT_MODES = ('shadow', 'lobes')


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


class TrochoidViewer(tk.Toplevel, VideoPlaybackMixin):
    """2D trochoid + shaft-shadow viewer, synced to the funscript."""

    _log_prefix = '[trochoid]'

    _FPS = 30

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.title("Trochoid Viewer")
        self.geometry("1200x820")
        self.minsize(960, 680)
        self.main_window = main_window

        if _HAVE_DND:
            try:
                import tkinterdnd2
                try:
                    tkinterdnd2.TkinterDnD._require(self)
                except Exception:
                    pass
            except ImportError:
                pass

        # Seed curve + projection from the Trochoid Spatial config, since
        # that path most closely matches "trochoid drives electrodes".
        cfg = (main_window.current_config or {})
        ts_cfg = cfg.get('trochoid_spatial', {}) or {}
        tq_cfg = cfg.get('trochoid_quantization', {}) or {}
        default_family = ts_cfg.get('family') or tq_cfg.get('family', 'hypo')
        if default_family not in CURVE_FAMILIES:
            default_family = 'hypo'
        default_proj = tq_cfg.get('projection', 'x')
        if default_proj not in PROJECTIONS:
            default_proj = 'x'
        default_cycles = float(ts_cfg.get('cycles_per_unit', 1.0))
        self._family_var = tk.StringVar(value=default_family)
        self._projection_var = tk.StringVar(value=default_proj)
        self._cycles_var = tk.DoubleVar(value=default_cycles)
        self._shaft_mode_var = tk.StringVar(value='shadow')

        # Per-family param dict, sourced from config when available.
        params_by_family = (ts_cfg.get('params_by_family')
                            or tq_cfg.get('params_by_family') or {})
        self._params_by_family = {}
        for fam, spec in FAMILY_DEFAULTS.items():
            out = dict(spec['params'])
            cfg_fam = params_by_family.get(fam, {}) or {}
            for k, default_v in out.items():
                v = cfg_fam.get(k, default_v)
                if isinstance(default_v, str):
                    out[k] = str(v)
                else:
                    try:
                        out[k] = float(v)
                    except (TypeError, ValueError):
                        pass
            self._params_by_family[fam] = out

        # Electrode positions along the shaft (0 = base, 1 = tip).
        # Seed from traveling_wave config if present; otherwise a
        # sensible default.
        tw_cfg = cfg.get('traveling_wave', {}) or {}
        positions = tw_cfg.get('electrode_positions',
                                [0.85, 0.65, 0.45, 0.25])
        self._pos_vars = [tk.DoubleVar(
            value=float(positions[i] if i < len(positions)
                         else (0.85 - 0.2 * i))) for i in range(4)]
        self._reach_var = tk.DoubleVar(value=0.18)

        # Show/hide video panel
        self._show_video_var = tk.BooleanVar(value=True)

        # Data / playback state
        self._funscript = None
        self._source_label = "(no file)"
        self._t_arr = None
        self._y_arr = None
        self._playhead_t = 0.0

        self._playing = False
        self._play_speed_var = tk.DoubleVar(value=1.0)
        self._last_tick_wall = None
        self._after_id = None

        # Precomputed shadow projection for the current curve (cached;
        # recomputed on family/projection/cycles/params change).
        self._shadow_lookup_t = None  # 1D array of theta samples
        self._shadow_lookup_v = None  # normalized shadow values
        self._curve_xy_cache = None   # (xc, yc) full dense curve

        # Video
        self._video_path = None
        self._video_cap = None
        self._video_fps = 0.0
        self._video_duration = 0.0
        self._video_offset_var = tk.DoubleVar(value=0.0)
        self._video_last_frame_time = -1.0
        self._video_widget = None
        self._video_photo = None

        # Matplotlib
        self._fig = None
        self._canvas = None
        self._ax_curve = None
        self._ax_shaft = None
        self._curve_line_artist = None
        self._curve_pen_artist = None
        self._curve_trail_artist = None
        self._shadow_marker_artist = None
        self._shadow_trail_artist = None
        self._elec_band_artists = []
        self._elec_label_artists = []
        self._intensity_bar_artists = []
        self._intensity_text_artists = []
        self._curve_trail_buf = []   # (t, x, y)
        self._shadow_trail_buf = []  # (t, shaft_pos)

        # Lobe-wrap mode data: list of dicts {theta_center,
        # theta_start, theta_end, peak_r, shaft_center}.
        self._lobes = []
        self._lobe_bar_artists = []
        self._lobe_label_artists = []
        self._active_lobe_outline = None

        self._build_ui()
        self._load_data()
        self._build_figure()
        self._recompute_curve()
        self._update_frame(force=True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═════════════════════════════════════════════════════════ UI

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        # Rows:
        #  0 source + family + projection + cycles + show-video
        #  1 main split (left=2D curve, right column = video above shaft)
        #  2 playback bar
        #  3 electrode positions row
        #  4 video controls
        self.rowconfigure(1, weight=1)

        # --- Row 0: top controls -------------------------------------
        top = ttk.Frame(self, padding=(8, 6))
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Source:").grid(row=0, column=0, padx=(0, 4))
        self._source_lbl = ttk.Label(top, text="(loading)",
                                     foreground='#222')
        self._source_lbl.grid(row=0, column=1, sticky='w')

        ttk.Label(top, text="Family:").grid(row=0, column=2, padx=(12, 2))
        fam_cb = ttk.Combobox(top, textvariable=self._family_var,
                               values=list(CURVE_FAMILIES),
                               state='readonly', width=12)
        fam_cb.grid(row=0, column=3)
        fam_cb.bind('<<ComboboxSelected>>',
                    lambda e: self._on_curve_changed())

        ttk.Label(top, text="Projection:").grid(row=0, column=4,
                                                  padx=(12, 2))
        proj_cb = ttk.Combobox(top, textvariable=self._projection_var,
                                values=list(PROJECTIONS),
                                state='readonly', width=8)
        proj_cb.grid(row=0, column=5)
        proj_cb.bind('<<ComboboxSelected>>',
                     lambda e: self._on_curve_changed())

        ttk.Label(top, text="Cycles:").grid(row=0, column=6,
                                              padx=(12, 2))
        ttk.Spinbox(top, from_=0.25, to=12.0, increment=0.25,
                    textvariable=self._cycles_var, width=6,
                    command=self._on_curve_changed).grid(row=0, column=7)
        self._cycles_var.trace_add('write',
                                    lambda *_a: self._on_curve_changed())

        ttk.Label(top, text="Shaft:").grid(row=0, column=8,
                                             padx=(12, 2))
        shaft_cb = ttk.Combobox(top, textvariable=self._shaft_mode_var,
                                 values=list(SHAFT_MODES),
                                 state='readonly', width=8)
        shaft_cb.grid(row=0, column=9)
        shaft_cb.bind('<<ComboboxSelected>>',
                      lambda e: self._on_shaft_mode_change())

        ttk.Checkbutton(top, text="Show video",
                        variable=self._show_video_var,
                        command=self._toggle_video_panel).grid(
            row=0, column=10, padx=(12, 0))

        # --- Row 1: split ---------------------------------------------
        # Left pane: 2D curve canvas (takes majority width).
        # Right pane: vertical stack — video frame above, shaft canvas below.
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky='nsew', padx=6, pady=(2, 2))

        self._left_frame = ttk.LabelFrame(paned, text="Trochoid (2D)",
                                          padding=4)
        paned.add(self._left_frame, weight=3)

        self._right_frame = ttk.Frame(paned)
        paned.add(self._right_frame, weight=4)
        self._right_frame.columnconfigure(0, weight=1)
        self._right_frame.rowconfigure(0, weight=2)  # video
        self._right_frame.rowconfigure(1, weight=3)  # shaft

        self._video_frame = ttk.LabelFrame(
            self._right_frame,
            text="Video (drop a video file here or click Browse)",
            padding=4)
        self._video_frame.grid(row=0, column=0, sticky='nsew',
                               padx=(2, 0), pady=(0, 2))
        self._video_frame.columnconfigure(0, weight=1)
        self._video_frame.rowconfigure(0, weight=1)
        placeholder = ("Drop a video file here  (.mp4 / .mov / .mkv / ...)"
                       if _HAVE_CV2 and _HAVE_PIL
                       else "Video playback unavailable — install "
                            "opencv-python + Pillow")
        self._video_widget = tk.Label(
            self._video_frame, text=placeholder,
            background='#111', foreground='#bbbbbb', anchor='center',
            font=('TkDefaultFont', 11))
        self._video_widget.grid(row=0, column=0, sticky='nsew')
        if _HAVE_DND:
            try:
                self._video_widget.drop_target_register('DND_Files')
                self._video_widget.dnd_bind('<<Drop>>',
                                             self._on_video_drop)
            except Exception as e:
                print(f"[trochoid] DnD init failed: {e}")

        self._shaft_frame = ttk.LabelFrame(
            self._right_frame, text="Shaft (shadow)", padding=4)
        self._shaft_frame.grid(row=1, column=0, sticky='nsew',
                               padx=(2, 0), pady=(2, 0))
        self._shaft_frame.columnconfigure(0, weight=1)
        self._shaft_frame.rowconfigure(0, weight=1)

        self._left_frame.columnconfigure(0, weight=1)
        self._left_frame.rowconfigure(0, weight=1)
        self._canvas_frame = ttk.Frame(self._left_frame)
        self._canvas_frame.grid(row=0, column=0, sticky='nsew')
        self._canvas_frame.columnconfigure(0, weight=1)
        self._canvas_frame.rowconfigure(0, weight=1)

        # --- Row 2: playback bar -------------------------------------
        play_row = ttk.Frame(self, padding=(8, 4))
        play_row.grid(row=2, column=0, sticky='ew')
        play_row.columnconfigure(1, weight=1)
        self._play_btn = ttk.Button(play_row, text="\u25b6 Play", width=9,
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
        speed_cb = ttk.Combobox(play_row, textvariable=self._play_speed_var,
                                 values=['0.25', '0.5', '1.0', '2.0', '4.0'],
                                 width=6, state='readonly')
        speed_cb.grid(row=0, column=4)
        speed_cb.set('1.0')

        # --- Row 3: electrode positions ------------------------------
        ep = ttk.LabelFrame(
            self, text="Electrode positions (0 = base, 1 = tip)",
            padding=(8, 4))
        ep.grid(row=3, column=0, sticky='ew', padx=8, pady=(2, 2))
        for i, label in enumerate(ELEC_LABELS):
            ttk.Label(ep, text=label, foreground=ELEC_COLORS[i],
                      width=3).grid(row=0, column=i * 3, padx=(0, 4))
            ttk.Scale(ep, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                      variable=self._pos_vars[i], length=150,
                      command=lambda v: self._update_frame(
                          force=True)).grid(
                row=0, column=i * 3 + 1, padx=(0, 4))
            ent = ttk.Entry(ep, textvariable=self._pos_vars[i], width=6)
            ent.grid(row=0, column=i * 3 + 2, padx=(0, 12))
            ent.bind('<Return>',
                     lambda e: self._update_frame(force=True))
        ttk.Label(ep, text="Proximity reach:").grid(
            row=0, column=13, padx=(12, 2))
        ttk.Scale(ep, from_=0.02, to=0.5, orient=tk.HORIZONTAL,
                  variable=self._reach_var, length=120,
                  command=lambda v: self._update_frame(
                      force=True)).grid(row=0, column=14)

        # --- Row 4: video controls -----------------------------------
        vc = ttk.Frame(self, padding=(8, 2, 8, 8))
        vc.grid(row=4, column=0, sticky='ew')
        vc.columnconfigure(2, weight=1)
        ttk.Label(vc, text="Video:").grid(row=0, column=0, padx=(0, 4))
        self._video_path_lbl = ttk.Label(vc, text="(none)",
                                          foreground='#666', width=32,
                                          anchor='w')
        self._video_path_lbl.grid(row=0, column=1, sticky='w')
        ttk.Button(vc, text="Browse\u2026",
                   command=self._browse_video).grid(
            row=0, column=2, sticky='e', padx=(4, 4))
        ttk.Button(vc, text="Clear",
                   command=self._clear_video).grid(row=0, column=3)
        ttk.Label(vc, text="Offset (s):").grid(
            row=0, column=4, padx=(12, 2))
        offs = ttk.Spinbox(vc, from_=-3600.0, to=3600.0,
                           increment=0.05,
                           textvariable=self._video_offset_var, width=8,
                           command=lambda: self._update_video_frame(force=True))
        offs.grid(row=0, column=5)
        offs.bind('<Return>',
                  lambda e: self._update_video_frame(force=True))
        ttk.Button(vc, text="Sync here",
                   command=self._sync_here).grid(row=0, column=6,
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
                print(f"[trochoid] load failed: {e}")
                self._funscript = None
                self._source_label = f"(load failed: {e})"
        else:
            t = np.linspace(0, 20, 1200)
            y = 0.5 + 0.45 * np.sin(2 * np.pi * 0.25 * t)
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

        if path and _HAVE_CV2 and _HAVE_PIL:
            base = (path[:-len('.funscript')]
                    if path.endswith('.funscript') else path)
            for ext in ('.mp4', '.mov', '.mkv', '.m4v',
                         '.avi', '.webm'):
                vp = base + ext
                if os.path.isfile(vp):
                    self._open_video(vp)
                    break

    # ═════════════════════════════════════════════════════════ curve

    def _active_family(self) -> str:
        f = str(self._family_var.get())
        return f if f in CURVE_FAMILIES else 'hypo'

    def _active_params(self) -> dict:
        fam = self._active_family()
        return dict(self._params_by_family.get(fam, {}))

    def _active_projection(self) -> str:
        p = str(self._projection_var.get())
        return p if p in PROJECTIONS else 'x'

    def _recompute_lobes(self):
        """Find peaks (lobes) of the SELECTED projection along the
        dense curve and assign each one an equal slice of shaft [0,1].

        Lobes are local maxima of the user-chosen projection (x/y/
        radius) — the same scalar that drives the shadow marker. This
        way the lobe count matches what the user sees in shadow mode
        and stays consistent when they switch projections. A minimum
        prominence threshold (8% of dynamic range) filters out noise
        wiggles. Bounds for each lobe are the surrounding valleys.
        """
        self._lobes = []
        if (self._curve_xy_cache is None or self._shadow_lookup_t is None
                or self._shadow_lookup_v is None):
            return
        theta = self._shadow_lookup_t
        # Peak detection on the normalized projection (same one used
        # for the shadow marker).
        r = np.asarray(self._shadow_lookup_v, dtype=float)
        n = len(r)
        if n < 5:
            return
        r_max = float(r.max())
        r_min = float(r.min())
        if r_max - r_min < 1e-9:
            return
        # Prominence: at least 8% of total dynamic range.
        min_prom = 0.08 * (r_max - r_min)

        # Find local maxima and minima by sign changes of diff.
        d = np.diff(r)
        sign = np.sign(d)
        # Replace zeros with the previous sign so flats don't confuse us.
        last = 1.0
        for i in range(len(sign)):
            if sign[i] == 0:
                sign[i] = last
            else:
                last = sign[i]
        peaks_idx = []
        valleys_idx = [0]
        for i in range(1, len(sign)):
            if sign[i - 1] > 0 and sign[i] < 0:
                peaks_idx.append(i)
            elif sign[i - 1] < 0 and sign[i] > 0:
                valleys_idx.append(i)
        valleys_idx.append(n - 1)

        # Filter peaks by prominence relative to the nearest valleys.
        filtered = []
        for p in peaks_idx:
            left_v = max([v for v in valleys_idx if v < p], default=0)
            right_v = min([v for v in valleys_idx if v > p], default=n - 1)
            prom = r[p] - max(r[left_v], r[right_v])
            if prom >= min_prom:
                filtered.append((p, left_v, right_v))
        if not filtered:
            # Fall back to the single global maximum.
            p = int(np.argmax(r))
            filtered = [(p, 0, n - 1)]

        # Sort by theta order so lobes wrap the shaft base→tip.
        filtered.sort(key=lambda e: theta[e[0]])
        n_lobes = len(filtered)
        for i, (p, lv, rv) in enumerate(filtered):
            self._lobes.append({
                'theta_center': float(theta[p]),
                'theta_start': float(theta[lv]),
                'theta_end': float(theta[rv]),
                'peak_r': float(r[p] / r_max),
                'shaft_center': (i + 0.5) / n_lobes,
                'shaft_width': 1.0 / n_lobes,
            })

    def _recompute_curve(self):
        """Rebuild the dense curve + shadow-projection lookup table."""
        family = self._active_family()
        params = self._active_params()
        try:
            theta_max = get_family_theta_max(family)
            theta_dense = np.linspace(0.0, theta_max, 1500)
            xc, yc = curve_xy(theta_dense, family, params)
            finite = np.isfinite(xc) & np.isfinite(yc)
            xc = np.where(finite, xc, 0.0)
            yc = np.where(finite, yc, 0.0)
            self._curve_xy_cache = (xc, yc)

            # Project to scalar, then normalize to [0, 1] using a
            # dense second pass to get a stable min/max.
            proj = self._active_projection()
            if proj == 'radius':
                vals = np.sqrt(xc * xc + yc * yc)
            elif proj == 'y':
                vals = yc
            else:
                vals = xc
            vmin, vmax = float(np.min(vals)), float(np.max(vals))
            if vmax - vmin < 1e-9:
                norm = np.full_like(vals, 0.5)
            else:
                norm = (vals - vmin) / (vmax - vmin)
            self._shadow_lookup_t = theta_dense
            self._shadow_lookup_v = np.clip(norm, 0.0, 1.0)
        except Exception as e:
            print(f"[trochoid] curve recompute failed: {e}")
            self._curve_xy_cache = None
            self._shadow_lookup_t = None
            self._shadow_lookup_v = None

        # Push the new curve into the figure if it already exists.
        if self._curve_line_artist is not None and self._curve_xy_cache is not None:
            xc, yc = self._curve_xy_cache
            # Normalize to unit-radius reference so different families share scale.
            r = np.sqrt(xc * xc + yc * yc)
            rmax = float(r.max()) if r.size else 1.0
            if rmax < 1e-9:
                rmax = 1.0
            self._curve_line_artist.set_data(xc / rmax, yc / rmax)
            if self._ax_curve is not None:
                self._ax_curve.set_xlim(-1.15, 1.15)
                self._ax_curve.set_ylim(-1.15, 1.15)

        # Detect lobes for the lobe-wrap shaft mode, then rebuild the
        # lobe bar artists if the shaft figure already exists.
        self._recompute_lobes()
        self._rebuild_lobe_artists()

    def _on_curve_changed(self):
        self._curve_trail_buf = []
        self._recompute_curve()
        self._update_frame(force=True)

    def _rebuild_lobe_artists(self):
        """Tear down and rebuild the lobe bar artists on the shaft axis
        to match the current `_lobes` list. Called whenever the curve
        changes."""
        if self._ax_shaft is None:
            return
        from matplotlib.patches import Rectangle
        for a in self._lobe_bar_artists:
            try:
                a.remove()
            except Exception:
                pass
        for t in self._lobe_label_artists:
            try:
                t.remove()
            except Exception:
                pass
        self._lobe_bar_artists = []
        self._lobe_label_artists = []
        if self._active_lobe_outline is not None:
            try:
                self._active_lobe_outline.remove()
            except Exception:
                pass
            self._active_lobe_outline = None

        base_y = self._shaft_y0 + self._shaft_h + 0.02
        max_h = 0.55
        for i, lobe in enumerate(self._lobes):
            w = lobe['shaft_width'] * 0.86  # small gap between bars
            x = lobe['shaft_center'] - w / 2
            h = max_h * lobe['peak_r']
            # Color by lobe index so adjacent lobes are distinguishable.
            import matplotlib as _mpl
            cmap = _mpl.colormaps.get_cmap('viridis')
            color = cmap(0.15 + 0.7 * (i / max(1, len(self._lobes) - 1)))
            bar = Rectangle(
                (x, base_y), w, h,
                facecolor=color, edgecolor='#222',
                linewidth=0.6, alpha=0.75, zorder=3)
            self._ax_shaft.add_patch(bar)
            self._lobe_bar_artists.append(bar)
            txt = self._ax_shaft.text(
                lobe['shaft_center'], base_y + h + 0.02,
                str(i + 1), ha='center', va='bottom',
                fontsize=7, color='#333', zorder=4)
            self._lobe_label_artists.append(txt)

        # Outline rectangle used to highlight the active lobe.
        self._active_lobe_outline = Rectangle(
            (0.0, base_y), 0.0, max_h,
            facecolor='none', edgecolor='#d62728',
            linewidth=1.8, zorder=5)
        self._ax_shaft.add_patch(self._active_lobe_outline)
        # Show/hide according to current mode.
        self._apply_shaft_mode_visibility()

    def _apply_shaft_mode_visibility(self):
        mode = str(self._shaft_mode_var.get())
        is_lobes = (mode == 'lobes')
        if self._shadow_marker_artist is not None:
            self._shadow_marker_artist.set_visible(not is_lobes)
        if self._shadow_trail_artist is not None:
            self._shadow_trail_artist.set_visible(not is_lobes)
        for bar in self._lobe_bar_artists:
            bar.set_visible(is_lobes)
        for t in self._lobe_label_artists:
            t.set_visible(is_lobes)
        if self._active_lobe_outline is not None:
            self._active_lobe_outline.set_visible(is_lobes)

    def _on_shaft_mode_change(self):
        self._shadow_trail_buf = []
        self._apply_shaft_mode_visibility()
        self._update_frame(force=True)

    def _active_lobe_index(self, theta: float) -> int:
        """Return the index of the lobe whose (theta_start, theta_end)
        range contains theta. Ties resolved to the closest center."""
        if not self._lobes:
            return -1
        # Since theta wraps modulo theta_max at update time, find the
        # lobe whose [start, end] span contains theta; if none (rare
        # around the seam), fall back to the lobe whose center is
        # nearest.
        for i, lobe in enumerate(self._lobes):
            if lobe['theta_start'] <= theta <= lobe['theta_end']:
                return i
        # Fallback: nearest center
        centers = np.array([l['theta_center'] for l in self._lobes])
        return int(np.argmin(np.abs(centers - theta)))

    # ═════════════════════════════════════════════════════ figure

    def _build_figure(self):
        from matplotlib.figure import Figure
        from matplotlib.patches import Rectangle
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        # Two separate figures — one for the left (2D curve) canvas,
        # one for the right (shaft) canvas — so each fills its pane.
        # --- Left: 2D curve --------------------------------------
        fig_curve = Figure(figsize=(5.0, 5.0), dpi=95)
        ax_curve = fig_curve.add_subplot(1, 1, 1)
        ax_curve.set_facecolor('#fafafa')
        ax_curve.set_aspect('equal', adjustable='datalim')
        ax_curve.grid(True, alpha=0.25)
        ax_curve.set_xlim(-1.15, 1.15)
        ax_curve.set_ylim(-1.15, 1.15)
        ax_curve.tick_params(labelsize=7)
        # Unit circle reference
        tt = np.linspace(0, 2 * np.pi, 200)
        ax_curve.plot(np.cos(tt), np.sin(tt),
                      color='#cccccc', linewidth=0.6,
                      linestyle='--', zorder=1)
        self._curve_line_artist, = ax_curve.plot(
            [], [], color='#4a90d9', linewidth=1.2, alpha=0.6,
            zorder=2)
        self._curve_trail_artist, = ax_curve.plot(
            [], [], color='#d62728', linewidth=1.4, alpha=0.45,
            zorder=3)
        self._curve_pen_artist, = ax_curve.plot(
            [0.0], [0.0], marker='o', color='#d62728',
            markersize=11, markeredgecolor='black',
            markeredgewidth=1.0, zorder=5)
        ax_curve.set_title("Trochoid curve + pen",
                           fontsize=10)
        fig_curve.tight_layout(pad=0.6)
        canvas_curve = FigureCanvasTkAgg(fig_curve, self._canvas_frame)
        canvas_curve.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        self._fig = fig_curve
        self._canvas = canvas_curve
        self._ax_curve = ax_curve
        # Seed with the current curve.
        if self._curve_xy_cache is not None:
            xc, yc = self._curve_xy_cache
            r = np.sqrt(xc * xc + yc * yc)
            rmax = float(r.max()) if r.size else 1.0
            if rmax < 1e-9:
                rmax = 1.0
            self._curve_line_artist.set_data(xc / rmax, yc / rmax)

        # --- Right: shaft -----------------------------------------
        fig_shaft = Figure(figsize=(5.0, 2.8), dpi=95)
        ax_shaft = fig_shaft.add_subplot(1, 1, 1)
        ax_shaft.set_facecolor('#fafafa')
        shaft_y0 = 0.35
        shaft_h = 0.14
        ax_shaft.add_patch(Rectangle(
            (0.0, shaft_y0), 1.0, shaft_h,
            facecolor='#dcdcdc', edgecolor='#444',
            linewidth=0.8, zorder=1))
        self._shaft_y0 = shaft_y0
        self._shaft_h = shaft_h

        # Shadow trail (faint)
        self._shadow_trail_artist, = ax_shaft.plot(
            [], [], color='#d62728', linewidth=1.4,
            alpha=0.35, zorder=2)
        # Shadow marker (moving)
        self._shadow_marker_artist, = ax_shaft.plot(
            [0.0], [shaft_y0 + shaft_h / 2],
            marker='o', color='#d62728', markersize=12,
            markeredgecolor='black', markeredgewidth=1.0,
            zorder=6)

        # Electrodes + intensity bars
        self._elec_band_artists = []
        self._elec_label_artists = []
        self._intensity_bar_artists = []
        self._intensity_text_artists = []
        bw = 0.04
        bar_base_y = shaft_y0 + shaft_h + 0.05
        bar_max_h = 0.35
        for i in range(4):
            pos = float(self._pos_vars[i].get())
            band = Rectangle(
                (pos - bw / 2, shaft_y0), bw, shaft_h,
                facecolor=ELEC_COLORS[i], edgecolor='black',
                linewidth=0.7, alpha=0.5, zorder=3)
            ax_shaft.add_patch(band)
            self._elec_band_artists.append(band)
            lbl = ax_shaft.text(
                pos, shaft_y0 - 0.06, ELEC_LABELS[i],
                ha='center', va='top', fontsize=10,
                color=ELEC_COLORS[i], fontweight='bold', zorder=4)
            self._elec_label_artists.append(lbl)
            bar = Rectangle(
                (pos - 0.02, bar_base_y), 0.04, 0.0,
                facecolor=ELEC_COLORS[i], edgecolor=ELEC_COLORS[i],
                linewidth=0.6, alpha=0.9, zorder=4)
            ax_shaft.add_patch(bar)
            self._intensity_bar_artists.append(bar)
            txt = ax_shaft.text(
                pos, bar_base_y + bar_max_h + 0.04, "0.00",
                ha='center', va='bottom', fontsize=9,
                color=ELEC_COLORS[i], zorder=4)
            self._intensity_text_artists.append(txt)
        self._bar_base_y = bar_base_y
        self._bar_max_h = bar_max_h

        ax_shaft.set_xlim(-0.02, 1.02)
        ax_shaft.set_ylim(0.0, 1.35)
        ax_shaft.set_yticks([])
        ax_shaft.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax_shaft.set_xlabel(
            'Shaft (0 = base, 1 = tip)   — shadow projection',
            fontsize=9)
        ax_shaft.set_title(
            "Shaft — shadow of the pen via projection",
            fontsize=10)
        fig_shaft.tight_layout(pad=0.5)
        canvas_shaft = FigureCanvasTkAgg(fig_shaft, self._shaft_frame)
        canvas_shaft.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        self._fig_shaft = fig_shaft
        self._canvas_shaft = canvas_shaft
        self._ax_shaft = ax_shaft

    # ═════════════════════════════════════════════════════ update

    def _pen_xy_at(self, theta: float):
        """Interpolate the pen's (x, y) on the unit-normalized curve."""
        if self._curve_xy_cache is None or self._shadow_lookup_t is None:
            return 0.0, 0.0
        xc, yc = self._curve_xy_cache
        t_arr = self._shadow_lookup_t
        r = np.sqrt(xc * xc + yc * yc)
        rmax = float(r.max()) if r.size else 1.0
        if rmax < 1e-9:
            rmax = 1.0
        # Clamp theta into the sampled range.
        if theta < t_arr[0]:
            theta = float(t_arr[0])
        elif theta > t_arr[-1]:
            theta = float(t_arr[-1])
        xp = float(np.interp(theta, t_arr, xc)) / rmax
        yp = float(np.interp(theta, t_arr, yc)) / rmax
        return xp, yp

    def _shadow_at(self, theta: float) -> float:
        if self._shadow_lookup_t is None or self._shadow_lookup_v is None:
            return 0.5
        if theta < self._shadow_lookup_t[0]:
            theta = float(self._shadow_lookup_t[0])
        elif theta > self._shadow_lookup_t[-1]:
            theta = float(self._shadow_lookup_t[-1])
        return float(np.interp(theta, self._shadow_lookup_t,
                                self._shadow_lookup_v))

    def _signal_y_at(self, t: float) -> float:
        if self._t_arr is None or len(self._t_arr) == 0:
            return 0.5
        return float(np.clip(np.interp(t, self._t_arr, self._y_arr),
                              0.0, 1.0))

    def _update_frame(self, force=False):
        if self._fig is None or self._canvas is None:
            return

        t = self._playhead_t
        y = self._signal_y_at(t)
        try:
            cycles = max(0.01, float(self._cycles_var.get()))
        except (tk.TclError, ValueError):
            cycles = 1.0
        family = self._active_family()
        try:
            theta_max = get_family_theta_max(family)
        except Exception:
            theta_max = 2.0 * np.pi
        # theta is folded into the curve's natural range via modulo,
        # so cycles > 1 just wraps the pen around the curve multiple
        # times as y sweeps 0→1.
        theta = (y * theta_max * cycles) % theta_max

        # Pen position on the 2D curve.
        xp, yp = self._pen_xy_at(theta)
        self._curve_pen_artist.set_data([xp], [yp])

        # Curve trail (short, last 0.6 s).
        self._curve_trail_buf.append((t, xp, yp))
        cutoff = t - 0.6
        self._curve_trail_buf = [e for e in self._curve_trail_buf
                                  if e[0] >= cutoff]
        if len(self._curve_trail_buf) >= 2:
            arr = np.asarray(self._curve_trail_buf)
            self._curve_trail_artist.set_data(arr[:, 1], arr[:, 2])
        else:
            self._curve_trail_artist.set_data([], [])

        # Shadow on the shaft — always compute (used for electrode
        # proximity) even when the shaft is showing lobes. In lobes
        # mode we override shadow_x to the active lobe's center.
        shadow_x = self._shadow_at(theta)
        shaft_mode = str(self._shaft_mode_var.get())
        active_lobe = -1
        if shaft_mode == 'lobes' and self._lobes:
            active_lobe = self._active_lobe_index(theta)
            if 0 <= active_lobe < len(self._lobes):
                shadow_x = self._lobes[active_lobe]['shaft_center']

        # Shadow marker — only visible in shadow mode.
        self._shadow_marker_artist.set_data(
            [shadow_x], [self._shaft_y0 + self._shaft_h / 2])

        # Shadow trail.
        self._shadow_trail_buf.append((t, shadow_x))
        self._shadow_trail_buf = [e for e in self._shadow_trail_buf
                                   if e[0] >= cutoff]
        if shaft_mode == 'shadow' and len(self._shadow_trail_buf) >= 2:
            arr = np.asarray(self._shadow_trail_buf)
            ys = np.full_like(arr[:, 1], self._shaft_y0 + self._shaft_h / 2)
            self._shadow_trail_artist.set_data(arr[:, 1], ys)
        else:
            self._shadow_trail_artist.set_data([], [])

        # Active-lobe outline — only shown in lobes mode.
        if (shaft_mode == 'lobes' and self._active_lobe_outline is not None
                and 0 <= active_lobe < len(self._lobes)):
            lobe = self._lobes[active_lobe]
            w = lobe['shaft_width'] * 0.86
            x = lobe['shaft_center'] - w / 2
            base_y = self._shaft_y0 + self._shaft_h + 0.02
            max_h = 0.55
            self._active_lobe_outline.set_bounds(
                x, base_y, w, max_h * lobe['peak_r'])

        # Electrode bands track their sliders.
        bw = 0.04
        try:
            reach = max(1e-3, float(self._reach_var.get()))
        except (tk.TclError, ValueError):
            reach = 0.18
        for i, rect in enumerate(self._elec_band_artists):
            try:
                ep = float(self._pos_vars[i].get())
            except (tk.TclError, ValueError):
                ep = [0.85, 0.65, 0.45, 0.25][i]
            rect.set_x(ep - bw / 2)
            self._elec_label_artists[i].set_position(
                (ep, self._shaft_y0 - 0.06))

        # Intensity bars via proximity of the shadow to each electrode.
        for i, axis in enumerate(('e1', 'e2', 'e3', 'e4')):
            try:
                ep = float(self._pos_vars[i].get())
            except (tk.TclError, ValueError):
                ep = [0.85, 0.65, 0.45, 0.25][i]
            d = abs(shadow_x - ep)
            v = max(0.0, min(1.0, 1.0 - d / reach))
            bar = self._intensity_bar_artists[i]
            bar.set_x(ep - 0.02)
            bar.set_y(self._bar_base_y)
            bar.set_height(v * self._bar_max_h)
            self._intensity_text_artists[i].set_position(
                (ep, self._bar_base_y + self._bar_max_h + 0.04))
            self._intensity_text_artists[i].set_text(f"{v:.2f}")

        if self._t_arr is not None and len(self._t_arr):
            self._time_lbl.config(
                text=f"{t:.2f} / {float(self._t_arr[-1]):.2f} s")

        self._canvas.draw_idle()
        if hasattr(self, '_canvas_shaft'):
            self._canvas_shaft.draw_idle()
        self._update_video_frame()

    # ═════════════════════════════════════════════════════ playback

    def _on_scrub(self, _val):
        try:
            t = float(self._scrub_var.get())
        except (tk.TclError, ValueError):
            return
        self._playhead_t = t
        self._update_frame()

    def _toggle_play(self):
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        self._update_video_frame(force=True)
        self._playing = True
        self._play_btn.config(text="\u23f8 Pause")
        self._last_tick_wall = time.monotonic()
        self._tick()

    def _stop_playback(self):
        self._playing = False
        self._play_btn.config(text="\u25b6 Play")
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

    # ═════════════════════════════════════════════════════ video

    def _toggle_video_panel(self):
        if not hasattr(self, '_video_frame'):
            return
        if bool(self._show_video_var.get()):
            self._video_frame.grid()
            self._right_frame.rowconfigure(0, weight=2)
            self._update_video_frame(force=True)
        else:
            self._video_frame.grid_remove()
            self._right_frame.rowconfigure(0, weight=0)

    # Video handlers (_open_video, _clear_video, _browse_video,
    # _on_video_drop, _update_video_frame, _sync_here) come from
    # VideoPlaybackMixin.

    def _on_close(self):
        self._stop_playback()
        if self._video_cap is not None:
            try:
                self._video_cap.release()
            except Exception:
                pass
        self.destroy()


def main():
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except Exception:
        root = tk.Tk()
    root.withdraw()

    class _Stub:
        input_files = sys.argv[1:]
        current_config = {}
    TrochoidViewer(root, _Stub())
    root.mainloop()


if __name__ == '__main__':
    main()
