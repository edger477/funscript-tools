"""
Global dark/light theme manager.

Usage:
    import ui.theme as theme

    theme.apply(dark)     # set theme (call once after Tk root created to initialise)
    theme.toggle()        # flip dark ↔ light
    theme.is_dark()       # current state
    theme.register(cb)    # callback(dark: bool) called on every change
    theme.unregister(cb)  # remove callback
"""

_dark: bool = False
_listeners: list = []
_native_body_size: int = -12   # TkDefaultFont pixel size captured before sv_ttk loads
_sv_ttk_available: bool | None = None  # None = not yet checked


def _check_sv_ttk() -> bool:
    global _sv_ttk_available
    if _sv_ttk_available is None:
        try:
            import sv_ttk  # noqa: F401
            _sv_ttk_available = True
        except ImportError:
            _sv_ttk_available = False
    return _sv_ttk_available


def _apply_fallback_theme(dark: bool) -> None:
    """Full dark/light fallback when sv_ttk is not installed.

    Both branches stay on 'clam' (it honors style.configure on every
    platform, including macOS where 'aqua' ignores color overrides).
    Both branches must explicitly configure every class — ttk's style
    database is additive, so leaving the light branch empty would keep
    the dark values in place.
    """
    try:
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.theme_use('clam')

        if dark:
            bg        = '#2d2d2d'   # window / frame background
            surface   = '#3c3c3c'   # button / entry / tab background
            surface_h = '#505050'   # hover / active background
            surface_s = '#4a4a4a'   # selected background
            fg        = '#e0e0e0'   # primary text
            fg_strong = '#ffffff'   # selected / active text
            border    = '#555555'
            select_bg = '#4a6fa5'   # text-selection highlight
        else:
            bg        = '#f0f0f0'
            surface   = '#e6e6e6'
            surface_h = '#d0d0d0'
            surface_s = '#c8c8c8'
            fg        = '#000000'
            fg_strong = '#000000'
            border    = '#b0b0b0'
            select_bg = '#3875d7'

        style.configure('.',
                        background=bg, foreground=fg,
                        fieldbackground=surface, bordercolor=border,
                        troughcolor=surface,
                        selectbackground=select_bg,
                        selectforeground='#ffffff',
                        insertcolor=fg)
        for cls in ('TEntry', 'TCombobox', 'TSpinbox'):
            style.configure(cls, fieldbackground='#ffffff' if not dark else surface,
                            foreground='#000000' if not dark else fg)
        style.configure('TNotebook', background=bg)
        style.configure('TNotebook.Tab',
                        background=surface, foreground=fg,
                        padding=[8, 2])
        # Explicit 'active' (hover) state — without this, ttk picks a
        # default hover bg that can fight with our fg and hide the text.
        style.map('TNotebook.Tab',
                  background=[('selected', surface_s),
                              ('active',   surface_h)],
                  foreground=[('selected', fg_strong),
                              ('active',   fg_strong)])
        style.configure('TLabelframe',       background=bg, foreground=fg)
        style.configure('TLabelframe.Label', background=bg, foreground=fg)
        style.configure('TCheckbutton', background=bg, foreground=fg)
        style.configure('TRadiobutton', background=bg, foreground=fg)
        style.configure('TButton',      background=surface, foreground=fg)
        style.configure('TLabel',       background=bg, foreground=fg)
        style.configure('TFrame',       background=bg)
        style.configure('TSeparator',   background=border)
        style.configure('TScrollbar',   background=surface,
                        troughcolor=bg, arrowcolor=fg)
        # Button hover/press — keep the text visible on every state.
        style.map('TButton',
                  background=[('active',  surface_h),
                              ('pressed', surface_s)],
                  foreground=[('active',  fg_strong),
                              ('pressed', fg_strong)])
        style.map('TCheckbutton',
                  background=[('active', bg)],
                  foreground=[('active', fg)])
        style.map('TRadiobutton',
                  background=[('active', bg)],
                  foreground=[('active', fg)])
    except Exception:
        pass


def _capture_native_size():
    """Snapshot TkDefaultFont size before sv_ttk changes it."""
    global _native_body_size
    try:
        import tkinter.font as tkfont
        _native_body_size = tkfont.nametofont('TkDefaultFont').actual()['size']
    except Exception:
        pass


def _restore_sv_font_sizes():
    """Bring sv_ttk's named fonts back down to the native body size."""
    try:
        import tkinter.font as tkfont
        size = _native_body_size
        # Body font used by almost all widgets
        tkfont.nametofont('SunValleyBodyFont').configure(size=size)
        # Caption font used by LabelFrame labels and Treeview headings
        tkfont.nametofont('SunValleyCaptionFont').configure(size=size)
        # Also restore standard Tk named fonts in case sv_ttk touched them
        for name in ('TkDefaultFont', 'TkTextFont', 'TkFixedFont',
                     'TkMenuFont', 'TkHeadingFont', 'TkSmallCaptionFont'):
            try:
                tkfont.nametofont(name).configure(size=size)
            except Exception:
                pass
    except Exception:
        pass  # SunValley fonts don't exist until sv_ttk first loads — safe to ignore


def is_dark() -> bool:
    return _dark


def toggle() -> None:
    apply(not _dark)


def _apply_accent_styles(dark: bool) -> None:
    """Configure named ttk styles used for small accent readouts
    (combine-ratio percentages, ramp %/min, etc.). These were formerly
    hardcoded to 'blue', which is unreadable on dark backgrounds.
    """
    try:
        import tkinter.ttk as ttk
        style = ttk.Style()
        # A readable accent for small stats labels.
        color = '#6fcf97' if dark else '#0b5ed7'   # green in dark, deep blue in light
        style.configure('Accent.TLabel', foreground=color)
    except Exception:
        pass


def _reset_root_style(dark: bool) -> None:
    """Guarantee the ttk root '.' style has non-empty foreground/background.

    An earlier version of the fallback set '.' to empty strings, which
    propagates down to every widget and makes all text invisible. This
    resets '.' to safe, explicit colors every time a theme is applied
    so the broken state self-heals on the next toggle.
    """
    try:
        import tkinter.ttk as ttk
        style = ttk.Style()
        if dark:
            style.configure('.', background='#2d2d2d',
                            foreground='#e0e0e0')
        else:
            style.configure('.', background='#f0f0f0',
                            foreground='#000000')
    except Exception:
        pass


def apply(dark: bool) -> None:
    global _dark
    _dark = dark
    _capture_native_size()
    _reset_root_style(dark)
    if _check_sv_ttk():
        try:
            import sv_ttk
            sv_ttk.set_theme('dark' if dark else 'light')
            _restore_sv_font_sizes()
        except Exception:
            pass
    else:
        _apply_fallback_theme(dark)
    _apply_accent_styles(dark)
    for cb in list(_listeners):
        try:
            cb(dark)
        except Exception:
            pass


def register(cb) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def unregister(cb) -> None:
    try:
        _listeners.remove(cb)
    except ValueError:
        pass
