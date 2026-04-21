# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for RestimFunscriptProcessor
Bundles VLC (libvlc.dll, libvlccore.dll, plugins/) for self-contained video playback.
Uses onedir mode — zip the output folder for distribution.
"""
import os
import glob
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ---------------------------------------------------------------------------
# Version (read from version.py without importing the whole app)
# ---------------------------------------------------------------------------
import re
with open('version.py') as _f:
    _m = re.search(r'__version__\s*=\s*"([^"]+)"', _f.read())
_version = _m.group(1) if _m else 'unknown'
_exe_name = f'RestimFunscriptProcessor-v{_version}'

# ---------------------------------------------------------------------------
# VLC binaries
# ---------------------------------------------------------------------------
VLC_DIR = r'C:\Program Files\VideoLAN\VLC'

datas = [('config.event_definitions.yml', '.')]
binaries = []

if os.path.exists(VLC_DIR):
    # Core DLLs — placed in the exe root so python-vlc finds them
    for dll in ('libvlc.dll', 'libvlccore.dll'):
        src = os.path.join(VLC_DIR, dll)
        if os.path.exists(src):
            binaries.append((src, '.'))
    # Plugin DLLs — placed in plugins/<subdir>/ relative to exe root
    for src in glob.glob(os.path.join(VLC_DIR, 'plugins', '**', '*.dll'),
                         recursive=True):
        rel_dest = os.path.relpath(os.path.dirname(src), VLC_DIR)
        binaries.append((src, rel_dest))

# ---------------------------------------------------------------------------
# Python packages
# ---------------------------------------------------------------------------
hiddenimports = [
    'tkinter',
    'numpy',
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
    'matplotlib.patches',
    'json',
    'pathlib',
    'processing.linear_mapping',
    'processing.motion_axis_generation',
    'vlc',
]

for _pkg in ('ui', 'processing'):
    _r = collect_all(_pkg)
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]

# sv_ttk (optional dark theme — include if installed)
try:
    _r = collect_all('sv_ttk')
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]
except Exception:
    pass

# tkinterdnd2 (optional drag-and-drop — include if installed)
try:
    _r = collect_all('tkinterdnd2')
    datas    += _r[0]
    binaries += _r[1]
    hiddenimports += _r[2]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_vlc.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],                         # onedir: no a.binaries/a.datas here
    exclude_binaries=True,      # onedir
    name=_exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['libvlc.dll', 'libvlccore.dll'],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['libvlc.dll', 'libvlccore.dll'],
    name=_exe_name,
)
