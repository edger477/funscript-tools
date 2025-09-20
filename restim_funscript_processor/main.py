#!/usr/bin/env python3
"""
Restim Funscript Processor
A GUI application for processing funscript files for electrostimulation devices.
"""

import sys
import logging
from pathlib import Path

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