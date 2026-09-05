from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Written by the web app once a download has fully finished (see
# app/clients/metadata_sidecar.py); must match COMPLETE_FILENAME there.
COMPLETE_MARKER = ".abb-complete"
_AUDIO_SUFFIXES = {".m4b", ".m4a", ".mp3"}


class _IncomingHandler(FileSystemEventHandler):
	def __init__(self, watch_dir: Path, callback: Callable[[Path], None]) -> None:
		self.watch_dir = watch_dir
		self.callback = callback

	def on_created(self, event: FileSystemEvent) -> None:
		if event.is_directory:
			return
		candidate = Path(event.src_path)
		if candidate.name == COMPLETE_MARKER:
			# Folder-based download finished; safe to process the whole folder now.
			self.callback(candidate.parent)
			return
		if candidate.parent == self.watch_dir and candidate.suffix.lower() in _AUDIO_SUFFIXES:
			# A lone audio file dropped directly in the incoming root (manual drop).
			self.callback(candidate)


class WatcherService:
	def __init__(self, watch_dir: Path, on_item: Callable[[Path], None]) -> None:
		self.watch_dir = watch_dir
		self.on_item = on_item
		self.observer = Observer()

	def start(self) -> None:
		handler = _IncomingHandler(self.watch_dir, self.on_item)
		self.observer.schedule(handler, str(self.watch_dir), recursive=True)
		self.observer.start()
		logger.info("watcher_started dir=%s", self.watch_dir)

	def run_forever(self) -> None:
		self.start()
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			logger.info("watcher_stopping")
			self.observer.stop()
			self.observer.join()
