"""
PyInstaller runtime hook — sets VLC_PLUGIN_PATH so libvlc can find its plugins
when running from the frozen onedir bundle.
"""
import os
import sys

if hasattr(sys, '_MEIPASS'):
    # onefile: everything extracted to _MEIPASS
    _base = sys._MEIPASS
else:
    # onedir: _base is the folder containing the exe
    _base = os.path.dirname(os.path.abspath(sys.executable))

_plugins = os.path.join(_base, 'plugins')
if os.path.isdir(_plugins):
    os.environ.setdefault('VLC_PLUGIN_PATH', _plugins)

# Ensure libvlc.dll is on the DLL search path (Python 3.8+ requires explicit add)
try:
    os.add_dll_directory(_base)
except (AttributeError, OSError):
    pass
