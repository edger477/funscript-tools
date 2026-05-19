"""
Funscript Generator Dialog

Generates funscripts from parametric waveform functions with interpolated parameters.
"""

import json
import math
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sys

sys.path.append(str(Path(__file__).parent.parent))
from funscript.funscript import Funscript
import ui.theme as _theme


FUNCTIONS = ['line', 'sin', 'triangle', 'sawtooth', 'sin-half', 'square']


def _waveform(func_type: str, phase: float) -> float:
    """Return waveform value in [-1, 1] (or [0, 1] for sin-half) for normalised phase in [0,1)."""
    p = phase % 1.0
    if func_type == 'sin':
        return math.sin(p * 2 * math.pi)
    elif func_type == 'triangle':
        if p < 0.25:
            return 4 * p
        elif p < 0.75:
            return 2 - 4 * p
        else:
            return 4 * p - 4
    elif func_type == 'sawtooth':
        return 2 * p - 1          # rises -1 → +1 then snaps
    elif func_type == 'sin-half':
        return math.sin(p * math.pi)   # 0 → +1 → 0 (always non-negative)
    elif func_type == 'square':
        return 1.0 if p < 0.5 else -1.0
    return 0.0


def generate_actions(length_sec: float, func_type: str,
                     amp_fn, center_fn, freq_fn,
                     overflow: str) -> list:
    """
    Generate funscript actions list.

    amp_fn(t), center_fn(t): parameter value at time t (seconds), range 0-100.
    freq_fn(t): frequency in Hz at time t — phase advances by freq*dt each step.
    overflow: 'crop' | 'shift'
    Returns list of {"at": ms, "pos": 0-100}.
    """
    if length_sec <= 0:
        return []

    if func_type == 'line':
        def _line_pos(t):
            c = center_fn(t)
            a = amp_fn(t)
            if overflow == 'shift':
                c = max(a, min(100 - a, c))
            return max(0, min(100, round(c)))
        return [{"at": 0, "pos": _line_pos(0)},
                {"at": round(length_sec * 1000), "pos": _line_pos(length_sec)}]

    dt = 0.002 if func_type == 'square' else 0.020

    actions = []
    phase = 0.0
    t = 0.0
    prev_pos = None

    while True:
        t_clamp = min(t, length_sec)
        amp = amp_fn(t_clamp)
        center = center_fn(t_clamp)
        freq = freq_fn(t_clamp)

        eff_center = max(amp, min(100 - amp, center)) if overflow == 'shift' else center

        wave = _waveform(func_type, phase) if amp > 0 and freq > 0 else 0.0

        pos_raw = eff_center + amp * wave
        pos = max(0, min(100, round(pos_raw)))
        at_ms = round(t_clamp * 1000)

        if pos != prev_pos or at_ms == 0 or t_clamp >= length_sec:
            # For square wave: insert a 1ms hold-point before a large jump so devices
            # don't linearly ramp instead of snapping.
            if func_type == 'square' and prev_pos is not None and abs(pos - prev_pos) > 20 and at_ms > 1:
                actions.append({"at": at_ms - 1, "pos": prev_pos})
            actions.append({"at": at_ms, "pos": pos})
            prev_pos = pos

        if t_clamp >= length_sec:
            break

        phase += freq * dt
        t += dt

    return actions


def _make_linear_fn(v_from: float, v_to: float, length_sec: float):
    if length_sec <= 0:
        return lambda t: v_from
    return lambda t: v_from + (v_to - v_from) * t / length_sec


def _make_fs_fn(fs_x: np.ndarray, fs_y: np.ndarray, scale: float = 100.0):
    """fs_y is 0-1 (Funscript internal), scale maps to parameter range."""
    def fn(t):
        return float(np.interp(t, fs_x, fs_y)) * scale
    return fn


class _ParamRow:
    """A single parameter row: label | From | To | Load Funscript | Clear | status [× mult]."""

    def __init__(self, parent, label, default_from, default_to,
                 param_scale: float, on_change=None, row: int = 0,
                 show_multiplier: bool = False):
        self._scale = param_scale      # multiplier to convert funscript 0-1 → param units
        self._on_change = on_change
        self._fs_data = None           # (x_array, y_array) loaded from file
        self._mult_var = tk.StringVar(value='1') if show_multiplier else None

        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=(5, 2), pady=3)

        self.from_var = tk.StringVar(value=str(default_from))
        self.to_var = tk.StringVar(value=str(default_to))

        if on_change:
            self.from_var.trace_add('write', lambda *_: on_change())
            self.to_var.trace_add('write', lambda *_: on_change())

        ttk.Label(parent, text="From:").grid(row=row, column=1, sticky=tk.E, padx=2)
        self._from_entry = ttk.Entry(parent, textvariable=self.from_var, width=6)
        self._from_entry.grid(row=row, column=2, padx=2)
        ttk.Label(parent, text="To:").grid(row=row, column=3, sticky=tk.E, padx=2)
        self._to_entry = ttk.Entry(parent, textvariable=self.to_var, width=6)
        self._to_entry.grid(row=row, column=4, padx=2)

        ttk.Button(parent, text="Load Funscript", width=14,
                   command=self._load_fs).grid(row=row, column=5, padx=(8, 2))

        self._clear_btn = ttk.Button(parent, text="Clear", width=6,
                                     command=self._clear_fs, state='disabled')
        self._clear_btn.grid(row=row, column=6, padx=2)

        self._status_lbl = ttk.Label(parent, text="(manual)", foreground='gray', width=22)
        self._status_lbl.grid(row=row, column=7, padx=2, sticky=tk.W)

        if show_multiplier:
            ttk.Label(parent, text="×").grid(row=row, column=8, padx=(6, 1))
            ttk.Entry(parent, textvariable=self._mult_var, width=5).grid(row=row, column=9, padx=2)

    def _load_fs(self):
        path = filedialog.askopenfilename(
            title="Select Funscript for Parameter",
            filetypes=[("Funscript files", "*.funscript"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            fs = Funscript.from_file(Path(path))
            self._fs_data = (fs.x, fs.y)
            self._status_lbl.config(text=Path(path).name, foreground='green')
            self._clear_btn.config(state='normal')
            self._from_entry.config(state='disabled')
            self._to_entry.config(state='disabled')
            if self._on_change:
                self._on_change()
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not load funscript:\n{exc}")

    def _clear_fs(self):
        self._fs_data = None
        self._status_lbl.config(text="(manual)", foreground='gray')
        self._clear_btn.config(state='disabled')
        self._from_entry.config(state='normal')
        self._to_entry.config(state='normal')
        if self._on_change:
            self._on_change()

    def get_from(self) -> float:
        try:
            return float(self.from_var.get())
        except ValueError:
            return 0.0

    def get_to(self) -> float:
        try:
            return float(self.to_var.get())
        except ValueError:
            return self.get_from()

    def _get_multiplier(self) -> float:
        if self._mult_var is None:
            return 1.0
        try:
            return float(self._mult_var.get())
        except ValueError:
            return 1.0

    def make_fn(self, length_sec: float):
        """Return a callable t → value."""
        if self._fs_data is not None:
            xs, ys = self._fs_data
            return _make_fs_fn(xs, ys, self._scale * self._get_multiplier())
        return _make_linear_fn(self.get_from(), self.get_to(), length_sec)


class FunscriptGeneratorDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Funscript Generator")
        self.resizable(True, True)
        self.minsize(740, 500)

        self._output_dir = tk.StringVar()
        self._filename_var = tk.StringVar()
        self._func_var = tk.StringVar(value='sin')
        self._overflow_var = tk.StringVar(value='crop')
        self._length_min_var = tk.StringVar(value='1')
        self._length_sec_var = tk.StringVar(value='0')

        self._build_ui()
        _theme.register(self._on_theme)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_filename()

    def _on_close(self):
        _theme.unregister(self._on_theme)
        self.destroy()

    def _on_theme(self, dark: bool):
        pass  # ttk handles theming

    def _build_ui(self):
        root_frame = ttk.Frame(self, padding=10)
        root_frame.pack(fill=tk.BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)

        row = 0

        # ── Length ──────────────────────────────────────────────────────────
        len_frame = ttk.LabelFrame(root_frame, text="Length", padding=5)
        len_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

        ttk.Label(len_frame, text="Minutes:").pack(side=tk.LEFT, padx=(5, 2))
        ttk.Entry(len_frame, textvariable=self._length_min_var, width=4).pack(side=tk.LEFT)
        ttk.Label(len_frame, text="Seconds:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(len_frame, textvariable=self._length_sec_var, width=4).pack(side=tk.LEFT)

        self._length_min_var.trace_add('write', lambda *_: self._update_filename())
        self._length_sec_var.trace_add('write', lambda *_: self._update_filename())
        row += 1

        # ── Function ─────────────────────────────────────────────────────────
        func_frame = ttk.LabelFrame(root_frame, text="Function", padding=5)
        func_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

        for f in FUNCTIONS:
            ttk.Radiobutton(func_frame, text=f, value=f, variable=self._func_var,
                            command=self._update_filename).pack(side=tk.LEFT, padx=6)
        row += 1

        # ── Parameters ───────────────────────────────────────────────────────
        params_frame = ttk.LabelFrame(root_frame, text="Parameters", padding=5)
        params_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

        for col, lbl in enumerate(['', 'From', '', 'To', '', 'Funscript Source', '', '']):
            ttk.Label(params_frame, text=lbl, foreground='gray').grid(row=0, column=col, padx=2)

        self._amp_row = _ParamRow(params_frame, "Amplitude (0–100):",
                                  50, 50, param_scale=100.0,
                                  on_change=self._update_filename, row=1)
        self._center_row = _ParamRow(params_frame, "Center (0–100):",
                                     50, 50, param_scale=100.0,
                                     on_change=self._update_filename, row=2)
        self._freq_row = _ParamRow(params_frame, "Frequency (0.01–50 Hz):",
                                   0.5, 0.5, param_scale=50.0,
                                   on_change=self._update_filename, row=3,
                                   show_multiplier=True)

        overflow_frame = ttk.Frame(params_frame)
        overflow_frame.grid(row=4, column=0, columnspan=8, sticky=tk.W, padx=5, pady=(2, 4))
        ttk.Label(overflow_frame, text="Center overflow:").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Radiobutton(overflow_frame, text="Crop (clamp to 0/100)",
                        value='crop', variable=self._overflow_var).pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(overflow_frame, text="Shift (move center to fit amplitude)",
                        value='shift', variable=self._overflow_var).pack(side=tk.LEFT, padx=4)
        row += 1

        # ── Output ───────────────────────────────────────────────────────────
        out_frame = ttk.LabelFrame(root_frame, text="Output", padding=5)
        out_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(out_frame, textvariable=self._output_dir).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(out_frame, text="Browse…", command=self._browse_dir).grid(
            row=0, column=2, padx=5)

        ttk.Label(out_frame, text="Filename:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(out_frame, textvariable=self._filename_var).grid(
            row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        row += 1

        # ── Status / Generate ─────────────────────────────────────────────────
        bottom = ttk.Frame(root_frame)
        bottom.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(4, 0))
        bottom.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Ready.")
        ttk.Label(bottom, textvariable=self._status_var).grid(
            row=0, column=0, sticky=tk.W, padx=5)

        self._gen_btn = ttk.Button(bottom, text="Generate", command=self._start_generate)
        self._gen_btn.grid(row=0, column=1, padx=5, sticky=tk.E)

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self._output_dir.set(d)

    def _get_length_sec(self) -> float:
        try:
            mins = int(self._length_min_var.get())
        except ValueError:
            mins = 0
        try:
            secs = float(self._length_sec_var.get())
        except ValueError:
            secs = 0
        return max(0, mins * 60 + secs)

    def _update_filename(self):
        length_sec = self._get_length_sec()
        total_min = int(length_sec // 60)
        func = self._func_var.get()

        a_from = self._amp_row.get_from()
        a_to = self._amp_row.get_to()
        c_from = self._center_row.get_from()
        c_to = self._center_row.get_to()
        f_from = self._freq_row.get_from()
        f_to = self._freq_row.get_to()

        def _fmt(v):
            return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip('0').rstrip('.')

        name = (f"{total_min}min-{func}"
                f"_amp{_fmt(a_from)}-{_fmt(a_to)}"
                f"_center{_fmt(c_from)}-{_fmt(c_to)}"
                f"_freq{_fmt(f_from)}-{_fmt(f_to)}"
                f".funscript")
        self._filename_var.set(name)

    def _start_generate(self):
        self._gen_btn.config(state='disabled')
        self._status_var.set("Generating…")
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self):
        try:
            length_sec = self._get_length_sec()
            if length_sec <= 0:
                raise ValueError("Length must be greater than zero.")

            out_dir = self._output_dir.get().strip()
            if not out_dir:
                raise ValueError("Please select an output folder.")
            out_path = Path(out_dir)
            if not out_path.exists():
                raise ValueError(f"Output folder does not exist:\n{out_dir}")

            filename = self._filename_var.get().strip()
            if not filename:
                raise ValueError("Filename cannot be empty.")
            if not filename.endswith('.funscript'):
                filename += '.funscript'

            func_type = self._func_var.get()
            overflow = self._overflow_var.get()

            amp_fn = self._amp_row.make_fn(length_sec)
            center_fn = self._center_row.make_fn(length_sec)
            freq_fn = self._freq_row.make_fn(length_sec)

            actions = generate_actions(length_sec, func_type,
                                       amp_fn, center_fn, freq_fn, overflow)

            dest = out_path / filename
            with open(dest, 'w', encoding='utf-8') as f:
                json.dump({"actions": actions}, f, indent=2)

            msg = f"Saved {len(actions)} points → {dest.name}"
            self.after(0, lambda: self._status_var.set(msg))
            self.after(0, lambda: messagebox.showinfo("Done", f"Generated successfully!\n\n{dest}",
                                                       parent=self))
        except Exception as exc:
            err = str(exc)
            self.after(0, lambda: self._status_var.set(f"Error: {err}"))
            self.after(0, lambda: messagebox.showerror("Generation Error", err, parent=self))
        finally:
            self.after(0, lambda: self._gen_btn.config(state='normal'))
