"""Convert custom events to OFS chapters in funscript metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from funscript import Funscript
from processing.event_display import format_event_display_name


class ChapterExportError(Exception):
    pass


@dataclass
class ChapterExportOptions:
    write_funscript: bool = False
    video_duration_ms: Optional[int] = None


@dataclass
class ChapterExportResult:
    messages: List[str] = field(default_factory=list)


def event_file_base_name(event_file_path: Path) -> str:
    name = event_file_path.name.replace(".events.yml", "").replace(".events.yaml", "")
    if not name:
        raise ChapterExportError(
            f"Could not determine base name from event file: {event_file_path.name}"
        )
    return name


def ms_to_ofs_time(ms: int) -> str:
    ms = int(ms)
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def enrich_events_from_timeline(
    events: List[Dict[str, Any]],
    event_definitions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    enriched = []
    for ev in events:
        event_name = ev["name"]
        if event_name not in event_definitions:
            raise ChapterExportError(
                f"Event '{event_name}' is not defined in event_definitions.yml."
            )
        final_params = event_definitions[event_name].get("default_params", {}).copy()
        if "params" in ev:
            final_params.update(ev["params"])
        enriched.append({
            "time": int(ev["time"]),
            "name": event_name,
            "final_params": final_params,
        })
    return sorted(enriched, key=lambda x: x["time"])


def _event_duration_ms(event: Dict[str, Any]) -> int:
    if "final_params" in event:
        return int(event["final_params"].get("duration_ms", 0) or 0)
    return int(event.get("params", {}).get("duration_ms", 0) or 0)


def events_to_chapters(
    events: List[Dict[str, Any]],
    *,
    duration_fallback_ms: Optional[int] = None,
) -> List[Dict[str, str]]:
    if not events:
        return []

    chapters: List[Dict[str, str]] = []
    for i, event in enumerate(events):
        start_ms = int(event["time"])
        duration_ms = _event_duration_ms(event)

        if duration_ms > 0:
            end_ms = start_ms + duration_ms
        elif i + 1 < len(events):
            end_ms = int(events[i + 1]["time"])
        elif duration_fallback_ms is not None and duration_fallback_ms > start_ms:
            end_ms = duration_fallback_ms
        else:
            end_ms = None

        chapter: Dict[str, str] = {
            "name": format_event_display_name(event["name"]),
            "startTime": ms_to_ofs_time(start_ms),
        }
        if end_ms is not None:
            chapter["endTime"] = ms_to_ofs_time(end_ms)
        chapters.append(chapter)
    return chapters


def _chapter_sort_key(chapter: Dict[str, str]) -> int:
    return _ofs_time_to_ms(chapter["startTime"])


def _chapter_identity(chapter: Dict[str, str]) -> tuple:
    end = chapter.get("endTime", "")
    return (chapter.get("name", ""), chapter.get("startTime", ""), end)


def merge_chapter_lists(
    existing: List[Dict[str, str]],
    new_chapters: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Combine chapter lists, keeping existing entries and appending non-duplicates."""
    merged: List[Dict[str, str]] = []
    seen = set()
    for chapter in existing + new_chapters:
        normalized = {
            "name": chapter.get("name", ""),
            "startTime": chapter.get("startTime", ""),
        }
        if chapter.get("endTime"):
            normalized["endTime"] = chapter["endTime"]
        ident = _chapter_identity(normalized)
        if ident in seen:
            continue
        seen.add(ident)
        merged.append(normalized)
    merged.sort(key=_chapter_sort_key)
    return merged


def read_chapters_from_funscript(base_funscript_path: Path) -> List[Dict[str, str]]:
    if not base_funscript_path.exists():
        return []
    fs = Funscript.from_file(base_funscript_path)
    nested = fs.metadata.get("metadata") if fs.metadata else None
    if not isinstance(nested, dict):
        return []
    chapters = nested.get("chapters")
    if not isinstance(chapters, list):
        return []
    return [c for c in chapters if isinstance(c, dict) and c.get("startTime")]


def merge_ofs_chapters(metadata: Optional[Dict[str, Any]], chapters: List[Dict[str, str]]) -> Dict[str, Any]:
    if metadata is None:
        metadata = {}
    nested = metadata.get("metadata")
    if not isinstance(nested, dict):
        nested = {}
        metadata["metadata"] = nested
    nested["chapters"] = chapters
    return metadata


def write_chapters_to_funscript(base_funscript_path: Path, chapters: List[Dict[str, str]]) -> None:
    fs = Funscript.from_file(base_funscript_path)
    fs.metadata = merge_ofs_chapters(fs.metadata, chapters)
    fs.save_to_path(base_funscript_path)


def _ofs_time_to_ms(time_str: str) -> int:
    parts = time_str.split(":")
    if len(parts) != 3:
        raise ChapterExportError(f"Invalid OFS time string: {time_str}")
    hours = int(parts[0])
    sec_parts = parts[2].split(".")
    minutes = int(parts[1])
    seconds = int(sec_parts[0])
    millis = int(sec_parts[1]) if len(sec_parts) > 1 else 0
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000 + millis


def funscript_duration_ms(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    fs = Funscript.from_file(path)
    if len(fs.x) == 0:
        return None
    return int(max(fs.x) * 1000)


def resolve_duration_fallback_ms(
    options: ChapterExportOptions,
    base_funscript_path: Path,
) -> Optional[int]:
    if options.video_duration_ms is not None and options.video_duration_ms > 0:
        return int(options.video_duration_ms)
    return funscript_duration_ms(base_funscript_path)


def export_chapters(
    events: List[Dict[str, Any]],
    base_name: str,
    events_dir: Path,
    options: ChapterExportOptions,
) -> ChapterExportResult:
    if not options.write_funscript:
        return ChapterExportResult()

    base_funscript_path = events_dir / f"{base_name}.funscript"
    duration_fallback = resolve_duration_fallback_ms(options, base_funscript_path)

    existing = read_chapters_from_funscript(base_funscript_path)
    new_chapters = events_to_chapters(events, duration_fallback_ms=duration_fallback)
    chapters = merge_chapter_lists(existing, new_chapters)
    if not chapters:
        return ChapterExportResult(messages=["No chapters to export."])

    result = ChapterExportResult()
    added_count = len(chapters) - len(existing)

    if base_funscript_path.exists():
        write_chapters_to_funscript(base_funscript_path, chapters)
        if existing:
            result.messages.append(
                f"Merged {added_count} new chapter(s) with {len(existing)} existing "
                f"in {base_funscript_path.name} ({len(chapters)} total)"
            )
        else:
            result.messages.append(
                f"Wrote {len(chapters)} chapter(s) to {base_funscript_path.name}"
            )
    else:
        result.messages.append(
            f"Skipped funscript chapters: {base_funscript_path.name} not found"
        )

    return result
