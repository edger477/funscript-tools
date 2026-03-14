"""
tests/test_cli.py

Tests for the cli.py adapter layer.

These are the canonical tests — they call only cli.py, never upstream
internals directly. If these pass, the adapter contract is intact regardless
of what changed upstream.

Run:
    python -m pytest tests/test_cli.py -v
    python tests/test_cli.py          # without pytest
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import cli

SAMPLE = Path(__file__).parent.parent / "examples" / "sample.funscript"

# Minimal inline funscript for tests that don't need the full sample
MINIMAL_FUNSCRIPT = {
    "version": 1,
    "actions": [
        {"at": 0,    "pos": 0},
        {"at": 500,  "pos": 100},
        {"at": 1000, "pos": 5},
        {"at": 1500, "pos": 95},
        {"at": 2000, "pos": 10},
        {"at": 3000, "pos": 100},
        {"at": 4000, "pos": 0},
        {"at": 5000, "pos": 80},
    ],
}


def _write_temp_funscript(data=None) -> Path:
    """Write a funscript to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".funscript", delete=False
    )
    json.dump(data or MINIMAL_FUNSCRIPT, f)
    f.close()
    return Path(f.name)


class TestLoadFile(unittest.TestCase):

    def test_load_sample(self):
        """load_file returns expected keys and sane values."""
        info = cli.load_file(str(SAMPLE))
        self.assertIn("name", info)
        self.assertIn("actions", info)
        self.assertIn("duration_s", info)
        self.assertIn("duration_fmt", info)
        self.assertIn("x", info)
        self.assertIn("y", info)
        self.assertGreater(info["actions"], 0)
        self.assertGreater(info["duration_s"], 0)
        self.assertGreater(len(info["x"]), 0)
        self.assertEqual(len(info["x"]), len(info["y"]))

    def test_load_values_in_range(self):
        """y values should be 0–100."""
        info = cli.load_file(str(SAMPLE))
        self.assertGreaterEqual(min(info["y"]), 0)
        self.assertLessEqual(max(info["y"]), 100)

    def test_load_missing_file(self):
        """load_file raises ValueError for missing files."""
        with self.assertRaises(ValueError):
            cli.load_file("/nonexistent/path/file.funscript")

    def test_load_wrong_extension(self):
        """load_file raises ValueError for non-.funscript files."""
        with self.assertRaises(ValueError):
            cli.load_file("/some/file.txt")

    def test_load_temp_file(self):
        """load_file works on a freshly written temp file."""
        p = _write_temp_funscript()
        try:
            info = cli.load_file(str(p))
            self.assertEqual(info["actions"], len(MINIMAL_FUNSCRIPT["actions"]))
        finally:
            p.unlink()


class TestGetDefaultConfig(unittest.TestCase):

    def test_returns_dict(self):
        cfg = cli.get_default_config()
        self.assertIsInstance(cfg, dict)

    def test_has_required_sections(self):
        cfg = cli.get_default_config()
        for section in ("general", "frequency", "volume", "pulse",
                        "alpha_beta_generation", "options"):
            self.assertIn(section, cfg, f"Missing config section: {section}")

    def test_independent_copies(self):
        """Each call returns an independent copy — mutations don't bleed."""
        cfg1 = cli.get_default_config()
        cfg2 = cli.get_default_config()
        cfg1["frequency"]["pulse_freq_min"] = 0.99
        self.assertNotEqual(
            cfg2["frequency"]["pulse_freq_min"], 0.99,
            "get_default_config() should return independent copies",
        )


class TestProcess(unittest.TestCase):

    def test_process_default(self):
        """process() with defaults succeeds and returns output files."""
        p = _write_temp_funscript()
        try:
            config = cli.get_default_config()
            # Write outputs next to the temp file
            result = cli.process(str(p), config)
            self.assertTrue(result["success"], msg=result.get("error"))
            self.assertIsInstance(result["outputs"], list)
            self.assertGreater(len(result["outputs"]), 0)
        finally:
            # Clean up temp file and any generated outputs
            stem = p.stem
            for f in p.parent.glob(f"{stem}*"):
                f.unlink(missing_ok=True)
            if p.parent.joinpath("funscript-temp").exists():
                import shutil
                shutil.rmtree(p.parent / "funscript-temp", ignore_errors=True)

    def test_process_returns_known_suffixes(self):
        """process() generates at least the core output types."""
        p = _write_temp_funscript()
        try:
            config = cli.get_default_config()
            result = cli.process(str(p), config)
            suffixes = {o["suffix"] for o in result["outputs"]}
            for expected in ("alpha", "beta", "frequency", "volume"):
                self.assertIn(expected, suffixes, f"Missing output: {expected}")
        finally:
            stem = p.stem
            for f in p.parent.glob(f"{stem}*"):
                f.unlink(missing_ok=True)
            import shutil
            shutil.rmtree(p.parent / "funscript-temp", ignore_errors=True)

    def test_process_missing_file(self):
        """process() on a missing file returns success=False."""
        config = cli.get_default_config()
        result = cli.process("/nonexistent/file.funscript", config)
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])


class TestListOutputs(unittest.TestCase):

    def test_empty_dir(self):
        """list_outputs returns empty list when nothing matches."""
        with tempfile.TemporaryDirectory() as d:
            outputs = cli.list_outputs(d, "nonexistent_stem")
            self.assertEqual(outputs, [])

    def test_finds_files(self):
        """list_outputs finds files matching the stem pattern."""
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "mystem.alpha.funscript").write_text("{}")
            (dp / "mystem.beta.funscript").write_text("{}")
            (dp / "other.alpha.funscript").write_text("{}")  # should not match

            outputs = cli.list_outputs(d, "mystem")
            suffixes = {o["suffix"] for o in outputs}
            self.assertIn("alpha", suffixes)
            self.assertIn("beta", suffixes)
            self.assertNotIn("other", suffixes)
            self.assertEqual(len(outputs), 2)


class TestPreviewElectrodePath(unittest.TestCase):

    def test_returns_expected_keys(self):
        result = cli.preview_electrode_path()
        self.assertIn("alpha", result)
        self.assertIn("beta", result)
        self.assertIn("label", result)
        self.assertIn("description", result)

    def test_all_algorithms(self):
        """All known algorithms return valid data."""
        for algo in cli.ALGORITHMS:
            result = cli.preview_electrode_path(algorithm=algo)
            self.assertGreater(len(result["alpha"]), 0, f"No data for {algo}")
            self.assertEqual(len(result["alpha"]), len(result["beta"]))

    def test_values_in_range(self):
        """Path values should stay within 0–1."""
        result = cli.preview_electrode_path()
        for v in result["alpha"]:
            self.assertGreaterEqual(v, -0.1)  # small tolerance for edge algorithms
            self.assertLessEqual(v, 1.1)


class TestPreviewFrequencyBlend(unittest.TestCase):

    def test_returns_expected_keys(self):
        result = cli.preview_frequency_blend()
        for key in ("frequency_ramp_pct", "frequency_speed_pct",
                    "pulse_speed_pct", "pulse_alpha_pct",
                    "frequency_label", "pulse_label", "overall_label"):
            self.assertIn(key, result)

    def test_percentages_sum_to_100(self):
        result = cli.preview_frequency_blend(2.0, 3.0)
        self.assertAlmostEqual(
            result["frequency_ramp_pct"] + result["frequency_speed_pct"],
            100.0, places=0
        )

    def test_ratio_1_is_equal_split(self):
        """Ratio of 1 means 100% of the second source."""
        result = cli.preview_frequency_blend(1.0, 1.0)
        self.assertAlmostEqual(result["frequency_speed_pct"], 100.0, places=0)


class TestPreviewPulseShape(unittest.TestCase):

    def test_returns_expected_keys(self):
        result = cli.preview_pulse_shape()
        for key in ("x", "y", "width", "rise", "label", "sharpness"):
            self.assertIn(key, result)

    def test_x_y_same_length(self):
        result = cli.preview_pulse_shape()
        self.assertEqual(len(result["x"]), len(result["y"]))

    def test_sharpness_values(self):
        sharp = cli.preview_pulse_shape(rise_min=0.0, rise_max=0.05)
        soft = cli.preview_pulse_shape(rise_min=0.5, rise_max=0.9)
        self.assertEqual(sharp["sharpness"], "sharp")
        self.assertEqual(soft["sharpness"], "soft")


class TestPreviewOutput(unittest.TestCase):

    def test_returns_original_data(self):
        """preview_output always returns original waveform data."""
        info = cli.load_file(str(SAMPLE))
        config = cli.get_default_config()
        result = cli.preview_output(info, config, "alpha")
        self.assertEqual(result["original_x"], info["x"])
        self.assertEqual(result["original_y"], info["y"])

    def test_available_outputs(self):
        """alpha, beta, speed, frequency, volume should all be previewable."""
        info = cli.load_file(str(SAMPLE))
        config = cli.get_default_config()
        for output_type in ("alpha", "beta", "speed", "frequency", "volume"):
            result = cli.preview_output(info, config, output_type)
            self.assertTrue(
                result["available"],
                f"preview_output failed for '{output_type}': {result['label']}"
            )
            self.assertGreater(len(result["output_x"]), 0)

    def test_unknown_output_graceful(self):
        """Unknown output type returns available=False, doesn't crash."""
        info = cli.load_file(str(SAMPLE))
        config = cli.get_default_config()
        result = cli.preview_output(info, config, "nonexistent_type")
        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
