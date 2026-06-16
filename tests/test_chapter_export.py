#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from processing.chapter_export import (
    ms_to_ofs_time,
    events_to_chapters,
    merge_chapter_lists,
    merge_ofs_chapters,
    enrich_events_from_timeline,
    write_chapters_to_funscript,
    ChapterExportOptions,
    export_chapters,
)
from processing.event_display import format_event_display_name
from funscript import Funscript
import json
import tempfile


class TestChapterExport(unittest.TestCase):

    def test_ms_to_ofs_time(self):
        self.assertEqual(ms_to_ofs_time(0), "00:00:00.000")
        self.assertEqual(ms_to_ofs_time(60000), "00:01:00.000")
        self.assertEqual(ms_to_ofs_time(3661234), "01:01:01.234")

    def test_format_event_display_name(self):
        self.assertEqual(format_event_display_name("mcb_extract_4p"), "MCB - Extract 4P")
        self.assertEqual(format_event_display_name("edge"), "General - Edge")

    def test_events_to_chapters_with_duration(self):
        events = [{
            "time": 60000,
            "name": "edge",
            "final_params": {"duration_ms": 30000},
        }]
        chapters = events_to_chapters(events)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["name"], "General - Edge")
        self.assertEqual(chapters[0]["startTime"], "00:01:00.000")
        self.assertEqual(chapters[0]["endTime"], "00:01:30.000")

    def test_events_to_chapters_next_event_boundary(self):
        events = [
            {"time": 1000, "name": "edge", "final_params": {"duration_ms": 0}},
            {"time": 5000, "name": "tranquil", "final_params": {"duration_ms": 2000}},
        ]
        chapters = events_to_chapters(events)
        self.assertEqual(chapters[0]["endTime"], "00:00:05.000")
        self.assertEqual(chapters[1]["endTime"], "00:00:07.000")

    def test_merge_ofs_chapters_preserves_metadata(self):
        metadata = {"creator": "Test", "metadata": {"generator": "App"}}
        chapters = [{"name": "General - Edge", "startTime": "00:00:01.000", "endTime": "00:00:02.000"}]
        merged = merge_ofs_chapters(metadata, chapters)
        self.assertEqual(merged["creator"], "Test")
        self.assertEqual(merged["metadata"]["generator"], "App")
        self.assertEqual(merged["metadata"]["chapters"], chapters)

    def test_write_chapters_to_funscript(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.funscript"
            path.write_text(json.dumps({"actions": [{"at": 0, "pos": 50}]}), encoding="utf-8")
            chapters = [{
                "name": "General - Edge",
                "startTime": "00:00:01.000",
                "endTime": "00:00:02.000",
            }]
            write_chapters_to_funscript(path, chapters)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["metadata"]["chapters"], chapters)

    def test_export_chapters_funscript_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "video.funscript"
            base.write_text(json.dumps({"actions": [{"at": 0, "pos": 50}, {"at": 10000, "pos": 50}]}), encoding="utf-8")
            events = enrich_events_from_timeline(
                [{"time": 1000, "name": "edge", "params": {"duration_ms": 2000}}],
                {"edge": {"default_params": {"duration_ms": 1000}}},
            )
            result = export_chapters(
                events,
                "video",
                tmp_path,
                ChapterExportOptions(write_funscript=True),
            )
            self.assertTrue(any("video.funscript" in m for m in result.messages))


    def test_merge_chapter_lists_keeps_existing(self):
        existing = [{
            "name": "Intro",
            "startTime": "00:00:00.000",
            "endTime": "00:00:30.000",
        }]
        new = [{
            "name": "General - Edge",
            "startTime": "00:01:00.000",
            "endTime": "00:01:30.000",
        }]
        merged = merge_chapter_lists(existing, new)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["name"], "Intro")
        self.assertEqual(merged[1]["name"], "General - Edge")

    def test_merge_chapter_lists_dedupes_identical(self):
        chapter = {"name": "Intro", "startTime": "00:00:00.000", "endTime": "00:00:30.000"}
        merged = merge_chapter_lists([chapter], [chapter.copy()])
        self.assertEqual(len(merged), 1)

    def test_export_merges_existing_funscript_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "video.funscript"
            base.write_text(json.dumps({
                "actions": [{"at": 0, "pos": 50}],
                "metadata": {
                    "chapters": [{
                        "name": "Existing Scene",
                        "startTime": "00:00:10.000",
                        "endTime": "00:00:40.000",
                    }]
                },
            }), encoding="utf-8")
            events = enrich_events_from_timeline(
                [{"time": 60000, "name": "edge", "params": {"duration_ms": 2000}}],
                {"edge": {"default_params": {"duration_ms": 1000}}},
            )
            result = export_chapters(
                events,
                "video",
                tmp_path,
                ChapterExportOptions(write_funscript=True),
            )
            data = json.loads(base.read_text(encoding="utf-8"))
            chapters = data["metadata"]["chapters"]
            self.assertEqual(len(chapters), 2)
            self.assertEqual(chapters[0]["name"], "Existing Scene")
            self.assertTrue(any("Merged" in m for m in result.messages))


if __name__ == "__main__":
    unittest.main()
