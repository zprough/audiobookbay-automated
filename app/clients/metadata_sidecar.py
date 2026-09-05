"""
Sidecar metadata + completion marker files written alongside a queued download.

These are the bridge between the web app (which knows the AudiobookBay title,
cover art URL, language, categories, etc.) and the agent (which only sees
files on disk). Filenames here must stay in sync with the agent's consumers:
  - agent/services/watcher.py (COMPLETE_MARKER)
  - agent/worker.py (bootstrap_existing)
  - agent/services/inspector.py (SIDECAR_FILENAME)
  - agent/services/cover_art.py (SIDECAR_FILENAME)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

META_FILENAME = ".abb-meta.json"
COMPLETE_FILENAME = ".abb-complete"


def write_sidecar(save_path: str, metadata: Dict[str, Any]) -> None:
    """Write the `.abb-meta.json` sidecar describing a queued download."""
    path = Path(save_path)
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "title": metadata.get("title"),
        "cover_url": metadata.get("cover"),
        "source_link": metadata.get("link"),
        "categories": metadata.get("categories") or [],
        "language": metadata.get("language"),
        "queued_at": time.time(),
    }
    (path / META_FILENAME).write_text(json.dumps(payload, indent=2))


def mark_complete(save_path: str) -> None:
    """Write the `.abb-complete` marker the agent watches/bootstraps for."""
    path = Path(save_path)
    path.mkdir(parents=True, exist_ok=True)
    (path / COMPLETE_FILENAME).write_text(str(time.time()))
