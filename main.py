#!/usr/bin/env python3
"""
Restim Funscript Processor
A GUI application for processing funscript files for electrostimulation devices.
"""

import sys
import logging
import os
from pathlib import Path

# Set VLC plugin path when running as a frozen PyInstaller exe
if getattr(sys, 'frozen', False):
    os.environ.setdefault('VLC_PLUGIN_PATH',
                          os.path.join(sys._MEIPASS, 'plugins'))

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import main

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Start the GUI application
    main()