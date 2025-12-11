#!/usr/bin/env python3
"""
Test script for the Custom Event Processor feature (New Architecture).
"""
import unittest
import tempfile
import os
import zipfile
from pathlib import Path
import yaml
import numpy as np
import json
import shutil

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from funscript.funscript import funscript_cache
from processing.event_processor import process_events, EventProcessorError


class TestEventProcessor(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory with dummy funscript and event files, and event definitions."""
        funscript_cache.clear()
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)

        # Create a dummy event_definitions.yml
        self.event_definitions_path = self.test_path / "event_definitions.yml"
        shutil.copyfile(Path(__file__).parent.parent / "config" / "event_definitions.yml", self.event_definitions_path)
        
        with open(self.event_definitions_path, 'a') as f:
            f.write("""
  good_slave_test:
    default_params:
      duration_ms: 1000
      volume_shift: 0.2
      pulse_freq_hz: 27
      pulse_width: 0.45
    steps:
      - operation: apply_linear_change
        axis: volume
        params:
          start_value: $volume_shift
          duration_ms: $duration_ms
          mode: additive
      - operation: apply_linear_change
        axis: pulse_frequency
        params:
          start_value: $pulse_freq_hz
          duration_ms: $duration_ms
          mode: overwrite
      - operation: apply_linear_change
        axis: pulse_width
        params:
          start_value: $pulse_width
          duration_ms: $duration_ms
          mode: overwrite

  edge_test:
    default_params:
      duration_ms: 1000
      volume_shift: 0.1
      buzz_freq: 2
      buzz_intensity: 0.5
      ramp_up: 100
    steps:
      - operation: apply_linear_change
        axis: volume
        params:
          start_value: $volume_shift
          duration_ms: $duration_ms
          mode: additive
      - operation: apply_modulation
        axis: volume
        params:
          waveform: sin
          frequency: $buzz_freq
          amplitude: $buzz_intensity
          duration_ms: $duration_ms
          ramp_in_ms: $ramp_up
          mode: additive
""")

        # Create a dummy user event file
        self.event_file_path = self.test_path / "test.events.yml"
        self.user_events_data = {
            "events": [
                {"time": 500, "name": "good_slave_test", "params": {"duration_ms": 1000}},
                {"time": 1500, "name": "edge_test", "params": {"duration_ms": 1000}}
            ]
        }
        with open(self.event_file_path, "w") as f:
            yaml.dump(self.user_events_data, f)

        # Create dummy funscript files
        self.volume_path = self.test_path / "test.volume.funscript"
        self.pulse_freq_path = self.test_path / "test.pulse_frequency.funscript"
        self.pulse_width_path = self.test_path / "test.pulse_width.funscript"
        
        self.actions = [{"at": i * 100, "pos": 50} for i in range(31)]
        self.pulse_freq_actions = [{"at": i * 100, "pos": 25} for i in range(31)]
        
        with open(self.volume_path, "w") as f: json.dump({"actions": self.actions}, f)
        with open(self.pulse_freq_path, "w") as f: json.dump({"actions": self.pulse_freq_actions}, f)
        with open(self.pulse_width_path, "w") as f: json.dump({"actions": self.actions}, f) # Same as volume initially

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_event_processing(self):
        """Test the full event processing workflow with the new architecture."""
        process_events(str(self.event_file_path), True, self.event_definitions_path)

        mod_volume_fs = Funscript.from_file(self.volume_path)
        mod_pulse_freq_fs = Funscript.from_file(self.pulse_freq_path)
        mod_pulse_width_fs = Funscript.from_file(self.pulse_width_path)

        # Verify 'good_slave_test' (500ms to 1500ms)
        gs_indices = np.where((mod_volume_fs.x >= 0.5) & (mod_volume_fs.x < 1.5))[0]
        self.assertTrue(np.allclose(mod_volume_fs.y[gs_indices], 0.7))
        self.assertTrue(np.allclose(mod_pulse_freq_fs.y[gs_indices], 0.13)) # 27 / 200 = 0.135 -> 0.13
        self.assertTrue(np.allclose(mod_pulse_width_fs.y[gs_indices], 0.45))

        # Verify 'edge_test' (1500ms to 2500ms)
        edge_indices = np.where((mod_volume_fs.x >= 1.5) & (mod_volume_fs.x < 2.5))[0]
        self.assertFalse(np.allclose(mod_volume_fs.y[edge_indices], 0.6))
        self.assertGreater(np.max(mod_volume_fs.y[edge_indices]), 0.6)

        # Verify values outside event ranges are unchanged
        before_indices = np.where(mod_volume_fs.x < 0.5)[0]
        after_indices = np.where(mod_volume_fs.x >= 2.5)[0]
        self.assertTrue(np.allclose(mod_volume_fs.y[before_indices], 0.5))
        self.assertTrue(np.allclose(mod_volume_fs.y[after_indices], 0.5))
        self.assertTrue(np.allclose(mod_pulse_freq_fs.y[after_indices], 0.25))

if __name__ == "__main__":
    print("Running Custom Event Processor Tests (New Architecture)...")
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventProcessor))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    print("Tests finished.")
    if result.failures or result.errors: sys.exit(1)