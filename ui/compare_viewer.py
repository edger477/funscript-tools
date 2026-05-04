"""
Funscript Comparison Viewer.

Loads two funscripts and shows them in stacked timelines (or overlaid)
with synchronized zoom/pan, a draggable playhead, and an optional
difference panel. Designed to run either as a Toplevel popup launched
from the main app or standalone via funscript_compare.py.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np

# Allow standalone import when launched as `python funscript_compare.py`.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from funscript import Funscript


COLOR_A = '#1f77b4'   # blue
COLOR_B = '#d62728'   # red
COLOR_DIFF = '#7b3294'  # purple
COLOR_PLAYHEAD = '#1f8a3a'  # green


class CompareViewer(tk.Toplevel):
    """Side-by-side (stacked or overlaid) comparison of two funscripts."""

    def __init__(self, parent=None, file_a=None, file_b=None):
        super().__init__(parent)
        self.title("Funscript Comparison")
        self.geometry("1100x720")
        self.minsize(800, 500)

        self._fs_a = None
        self._fs_b = None
        self._path_a = None
        self._path_b = None

        # Interactive view state
        self._view_t_start = 0.0
        self._view_t_end = 1.0
        self._playhead_t = None
        self._drag = None  # {'kind': 'pan'|'playhead', ...}
        self._motion_was_drag = False

        # Display options
        self._overlay_var = tk.BooleanVar(value=False)
        self._diff_var = tk.BooleanVar(value=False)

        # Matplotlib state (built lazily)
        self._fig = None
        self._canvas = None
        self._ax_a = None
        self._ax_b = None
        self._ax_diff = None
        self._playhead_lines = []  # one per visible axis

        self._build_ui()

        if file_a:
            self._load(file_a, slot='a')
        if file_b:
            self._load(file_b, slot='b')
        self._fit_view()
        self._redraw()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        # Row layout: 0=file A bar, 1=file B bar, 2=canvas (expands),
        # 3=scrubber, 4=controls, 5=hint.
        self.rowconfigure(2, weight=1)

        # ── Top bar: file A picker ────────────────────────────────
        top_a = ttk.Frame(self, padding=(8, 6, 8, 2))
        top_a.grid(row=0, column=0, sticky='ew')
        top_a.columnconfigure(2, weight=1)
        ttk.Label(top_a, text="A:").grid(row=0, column=0, padx=(0, 4))
        ttk.Button(top_a, text="Browse…",
                   command=lambda: self._browse('a')
                   ).grid(row=0, column=1)
        self._label_a = ttk.Label(top_a, text="(no file loaded)",
                                  foreground='#666666')
        self._label_a.grid(row=0, column=2, sticky='w', padx=8)
        ttk.Button(top_a, text="Swap A↔B",
                   command=self._swap).grid(row=0, column=3, padx=(8, 0))

        # ── Top bar 2: file B picker ──────────────────────────────
        top_b = ttk.Frame(self, padding=(8, 2, 8, 6))
        top_b.grid(row=1, column=0, sticky='ew')
        top_b.columnconfigure(2, weight=1)
        ttk.Label(top_b, text="B:").grid(row=0, column=0, padx=(0, 4))
        ttk.Button(top_b, text="Browse…",
                   command=lambda: self._browse('b')
                   ).grid(row=0, column=1)
        self._label_b = ttk.Label(top_b, text="(no file loaded)",
                                  foreground='#666666')
        self._label_b.grid(row=0, column=2, sticky='w', padx=8)

        # ── Main canvas frame ─────────────────────────────────────
        self._canvas_frame = ttk.Frame(self)
        self._canvas_frame.grid(row=2, column=0, sticky='nsew',
                                padx=8, pady=4)
        self._canvas_frame.columnconfigure(0, weight=1)
        self._canvas_frame.rowconfigure(0, weight=1)

        # ── Timeline scrubber (drag the playhead through the file) ─
        scrub_row = ttk.Frame(self, padding=(8, 4, 8, 0))
        scrub_row.grid(row=3, column=0, sticky='ew')
        scrub_row.columnconfigure(1, weight=1)
        ttk.Label(scrub_row, text="Scrub:").grid(row=0, column=0,
                                                  padx=(0, 6))
        self._scrub_var = tk.DoubleVar(value=0.0)
        self._scrubber = ttk.Scale(
            scrub_row, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
            variable=self._scrub_var, command=self._on_scrub)
        self._scrubber.grid(row=0, column=1, sticky='ew')
        self._scrub_time_label = ttk.Label(scrub_row, text="0.000 s",
                                           foreground='#444', width=12)
        self._scrub_time_label.grid(row=0, column=2, padx=(8, 0))
        self._scrub_updating = False  # prevents feedback loop with set_playhead

        # ── Bottom controls ───────────────────────────────────────
        ctl = ttk.Frame(self, padding=(8, 4, 8, 8))
        ctl.grid(row=4, column=0, sticky='ew')
        ctl.columnconfigure(7, weight=1)

        ttk.Checkbutton(ctl, text="Overlay (one plot)",
                        variable=self._overlay_var,
                        command=self._redraw
                        ).grid(row=0, column=0, padx=(0, 12))
        ttk.Checkbutton(ctl, text="Difference (B − A) panel",
                        variable=self._diff_var,
                        command=self._redraw
                        ).grid(row=0, column=1, padx=(0, 12))

        ttk.Button(ctl, text="Fit", command=self._fit_view_and_redraw
                   ).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(ctl, text="Clear playhead",
                   command=self._clear_playhead
                   ).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(ctl, text="View:").grid(row=0, column=4, padx=(0, 4))
        self._view_label = ttk.Label(ctl, text="0.000 → 0.000 s",
                                     foreground='#444')
        self._view_label.grid(row=0, column=5, padx=(0, 12))

        ttk.Label(ctl, text="Playhead:").grid(
            row=0, column=6, padx=(0, 4))
        self._playhead_label = ttk.Label(ctl, text="—",
                                         foreground='#1f8a3a')
        self._playhead_label.grid(row=0, column=7, sticky='w')

        # Follow-scrub toggle: when on, dragging the scrubber auto-scrolls
        # the visible view to keep the playhead inside the window. Useful
        # when zoomed in and you want to scrub through quickly.
        self._scrub_follow_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctl, text="Follow scrub",
                        variable=self._scrub_follow_var
                        ).grid(row=0, column=8, padx=(12, 0))

        # Hint
        hint = ttk.Label(self,
                         text=("Mouse: scroll-wheel = zoom (anchored on "
                               "cursor) · drag = pan · click = set "
                               "playhead · right-click = clear playhead"
                               "   ·   Scrub: drag slider to move "
                               "playhead (auto-scrolls view if Follow on)"),
                         foreground='#888888')
        hint.grid(row=5, column=0, sticky='w', padx=8, pady=(0, 6))

    # -------------------------------------------------------- File loading

    def _browse(self, slot):
        path = filedialog.askopenfilename(
            title=f"Select funscript for slot {slot.upper()}",
            filetypes=[("Funscript files", "*.funscript"),
                       ("All files", "*.*")],
            parent=self,
        )
        if not path:
            return
        self._load(path, slot=slot)
        # Re-fit only if the *other* slot is empty (so loading both at once
        # via two browses doesn't keep snapping the view).
        other = self._fs_b if slot == 'a' else self._fs_a
        if other is None:
            self._fit_view()
        self._redraw()

    def _load(self, path, slot):
        try:
            fs = Funscript.from_file(path)
        except Exception as e:
            messagebox.showerror("Load error",
                                 f"Could not load:\n{path}\n\n{e}",
                                 parent=self)
            return
        if slot == 'a':
            self._fs_a = fs
            self._path_a = path
            self._label_a.config(
                text=self._slot_summary(path, fs),
                foreground='#222222')
        else:
            self._fs_b = fs
            self._path_b = path
            self._label_b.config(
                text=self._slot_summary(path, fs),
                foreground='#222222')
        # Newly loaded data may change the time span — re-range the scrubber
        # so dragging covers the whole loaded duration.
        self._refresh_scrub_range()

    def _slot_summary(self, path, fs):
        n = len(fs.y)
        dur = float(fs.x[-1]) if n > 0 else 0.0
        return f"{os.path.basename(path)}  —  {n} samples  |  {dur:.2f} s"

    def _swap(self):
        self._fs_a, self._fs_b = self._fs_b, self._fs_a
        self._path_a, self._path_b = self._path_b, self._path_a
        for slot, lab, path, fs in [
                ('a', self._label_a, self._path_a, self._fs_a),
                ('b', self._label_b, self._path_b, self._fs_b)]:
            if fs is None:
                lab.config(text="(no file loaded)", foreground='#666666')
            else:
                lab.config(text=self._slot_summary(path, fs),
                           foreground='#222222')
        self._refresh_scrub_range()
        self._redraw()

    # ---------------------------------------------------------- View math

    def _data_t_range(self):
        """Return (t_start, t_end) covering whichever files are loaded."""
        starts = []
        ends = []
        for fs in (self._fs_a, self._fs_b):
            if fs is None or len(fs.x) == 0:
                continue
            starts.append(float(fs.x[0]))
            ends.append(float(fs.x[-1]))
        if not starts:
            return 0.0, 1.0
        return min(starts), max(ends)

    def _fit_view(self):
        self._view_t_start, self._view_t_end = self._data_t_range()
        if self._view_t_end <= self._view_t_start:
            self._view_t_end = self._view_t_start + 1.0

    def _fit_view_and_redraw(self):
        self._fit_view()
        self._redraw()

    def _clamp_view(self):
        full_start, full_end = self._data_t_range()
        if self._view_t_end <= self._view_t_start:
            self._view_t_end = self._view_t_start + 1.0
        # Don't let the visible window exceed the data range — let it shrink
        # all the way down for zoom-in but never expand beyond data on edges.
        vis = self._view_t_end - self._view_t_start
        full_dur = full_end - full_start
        if vis > full_dur:
            self._view_t_start = full_start
            self._view_t_end = full_end
            return
        if self._view_t_start < full_start:
            shift = full_start - self._view_t_start
            self._view_t_start += shift
            self._view_t_end += shift
        if self._view_t_end > full_end:
            shift = self._view_t_end - full_end
            self._view_t_start -= shift
            self._view_t_end -= shift

    # ---------------------------------------------------------- Rendering

    def _redraw(self):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            for w in self._canvas_frame.winfo_children():
                w.destroy()
            ttk.Label(self._canvas_frame,
                      text=("matplotlib is required for the comparison "
                            "viewer (pip install matplotlib)."),
                      foreground='red').grid(row=0, column=0,
                                              padx=20, pady=20)
            return

        for w in self._canvas_frame.winfo_children():
            w.destroy()

        self._clamp_view()

        overlay = bool(self._overlay_var.get())
        diff = bool(self._diff_var.get())

        n_panels = 1 if overlay else 2
        if diff:
            n_panels += 1
        # Slightly shorter diff panel.
        height_ratios = [1.0] * (n_panels - 1) + ([0.6] if diff else [1.0])
        if not diff:
            height_ratios = [1.0] * n_panels

        fig = Figure(figsize=(10, 6.5), dpi=85)
        gs = fig.add_gridspec(n_panels, 1, height_ratios=height_ratios,
                              hspace=0.18)

        first_ax = None
        self._playhead_lines = []
        self._ax_a = self._ax_b = self._ax_diff = None

        if overlay:
            ax = fig.add_subplot(gs[0])
            self._draw_signal(ax, self._fs_a, color=COLOR_A,
                              label=self._label_for('a'))
            self._draw_signal(ax, self._fs_b, color=COLOR_B,
                              label=self._label_for('b'))
            self._format_signal_axis(ax, "A and B (overlaid)")
            ax.legend(loc='upper right', fontsize=8, framealpha=0.85)
            first_ax = ax
            self._ax_a = ax
            self._ax_b = ax
            row = 1
        else:
            ax_a = fig.add_subplot(gs[0])
            self._draw_signal(ax_a, self._fs_a, color=COLOR_A,
                              label='A')
            self._format_signal_axis(ax_a,
                                     f"A — {self._label_for('a')}")
            first_ax = ax_a
            self._ax_a = ax_a

            ax_b = fig.add_subplot(gs[1], sharex=ax_a)
            self._draw_signal(ax_b, self._fs_b, color=COLOR_B,
                              label='B')
            self._format_signal_axis(ax_b,
                                     f"B — {self._label_for('b')}")
            self._ax_b = ax_b
            row = 2

        if diff:
            ax_d = fig.add_subplot(gs[row], sharex=first_ax)
            self._draw_diff(ax_d)
            self._ax_diff = ax_d

        # Apply view limits
        first_ax.set_xlim(self._view_t_start, self._view_t_end)

        # Playhead lines (vertical) on every visible axis
        if self._playhead_t is not None:
            for ax in (self._ax_a, self._ax_b, self._ax_diff):
                if ax is None or (overlay and ax is self._ax_b):
                    continue
                line = ax.axvline(self._playhead_t,
                                  color=COLOR_PLAYHEAD, linewidth=1.4,
                                  alpha=0.9, zorder=10)
                self._playhead_lines.append(line)

        fig.tight_layout(pad=0.6)

        canvas = FigureCanvasTkAgg(fig, self._canvas_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.grid(row=0, column=0, sticky='nsew')
        self._fig = fig
        self._canvas = canvas

        # Hook events. We bind once per redraw because the canvas is
        # rebuilt; matplotlib stores callbacks on the Figure not the
        # widget so old ones GC away with the old figure.
        canvas.mpl_connect('button_press_event', self._on_press)
        canvas.mpl_connect('button_release_event', self._on_release)
        canvas.mpl_connect('motion_notify_event', self._on_motion)
        canvas.mpl_connect('scroll_event', self._on_scroll)

        self._update_view_label()

    def _label_for(self, slot):
        path = self._path_a if slot == 'a' else self._path_b
        if not path:
            return "(no file loaded)"
        return os.path.basename(path)

    def _draw_signal(self, ax, fs, color, label):
        if fs is None or len(fs.x) == 0:
            ax.text(0.5, 0.5, "no file loaded",
                    ha='center', va='center', fontsize=10,
                    color='#888888', transform=ax.transAxes)
            return
        x = np.asarray(fs.x, dtype=float)
        y = np.asarray(fs.y, dtype=float) * 100.0
        ax.plot(x, y, color=color, linewidth=1.0, label=label)
        ax.fill_between(x, 0, y, color=color, alpha=0.10)

    def _format_signal_axis(self, ax, title):
        ax.set_title(title, fontsize=9, loc='left')
        ax.set_ylabel('Position', fontsize=8)
        ax.set_ylim(-2, 102)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.25)

    def _draw_diff(self, ax):
        if self._fs_a is None or self._fs_b is None:
            ax.text(0.5, 0.5, "Load both files to see the difference",
                    ha='center', va='center', fontsize=10,
                    color='#888888', transform=ax.transAxes)
            ax.tick_params(labelsize=7)
            ax.set_xlabel('Time (s)', fontsize=8)
            return
        # Resample both onto a common dense grid covering only the
        # time range where both signals exist.
        t0 = max(float(self._fs_a.x[0]), float(self._fs_b.x[0]))
        t1 = min(float(self._fs_a.x[-1]), float(self._fs_b.x[-1]))
        if t1 <= t0:
            ax.text(0.5, 0.5,
                    "Files don't overlap in time — no difference to plot",
                    ha='center', va='center', fontsize=10,
                    color='#888888', transform=ax.transAxes)
            ax.tick_params(labelsize=7)
            ax.set_xlabel('Time (s)', fontsize=8)
            return
        # ~200 samples per second on the overlap, cap at 20k pts so we
        # don't blow up on long files.
        n = min(20000, max(200, int(200 * (t1 - t0))))
        t = np.linspace(t0, t1, n)
        ya = np.interp(t, self._fs_a.x, self._fs_a.y) * 100.0
        yb = np.interp(t, self._fs_b.x, self._fs_b.y) * 100.0
        diff = yb - ya
        ax.axhline(0, color='#888888', linewidth=0.6, alpha=0.7)
        ax.plot(t, diff, color=COLOR_DIFF, linewidth=1.0, label='B − A')
        ax.set_ylabel('Δ Position', fontsize=8)
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_ylim(-105, 105)
        # Show RMS as a subtitle
        rms = float(np.sqrt(np.mean(diff * diff)))
        peak = float(np.max(np.abs(diff)))
        ax.set_title(f"Difference — RMS {rms:.2f} | peak {peak:.2f}",
                     fontsize=9, loc='left')
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.25)

    def _update_view_label(self):
        self._view_label.config(
            text=f"{self._view_t_start:.3f} → {self._view_t_end:.3f} s")

    def _set_playhead(self, t):
        if t is None:
            self._playhead_t = None
            self._playhead_label.config(text="—")
            self._redraw()
            # Don't move the slider when clearing — the scrubber position
            # is informational and doesn't need to follow the clear.
            return
        full_start, full_end = self._data_t_range()
        t = max(full_start, min(full_end, float(t)))
        self._playhead_t = t
        # Look up nearest sample value on both signals
        msg = f"{t:.3f} s"
        for slot, fs in (('A', self._fs_a), ('B', self._fs_b)):
            if fs is None or len(fs.x) == 0:
                continue
            i = int(np.argmin(np.abs(np.asarray(fs.x, dtype=float) - t)))
            v = float(fs.y[i]) * 100.0
            msg += f"   {slot}={v:.1f}"
        self._playhead_label.config(text=msg)
        self._sync_scrub_to_playhead()
        self._redraw()

    def _clear_playhead(self):
        self._set_playhead(None)

    # ---------------------------------------------------- Scrubber (slider)

    def _refresh_scrub_range(self):
        """Reconfigure the scrubber's range from the loaded data span."""
        full_start, full_end = self._data_t_range()
        # Avoid zero-length range.
        if full_end <= full_start:
            full_end = full_start + 1.0
        self._scrub_updating = True
        try:
            self._scrubber.configure(from_=full_start, to=full_end)
            cur = float(self._scrub_var.get())
            cur = max(full_start, min(full_end, cur))
            self._scrub_var.set(cur)
            self._scrub_time_label.config(text=f"{cur:.3f} s")
        finally:
            self._scrub_updating = False

    def _on_scrub(self, value=None):
        """User dragged the slider — move the playhead and (optionally)
        scroll the view to keep it visible."""
        if self._scrub_updating:
            return
        try:
            t = float(self._scrub_var.get())
        except (tk.TclError, ValueError):
            return
        # Update playhead WITHOUT triggering a slider rewrite.
        self._scrub_updating = True
        try:
            self._set_playhead_no_scrub_sync(t)
        finally:
            self._scrub_updating = False
        self._scrub_time_label.config(text=f"{t:.3f} s")

        # If the playhead has scrolled outside the visible window and
        # follow-mode is on, recenter the view on it.
        if self._scrub_follow_var.get():
            vis = self._view_t_end - self._view_t_start
            if t < self._view_t_start or t > self._view_t_end:
                self._view_t_start = t - vis / 2
                self._view_t_end = t + vis / 2
                self._clamp_view()
                self._refresh_xlim()
                self._update_view_label()

    def _set_playhead_no_scrub_sync(self, t):
        """Set the playhead from the scrubber, without writing back to the
        scrubber (which would create a feedback loop)."""
        if t is None:
            self._playhead_t = None
            self._playhead_label.config(text="—")
            self._redraw()
            return
        full_start, full_end = self._data_t_range()
        t = max(full_start, min(full_end, float(t)))
        self._playhead_t = t
        msg = f"{t:.3f} s"
        for slot, fs in (('A', self._fs_a), ('B', self._fs_b)):
            if fs is None or len(fs.x) == 0:
                continue
            i = int(np.argmin(np.abs(np.asarray(fs.x, dtype=float) - t)))
            v = float(fs.y[i]) * 100.0
            msg += f"   {slot}={v:.1f}"
        self._playhead_label.config(text=msg)
        self._redraw()

    def _sync_scrub_to_playhead(self):
        """Push the current playhead time into the slider position."""
        if self._playhead_t is None:
            return
        self._scrub_updating = True
        try:
            self._scrub_var.set(float(self._playhead_t))
            self._scrub_time_label.config(
                text=f"{float(self._playhead_t):.3f} s")
        finally:
            self._scrub_updating = False

    # -------------------------------------------------- Mouse interactions

    def _is_signal_axes(self, ax):
        return ax in (self._ax_a, self._ax_b, self._ax_diff)

    def _on_press(self, event):
        if not self._is_signal_axes(event.inaxes) or event.xdata is None:
            return
        if event.button == 1:
            self._drag = {
                'kind': 'pan',
                'start_x': float(event.xdata),
                'start_view': (self._view_t_start, self._view_t_end),
                'moved': False,
            }
        elif event.button == 3:
            self._clear_playhead()

    def _on_motion(self, event):
        if not self._drag or event.xdata is None:
            return
        if self._drag['kind'] != 'pan':
            return
        dx = float(event.xdata) - self._drag['start_x']
        # Drag-right should reveal earlier content (i.e. pan view left).
        # Movement threshold prevents accidental drags on click-release.
        if abs(dx) > 1e-9:
            self._drag['moved'] = True
        s, e = self._drag['start_view']
        self._view_t_start = s - dx
        self._view_t_end = e - dx
        self._clamp_view()
        # Light redraw: just adjust xlim instead of full redraw for smoothness
        self._refresh_xlim()
        self._update_view_label()

    def _on_release(self, event):
        drag = self._drag
        self._drag = None
        if drag is None:
            return
        if (drag['kind'] == 'pan' and not drag['moved']
                and event.button == 1 and event.xdata is not None):
            self._set_playhead(event.xdata)

    def _on_scroll(self, event):
        if not self._is_signal_axes(event.inaxes) or event.xdata is None:
            return
        # Zoom anchored on cursor. Wheel up = zoom in, wheel down = out.
        cursor_t = float(event.xdata)
        cur_vis = self._view_t_end - self._view_t_start
        if cur_vis <= 0:
            return
        factor = 1 / 1.25 if event.button == 'up' else 1.25
        new_vis = max(1e-3, cur_vis * factor)
        full_start, full_end = self._data_t_range()
        new_vis = min(new_vis, full_end - full_start)
        cursor_frac = (cursor_t - self._view_t_start) / cur_vis
        new_start = cursor_t - cursor_frac * new_vis
        self._view_t_start = new_start
        self._view_t_end = new_start + new_vis
        self._clamp_view()
        self._refresh_xlim()
        self._update_view_label()

    def _refresh_xlim(self):
        """Lightweight: update existing xlim without full redraw."""
        if self._canvas is None:
            return
        for ax in (self._ax_a, self._ax_b, self._ax_diff):
            if ax is None:
                continue
            ax.set_xlim(self._view_t_start, self._view_t_end)
        self._canvas.draw_idle()


def main():
    """Standalone entry point."""
    root = tk.Tk()
    root.withdraw()
    file_a = sys.argv[1] if len(sys.argv) > 1 else None
    file_b = sys.argv[2] if len(sys.argv) > 2 else None
    viewer = CompareViewer(root, file_a=file_a, file_b=file_b)
    viewer.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
