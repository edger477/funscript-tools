"""
Signal Analyzer popup — examines a loaded funscript and recommends
optimal processing settings based on signal characteristics.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import warnings


class SignalAnalyzer(tk.Toplevel):
    """Popup window: analyze a funscript and recommend settings."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.title("Signal Analyzer")
        self.geometry("900x750")
        self.minsize(750, 550)
        self.main_window = main_window

        self._build_ui()
        self._run_analysis()

    # ── UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top bar: source label on the left, trochoid toggle on the right.
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 0))
        top_bar.columnconfigure(0, weight=1)

        self._source_label = ttk.Label(top_bar, text="Loading...",
                                       font=('TkDefaultFont', 10, 'bold'))
        self._source_label.grid(row=0, column=0, sticky='w')

        # Trochoid quantization toggle. Defaults to whatever the global
        # config has, but the user can flip it independently to A/B the
        # metrics and recommendations.
        tq_default = bool(self.main_window.current_config
                          .get('trochoid_quantization', {})
                          .get('enabled', False))
        self._tq_apply_var = tk.BooleanVar(value=tq_default)
        ttk.Checkbutton(
            top_bar,
            text="Apply trochoid quantization to source",
            variable=self._tq_apply_var,
            command=self._run_analysis,
        ).grid(row=0, column=1, sticky='e', padx=(10, 0))

        # Main content: paned — top for charts, bottom for recommendations
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)

        # Top: summary + charts
        self._charts_frame = ttk.Frame(paned)
        paned.add(self._charts_frame, weight=2)
        self._charts_frame.columnconfigure(0, weight=1)
        self._charts_frame.rowconfigure(1, weight=1)

        # Summary card
        self._summary_frame = ttk.LabelFrame(self._charts_frame, text="Summary", padding="8")
        self._summary_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        self._summary_label = ttk.Label(self._summary_frame, text="Analyzing...",
                                        wraplength=800, justify=tk.LEFT)
        self._summary_label.pack(anchor='w')

        # Chart canvas placeholder
        self._chart_canvas_frame = ttk.Frame(self._charts_frame)
        self._chart_canvas_frame.grid(row=1, column=0, sticky='nsew')
        self._chart_canvas_frame.columnconfigure(0, weight=1)
        self._chart_canvas_frame.rowconfigure(0, weight=1)

        # Bottom: recommendations table
        rec_frame = ttk.Frame(paned)
        paned.add(rec_frame, weight=1)
        rec_frame.columnconfigure(0, weight=1)
        rec_frame.rowconfigure(0, weight=1)

        ttk.Label(rec_frame, text="Recommendations",
                  font=('TkDefaultFont', 10, 'bold')).grid(
            row=0, column=0, sticky='w', pady=(5, 2))

        # Treeview: Setting | Current | Recommended | Reason
        cols = ('setting', 'current', 'recommended', 'reason')
        self._tree = ttk.Treeview(rec_frame, columns=cols, show='headings', height=10)
        self._tree.heading('setting', text='Setting')
        self._tree.heading('current', text='Current')
        self._tree.heading('recommended', text='Recommended')
        self._tree.heading('reason', text='Reason')
        self._tree.column('setting', width=200, minwidth=150)
        self._tree.column('current', width=90, minwidth=60)
        self._tree.column('recommended', width=90, minwidth=60)
        self._tree.column('reason', width=400, minwidth=200)
        self._tree.grid(row=1, column=0, sticky='nsew')

        tree_sb = ttk.Scrollbar(rec_frame, orient=tk.VERTICAL, command=self._tree.yview)
        tree_sb.grid(row=1, column=1, sticky='ns')
        self._tree.config(yscrollcommand=tree_sb.set)

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, pady=10)
        ttk.Button(btn_frame, text="Apply All Recommendations",
                   command=self._apply_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Apply Selected",
                   command=self._apply_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close",
                   command=self.destroy).pack(side=tk.LEFT, padx=5)

    # ── Analysis ─────────────────────────────────────────────────────

    def _run_analysis(self):
        """Load funscript, analyze, populate UI."""
        import numpy as np
        from funscript import Funscript
        from processing.signal_analysis import analyze_funscript

        # Load source
        fs = None
        source_name = "No file loaded"
        mw = self.main_window
        if hasattr(mw, 'input_files') and mw.input_files:
            path = mw.input_files[0]
            if os.path.isfile(path) and path.endswith('.funscript'):
                try:
                    fs = Funscript.from_file(path)
                    source_name = os.path.basename(path)
                except Exception as e:
                    messagebox.showerror("Load Error", str(e), parent=self)
                    return

        if fs is None:
            # Generate synthetic for demo
            t = np.linspace(0, 30, 1500)
            y = np.piecewise(t, [t < 10, (t >= 10) & (t < 20), t >= 20], [
                lambda tt: 0.5 + 0.4 * np.sin(2 * np.pi * 1.0 * tt),
                lambda tt: 0.5 + 0.1 * np.sin(2 * np.pi * 0.3 * tt),
                lambda tt: 0.5 + 0.4 * np.sin(2 * np.pi * 2.5 * tt),
            ])
            fs = Funscript(t, y)
            source_name = "Demo (synthetic signal — load a file for real analysis)"

        # Optional trochoid quantization. When this checkbox is on, all
        # metrics, charts, and recommendations are computed against the
        # quantized signal — same signal the processor would produce.
        config = self.main_window.current_config
        tq_cfg = config.get('trochoid_quantization', {}) or {}
        if hasattr(self, '_tq_apply_var') and self._tq_apply_var.get():
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
                fs = quantize_to_curve(
                    fs, int(tq_cfg.get('n_points', 23)),
                    family, family_params,
                    str(tq_cfg.get('projection', 'radius')))
                if tq_cfg.get('deduplicate_holds', False):
                    fs = deduplicate_holds(fs)
                source_name = (f"{source_name}  "
                               f"[trochoid: {family}, "
                               f"N={int(tq_cfg.get('n_points', 23))}]")
            except (ValueError, TypeError) as e:
                print(f"[analyzer] trochoid quantization skipped: {e}")

        self._source_label.config(text=f"Source: {source_name}")

        # Analyze
        self._result = analyze_funscript(fs)
        self._source_fs = fs

        # Populate summary
        c = self._result['classification']
        m = self._result['metrics']
        summary = (
            f"{c['tag']}\n\n"
            f"{c['description']}\n\n"
            f"Strokes: {m['stroke']['stroke_count']}  |  "
            f"Rate: {m['stroke']['strokes_per_minute']:.0f} SPM  |  "
            f"Amplitude: {m['stroke']['mean_amplitude']:.2f} (mean)  |  "
            f"Rest: {m['temporal']['rest_fraction']*100:.0f}%  |  "
            f"Dominant freq: {m['frequency']['dominant_freq_hz']:.2f} Hz"
        )
        self._summary_label.config(text=summary)

        # Populate recommendations
        self._populate_recommendations()

        # Draw charts
        self._draw_charts()

    def _get_current_value(self, setting: str):
        """Look up the current config value for a dotted setting path."""
        config = self.main_window.current_config
        parts = setting.split('.')
        obj = config
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return '—'
        return obj

    def _populate_recommendations(self):
        """Fill the treeview with recommendations."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        self._recs = self._result['recommendations']
        for rec in self._recs:
            current = self._get_current_value(rec['setting'])
            current_str = str(current)
            rec_str = str(rec['value'])
            # Highlight if different
            tags = ()
            if str(current) != str(rec['value']):
                tags = ('changed',)
            self._tree.insert('', 'end',
                              values=(rec['setting'], current_str,
                                      rec_str, rec['reason']),
                              tags=tags)

        self._tree.tag_configure('changed', foreground='#d32f2f')

    # ── Charts ───────────────────────────────────────────────────────

    def _draw_charts(self):
        """Draw the 2x2 analysis charts."""
        try:
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            return

        for w in self._chart_canvas_frame.winfo_children():
            w.destroy()

        m = self._result['metrics']
        fs = self._source_fs
        t = np.asarray(fs.x, dtype=float)
        y = np.asarray(fs.y, dtype=float)

        fig = Figure(figsize=(9, 3.5), dpi=85)
        fig.patch.set_facecolor('#f5f5f5')

        # 1) Position histogram
        ax1 = fig.add_subplot(1, 4, 1)
        pos = m['position']
        centers = [(pos['position_bin_edges'][i] + pos['position_bin_edges'][i+1]) / 2
                   for i in range(len(pos['position_histogram']))]
        ax1.barh(centers, pos['position_histogram'], height=0.045,
                 color='#1976D2', alpha=0.7)
        ax1.set_ylabel('Position', fontsize=7)
        ax1.set_xlabel('Density', fontsize=7)
        ax1.set_title('Position Dist.', fontsize=8)
        ax1.set_ylim(0, 1)
        ax1.tick_params(labelsize=6)

        # 2) Amplitude distribution
        ax2 = fig.add_subplot(1, 4, 2)
        amps = m['stroke']['amplitudes']
        if amps:
            ax2.hist(amps, bins=20, color='#4CAF50', alpha=0.7, edgecolor='white')
            ax2.axvline(m['stroke']['mean_amplitude'], color='#d32f2f',
                        linewidth=1, linestyle='--', label=f"mean={m['stroke']['mean_amplitude']:.2f}")
            ax2.legend(fontsize=6)
        ax2.set_xlabel('Amplitude', fontsize=7)
        ax2.set_title('Stroke Amplitude', fontsize=8)
        ax2.tick_params(labelsize=6)

        # 3) Speed over time (sampled for performance)
        ax3 = fig.add_subplot(1, 4, 3)
        dt = np.diff(t)
        dy = np.abs(np.diff(y))
        inst_speed = np.where(dt > 0, dy / dt, 0.0)
        # Downsample for plotting
        step = max(1, len(inst_speed) // 500)
        ax3.plot(t[1::step], inst_speed[::step], color='#FF9800',
                 linewidth=0.5, alpha=0.7)
        # Shade rest periods
        for rs, re in m['temporal']['rest_periods']:
            ax3.axvspan(rs, re, color='#999', alpha=0.15)
        ax3.set_xlabel('Time (s)', fontsize=7)
        ax3.set_title('Instant Speed', fontsize=8)
        ax3.tick_params(labelsize=6)

        # 4) Stroke rate over time (windowed)
        ax4 = fig.add_subplot(1, 4, 4)
        if m['stroke']['stroke_count'] > 2:
            from processing.signal_analysis import _find_strokes
            strokes = _find_strokes(y)
            if len(strokes) > 1:
                stroke_times = [(t[s['start_idx']] + t[s['end_idx']]) / 2
                                for s in strokes]
                stroke_durs = [t[s['end_idx']] - t[s['start_idx']] for s in strokes]
                stroke_rates = [60.0 / max(d, 0.01) for d in stroke_durs]  # SPM
                ax4.plot(stroke_times, stroke_rates, color='#9C27B0',
                         linewidth=0.8, alpha=0.8)
                ax4.axhline(m['stroke']['strokes_per_minute'],
                            color='#d32f2f', linewidth=0.8, linestyle='--',
                            label=f"avg {m['stroke']['strokes_per_minute']:.0f}")
                ax4.legend(fontsize=6)
        ax4.set_xlabel('Time (s)', fontsize=7)
        ax4.set_ylabel('SPM', fontsize=7)
        ax4.set_title('Stroke Rate', fontsize=8)
        ax4.tick_params(labelsize=6)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                fig.tight_layout(pad=1.0)
            except Exception:
                pass

        canvas = FigureCanvasTkAgg(fig, self._chart_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ── Apply ────────────────────────────────────────────────────────

    def _set_config_value(self, setting: str, value):
        """Write a value into the config at a dotted path."""
        config = self.main_window.current_config
        parts = setting.split('.')

        # Navigate to the parent
        obj = config
        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]

        obj[parts[-1]] = value

    def _apply_recs(self, recs: list):
        """Apply a list of recommendation dicts to the config."""
        for rec in recs:
            setting = rec['setting']
            value = rec['value']

            # Handle special grouped settings
            if setting.startswith('modulation.'):
                key = setting.split('.', 1)[1]
                axes = self.main_window.current_config.get('positional_axes', {})
                for ax_name in ['e1', 'e2', 'e3', 'e4']:
                    mod = axes.get(ax_name, {}).setdefault('modulation', {})
                    mod[key] = value
            elif setting.startswith('physical_model.'):
                key = setting.split('.', 1)[1]
                pm = self.main_window.current_config.setdefault(
                    'positional_axes', {}).setdefault('physical_model', {})
                pm[key] = value
            elif setting.startswith('speed.savgol_options.'):
                key = setting.split('.')[-1]
                so = self.main_window.current_config.setdefault(
                    'speed', {}).setdefault('savgol_options', {})
                so[key] = value
            else:
                self._set_config_value(setting, value)

        # Refresh the UI
        try:
            self.main_window.parameter_tabs.update_display(
                self.main_window.current_config)
        except Exception as e:
            print(f"Warning: could not refresh UI: {e}")

        # Refresh the recommendations table to show new current values
        self._populate_recommendations()

    def _apply_all(self):
        """Apply all recommendations."""
        if not messagebox.askyesno(
                "Apply All",
                f"Apply all {len(self._recs)} recommendations to the current config?",
                parent=self):
            return
        self._apply_recs(self._recs)
        messagebox.showinfo("Applied",
                            f"{len(self._recs)} settings updated.",
                            parent=self)

    def _apply_selected(self):
        """Apply only the selected recommendations."""
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("No Selection",
                                "Select one or more rows in the table first.",
                                parent=self)
            return
        # Map tree items back to recs by index
        all_items = self._tree.get_children()
        indices = [all_items.index(item) for item in selected if item in all_items]
        to_apply = [self._recs[i] for i in indices if i < len(self._recs)]
        if not to_apply:
            return
        self._apply_recs(to_apply)
        messagebox.showinfo("Applied",
                            f"{len(to_apply)} settings updated.",
                            parent=self)
