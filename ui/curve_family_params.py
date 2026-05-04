"""
Shared curve-family parameter UI builder.

Used by the Trochoid Quantization and Trochoid Spatial tabs. Both tabs
let the user edit per-family parameters (R/r/d for hypo/epi, a/k for
rose, etc.) in a small grid, with short one-line hints inline and
longer explanations on hover. Previously this was duplicated as
`_trochoid_build_param_ui` and `_ts_build_param_ui` — this module
consolidates the help dict and the build routine.
"""

import tkinter as tk
from tkinter import ttk

from ui.tooltip_helper import create_tooltip


# (short_hint, long_tooltip) per param name. Used across all curve
# families. Lissajous's 'a' gets overridden at build time below because
# it means "X frequency" rather than "amplitude" for that family.
FAMILY_PARAM_HELP = {
    'R': ('Outer (fixed) circle radius',
          'Outer (fixed) circle radius. The bounding container inside '
          'which (hypo) or outside which (epi) the rolling circle '
          'travels. Larger R = larger overall pattern. The R/r ratio '
          'sets the symmetry: integer ratios produce a closed curve '
          '(e.g. R=5, r=3 closes after 3 turns); irrational ratios '
          'trace forever without closing.'),
    'r': ('Rolling circle radius (>0; smaller r = more lobes)',
          'Rolling circle radius (must be > 0). Smaller r relative to '
          'R = more lobes/petals. For integer R/r ratios, the curve '
          'has roughly R/gcd(R,r) lobes. Try r near R/3 to R/5 for '
          'classic Spirograph-style patterns; r close to R gives soft '
          'single-loop shapes.'),
    'd': ('Pen offset; d=r=cusps, d<r=curtate, d>r=prolate',
          'Pen offset — distance from rolling-circle center to the '
          'tracing point. Three regimes: (1) d = r → cusps (true '
          'hypo/epicycloid, sharp points); (2) d < r → curtate '
          'trochoid (rounded loops, no cusps); (3) d > r → prolate '
          'trochoid (self-intersecting loops/knots).'),
    'a': ('Amplitude / petal length',
          'Amplitude / petal length. Sets the maximum radius of each '
          'petal.'),
    'k': ('Petal frequency (odd k=k petals, even k=2k petals)',
          'Petal frequency. If k is odd the rose has k petals; if k '
          'is even it has 2k petals. Non-integer k traces a '
          'non-closing pattern.'),
    'A': ('X amplitude', 'X amplitude — half-width of the figure.'),
    'B': ('Y amplitude', 'Y amplitude — half-height of the figure.'),
    'b': ('Y frequency',
          'Y frequency. The a:b ratio determines the figure structure '
          '(3:2, 5:4, etc.). Integer ratios close.'),
    'delta': ('Phase offset (radians)',
              'Phase offset (radians). delta=pi/2 gives the classic '
              'upright Lissajous; delta=0 collapses to a line for '
              'a:b=1.'),
    'scale': ('Overall scale factor',
              'Overall scale factor for the butterfly curve. Affects '
              'the bounding box only; level distribution is invariant.'),
    'm': ('Symmetry order',
          'Symmetry order. Integer m gives m-fold symmetry (m=4 → '
          'square-like, m=6 → hexagonal, etc.).'),
    'n1': ('Shape exponent 1 (>0)',
           'Shape exponent 1 (must be > 0). Lower values produce more '
           'pronounced features; higher values smooth them.'),
    'n2': ('Shape exponent 2',
           'Shape exponent 2. Together with n3, controls how rounded '
           'vs. pinched the corners are.'),
    'n3': ('Shape exponent 3',
           'Shape exponent 3. n2=n3 gives symmetric corners.'),
    'x_expr': ('x(t) — numpy math (sin, cos, exp, sqrt, pi, ...)',
               'x(t) expression. Available: sin cos tan asin acos atan '
               'atan2 sinh cosh tanh exp log log2 log10 sqrt cbrt abs '
               'sign floor ceil round pow minimum maximum, plus pi e '
               'tau. t is in [0, 2*pi). Example: sin(3*t) + 0.5*cos(7*t).'),
    'y_expr': ('y(t) — numpy math (sin, cos, exp, sqrt, pi, ...)',
               'y(t) expression. Same available functions as x(t). '
               'Example: cos(2*t) + 0.3*sin(5*t).'),
}


def build_family_param_grid(parent, family, family_specs, param_vars):
    """Rebuild `parent`'s children as a grid of per-param widgets.

    Args:
        parent: ttk.LabelFrame (or similar) whose children will be
            cleared and replaced with the new param widgets.
        family: key into `family_specs`, e.g. 'hypo', 'rose'.
        family_specs: dict from curve_family name to {params: {...}}.
        param_vars: nested dict {family_name: {param_name: tk.Var}}
            containing the Tk variables bound to each entry.
    """
    for child in parent.winfo_children():
        child.destroy()
    spec = family_specs.get(family)
    if not spec:
        return

    # Lissajous reuses 'a' as a frequency, not amplitude; override its
    # hint locally.
    help_dict = FAMILY_PARAM_HELP
    if family == 'lissajous':
        help_dict = dict(FAMILY_PARAM_HELP)
        help_dict['a'] = ('X frequency',
                          'X frequency. The a:b ratio determines the '
                          'figure structure (3:2, 5:4, etc.). Integer '
                          'ratios produce a closed Lissajous figure.')

    for i, (pname, default_v) in enumerate(spec['params'].items()):
        short, long_ = help_dict.get(pname, ('', ''))
        ttk.Label(parent, text=f"{pname}:").grid(
            row=i, column=0, sticky=tk.W, padx=4, pady=2)
        var = param_vars.get(family, {}).get(pname)
        entry_w = 32 if isinstance(default_v, str) else 10
        entry = ttk.Entry(parent, textvariable=var, width=entry_w)
        entry.grid(row=i, column=1, sticky=tk.W, padx=4, pady=2)
        hint_label = ttk.Label(parent, text=short, foreground='#555555')
        hint_label.grid(row=i, column=2, sticky=tk.W, padx=8, pady=2)
        if long_:
            create_tooltip(entry, long_)
            create_tooltip(hint_label, long_)
