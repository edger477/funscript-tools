"""
Shared tooltip helper.

Usage:
    from ui.tooltip_helper import create_tooltip
    create_tooltip(my_entry, "Explains what this setting does.")

The tooltip is lazily created on <Enter> and destroyed on <Leave>, so
idle cost is zero. Positioning is clamped against screen bounds so the
popup never lands off-screen.
"""

import tkinter as tk


def create_tooltip(widget, text: str, wraplength: int = 420) -> None:
    """Attach a hover tooltip to `widget`.

    Args:
        widget: Any Tk widget; the tooltip shows while the pointer is
            over it and hides on leave.
        text: The tooltip body.
        wraplength: Pixel width at which the text wraps. 420 px fits
            most multi-sentence explanations on screen.
    """
    state = {'tooltip': None, 'screen_w': None, 'screen_h': None}

    def show(_event):
        if state['tooltip']:
            return
        try:
            if not widget.winfo_ismapped():
                return
        except tk.TclError:
            return
        if state['screen_w'] is None:
            try:
                state['screen_w'] = widget.winfo_screenwidth()
                state['screen_h'] = widget.winfo_screenheight()
            except tk.TclError:
                state['screen_w'], state['screen_h'] = 1920, 1080
        try:
            x = widget.winfo_rootx() + widget.winfo_width() + 12
            y = widget.winfo_rooty()
        except tk.TclError:
            return
        approx_w = min(wraplength + 24, 460)
        if x + approx_w > state['screen_w']:
            x = max(4, widget.winfo_rootx() - approx_w - 4)
        if y + 60 > state['screen_h']:
            y = max(4, state['screen_h'] - 80)
        tip = tk.Toplevel(widget)
        try:
            tip.wm_overrideredirect(True)
        except tk.TclError:
            pass
        try:
            tip.wm_attributes('-topmost', True)
        except tk.TclError:
            pass
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tip, text=text, background="lightyellow",
                         foreground="#000000",
                         relief=tk.SOLID, borderwidth=1,
                         font=('TkDefaultFont', 9),
                         wraplength=wraplength, justify=tk.LEFT,
                         padx=6, pady=4)
        label.pack()
        tip.update_idletasks()
        tip.lift()
        state['tooltip'] = tip

    def hide(_event):
        tip = state['tooltip']
        if tip is not None:
            try:
                tip.destroy()
            except tk.TclError:
                pass
            state['tooltip'] = None

    widget.bind('<Enter>', show, add='+')
    widget.bind('<Leave>', hide, add='+')
