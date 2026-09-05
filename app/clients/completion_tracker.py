"""
Background poller that marks a download folder complete once its contents
stop changing, for download clients that don't block until finished
(qBittorrent, Transmission, Deluge). Real-Debrid's manager already blocks
until the file is fully downloaded, so it never needs to go through this
tracker - see app/app.py's /send route.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

from .metadata_sidecar import mark_complete, write_sidecar

logger = logging.getLogger(__name__)

_STATE_FILE = os.getenv("ABB_PENDING_STATE_FILE", "/config/.abb-pending.json")
_POLL_INTERVAL_SEC = int(os.getenv("ABB_COMPLETION_POLL_INTERVAL_SEC", "15"))
_MIN_STABLE_AGE_SEC = int(os.getenv("ABB_COMPLETION_MIN_AGE_SEC", "30"))

_lock = threading.Lock()
_pending: Dict[str, Dict[str, Any]] = {}
_started = False


def _load_state() -> None:
    global _pending
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as fh:
            _pending = json.load(fh)
    except (OSError, json.JSONDecodeError):
        _pending = {}


def _save_state() -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_FILE) or ".", exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(_pending, fh)
    except OSError as exc:
        logger.warning("completion_tracker: failed to persist state: %s", exc)


def track(save_path: str, metadata: Dict[str, Any]) -> None:
    """Register a save_path to be watched for completion."""
    with _lock:
        _pending[save_path] = {
            "metadata": metadata,
            "last_snapshot": None,
            "last_seen_stable_at": None,
        }
        _save_state()
    _ensure_started()


def _snapshot(save_path: str) -> Tuple[int, int, float]:
    total_size = 0
    file_count = 0
    latest_mtime = 0.0
    for root, _dirs, files in os.walk(save_path):
        for name in files:
            if name.startswith(".abb-"):
                continue
            file_path = os.path.join(root, name)
            try:
                stat = os.stat(file_path)
            except OSError:
                continue
            total_size += stat.st_size
            file_count += 1
            latest_mtime = max(latest_mtime, stat.st_mtime)
    return (total_size, file_count, latest_mtime)


def _poll_once() -> None:
    with _lock:
        items = list(_pending.items())

    for save_path, entry in items:
        if not os.path.isdir(save_path):
            continue

        snapshot = _snapshot(save_path)
        _total_size, file_count, _mtime = snapshot
        if file_count == 0:
            continue

        now = time.time()
        if snapshot == tuple(entry.get("last_snapshot") or ()):
            stable_since = entry.get("last_seen_stable_at") or now
            if now - stable_since >= _MIN_STABLE_AGE_SEC:
                write_sidecar(save_path, entry["metadata"])
                mark_complete(save_path)
                logger.info("completion_tracker: marked complete save_path=%s", save_path)
                with _lock:
                    _pending.pop(save_path, None)
                    _save_state()
                continue
            with _lock:
                entry["last_seen_stable_at"] = stable_since
        else:
            with _lock:
                entry["last_snapshot"] = list(snapshot)
                entry["last_seen_stable_at"] = None

        with _lock:
            _save_state()


def _run_forever() -> None:
    while True:
        try:
            _poll_once()
        except Exception:  # noqa: BLE001 - keep the poller alive no matter what
            logger.exception("completion_tracker: poll iteration failed")
        time.sleep(_POLL_INTERVAL_SEC)


def _ensure_started() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    _load_state()
    thread = threading.Thread(target=_run_forever, daemon=True, name="completion-tracker")
    thread.start()
