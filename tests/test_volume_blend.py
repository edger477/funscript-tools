import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from funscript import Funscript
from processing.combining import combine_funscripts, blend_supplied_volume
from processing.basic_transforms import normalize_funscript
from processor import RestimProcessor
from config import DEFAULT_CONFIG


class TestBlendSuppliedVolume(unittest.TestCase):
    def test_blend_ratio_math(self):
        generated = Funscript([0.0, 1.0], [0.6, 0.8])
        external = Funscript([0.0, 1.0], [0.0, 1.0])
        ratio = 4.0
        result = blend_supplied_volume(generated, external, ratio)
        expected_y0 = (0.6 * 3 + 0.0) / 4
        expected_y1 = (0.8 * 3 + 1.0) / 4
        self.assertAlmostEqual(result.y[0], expected_y0, places=6)
        self.assertAlmostEqual(result.y[1], expected_y1, places=6)

    def test_output_range_mapping(self):
        generated = Funscript([0.0, 1.0], [0.0, 1.0])
        external = Funscript([0.0, 1.0], [0.0, 1.0])
        result = blend_supplied_volume(generated, external, 2.0, 0.35, 0.85)
        self.assertAlmostEqual(float(np.min(result.y)), 0.35, places=6)
        self.assertAlmostEqual(float(np.max(result.y)), 0.85, places=6)

    def test_combine_sequence(self):
        ramp = Funscript([0.0, 10.0], [0.0, 1.0])
        speed = Funscript([0.0, 10.0], [0.5, 0.5])
        generated = combine_funscripts(ramp, speed, 20.0, rest_level=0.4, ramp_up_duration=0.0)
        external = Funscript([0.0, 10.0], [1.0, 1.0])
        blended = blend_supplied_volume(generated, external, 4.0)
        self.assertGreater(float(blended.y[0]), float(generated.y[0]))
        self.assertLess(float(blended.y[0]), 1.0)

    def test_normalize_after_both_combines(self):
        generated = Funscript([0.0, 1.0], [0.2, 0.6])
        external = Funscript([0.0, 1.0], [0.0, 0.4])
        blended = blend_supplied_volume(generated, external, 4.0)
        normalized = normalize_funscript(blended)
        self.assertAlmostEqual(float(np.max(normalized.y)), 1.0, places=6)


class TestProcessorVolumeBlend(unittest.TestCase):
    def _make_main_funscript(self, path: Path):
        actions = [
            {"at": 0, "pos": 50},
            {"at": 10000, "pos": 60},
            {"at": 59000, "pos": 70},
            {"at": 60000, "pos": 80},
        ]
        path.write_text(json.dumps({"actions": actions}), encoding="utf-8")

    def _make_external_volume(self, path: Path):
        actions = [
            {"at": 0, "pos": 0},
            {"at": 60000, "pos": 100},
        ]
        path.write_text(json.dumps({"actions": actions}), encoding="utf-8")

    def test_blend_disabled_skips_combine_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "test.funscript"
            self._make_main_funscript(main)
            config = json.loads(json.dumps(DEFAULT_CONFIG))
            config["options"]["overwrite_existing_files"] = True
            config["options"]["normalize_volume"] = False
            config["volume"]["enable_volume_blend"] = False
            processor = RestimProcessor(config)
            self.assertTrue(processor.process(str(main)))
            volume = Funscript.from_file(tmp_path / "test.volume.funscript")
            meta = volume.metadata.get("metadata", {})
            self.assertNotIn("blended_with_supplied", meta)

    def test_blend_enabled_writes_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "test.funscript"
            external = tmp_path / "external.volume.funscript"
            self._make_main_funscript(main)
            self._make_external_volume(external)
            config = json.loads(json.dumps(DEFAULT_CONFIG))
            config["options"]["overwrite_existing_files"] = True
            config["options"]["normalize_volume"] = False
            config["prostate_generation"]["generate_prostate_files"] = False
            config["positional_axes"]["generate_legacy"] = False
            config["positional_axes"]["generate_motion_axis"] = False
            config["volume"]["enable_volume_blend"] = True
            config["volume"]["supplied_volume_path"] = str(external)
            config["volume"]["supplied_volume_combine_ratio"] = 4.0
            processor = RestimProcessor(config)
            self.assertTrue(processor.process(str(main)))
            volume = Funscript.from_file(tmp_path / "test.volume.funscript")
            meta = volume.metadata.get("metadata", {})
            self.assertTrue(meta.get("blended_with_supplied"))
            self.assertEqual(meta.get("supplied_volume_combine_ratio"), 4.0)

    def test_overlap_copies_before_blend(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "test.funscript"
            overlap = tmp_path / "test.volume.funscript"
            self._make_main_funscript(main)
            self._make_external_volume(overlap)
            config = json.loads(json.dumps(DEFAULT_CONFIG))
            config["options"]["overwrite_existing_files"] = True
            config["options"]["normalize_volume"] = False
            config["prostate_generation"]["generate_prostate_files"] = False
            config["positional_axes"]["generate_legacy"] = False
            config["positional_axes"]["generate_motion_axis"] = False
            config["volume"]["enable_volume_blend"] = True
            config["volume"]["supplied_volume_path"] = str(overlap)
            config["volume"]["supplied_volume_combine_ratio"] = 2.0
            processor = RestimProcessor(config)
            self.assertTrue(processor.process(str(main)))
            volume = Funscript.from_file(overlap)
            meta = volume.metadata.get("metadata", {})
            self.assertTrue(meta.get("blended_with_supplied"))


if __name__ == "__main__":
    unittest.main()
