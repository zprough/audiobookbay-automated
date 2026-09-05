from __future__ import annotations

import json
import re
from pathlib import Path

from agent.models.book_context import BookContext, InputType
from agent.services.filesystem import FilesystemService

# Written by the web app alongside the download (see app/clients/metadata_sidecar.py);
# must match META_FILENAME there.
SIDECAR_FILENAME = ".abb-meta.json"


class InspectorService:
    _title_author = re.compile(r"(?P<author>[^-]+)\s*-\s*(?P<title>.+)")

    def __init__(self, filesystem: FilesystemService) -> None:
        self.filesystem = filesystem

    def inspect(self, source_path: Path) -> BookContext:
        files = self.filesystem.list_audio_files(source_path)
        input_type = self._determine_input_type(source_path, files)

        sidecar = self._read_sidecar(source_path)
        sidecar_title = sidecar.get("title") if sidecar else None
        if sidecar_title:
            title, author = self._split_title_author(sidecar_title)
            confidence = 0.9
        else:
            title, author = self._parse_name(source_path)
            confidence = 0.5 if title else 0.0

        return BookContext(
            source_path=source_path,
            input_type=input_type,
            files=files,
            title=title,
            author=author,
            confidence=confidence,
            needs_human_review=input_type == InputType.unsupported,
        )

    def _read_sidecar(self, source_path: Path) -> dict | None:
        sidecar_dir = source_path if source_path.is_dir() else source_path.parent
        sidecar_path = sidecar_dir / SIDECAR_FILENAME
        if not sidecar_path.exists():
            return None
        try:
            return json.loads(sidecar_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def _determine_input_type(self, source_path: Path, files: list[Path]) -> InputType:
        if source_path.is_file() and source_path.suffix.lower() == ".m4b":
            return InputType.single_m4b
        if source_path.is_file() and source_path.suffix.lower() == ".m4a":
            return InputType.single_m4a
        if source_path.is_dir() and files and all(item.suffix.lower() == ".mp3" for item in files):
            return InputType.chapter_folder
        return InputType.unsupported

    def _parse_name(self, source_path: Path) -> tuple[str | None, str | None]:
        stem = source_path.stem if source_path.is_file() else source_path.name
        cleaned = stem.replace("_", " ").strip()
        return self._split_title_author(cleaned)

    def _split_title_author(self, raw_title: str) -> tuple[str | None, str | None]:
        cleaned = raw_title.strip()
        match = self._title_author.match(cleaned)
        if not match:
            return cleaned or None, None

        author = match.group("author").strip()
        title = match.group("title").strip()
        return title or None, author or None