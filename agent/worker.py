from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from pathlib import Path

from agent.models.job import Job
from agent.pipelines.audiobook_pipeline import AudiobookPipeline

logger = logging.getLogger(__name__)


class Worker:
	def __init__(self, pipeline: AudiobookPipeline) -> None:
		self.pipeline = pipeline
		self.queue: queue.Queue[Path] = queue.Queue()
		self._stop_event = threading.Event()

	def submit(self, source_path: Path) -> None:
		self.queue.put(source_path)
		logger.info("job_queued source=%s", source_path)

	def process_once(self, source_path: Path) -> None:
		if not source_path.exists():
			logger.warning("source_missing source=%s", source_path)
			return
		job = Job(id=str(uuid.uuid4()), source_path=source_path)
		result = self.pipeline.run(job)
		logger.info(
			"job_finished id=%s success=%s message=%s",
			result.job_id,
			result.success,
			result.message,
		)

	def run_forever(self) -> None:
		logger.info("worker_started")
		while not self._stop_event.is_set():
			try:
				source_path = self.queue.get(timeout=1)
			except queue.Empty:
				continue
			self.process_once(source_path)

	def stop(self) -> None:
		self._stop_event.set()

	def bootstrap_existing(self, input_dir: Path) -> None:
		# Keep this marker filename in sync with agent/services/watcher.py's
		# COMPLETE_MARKER and app/clients/metadata_sidecar.py's COMPLETE_FILENAME.
		complete_marker = ".abb-complete"
		for item in sorted(input_dir.iterdir()):
			if item.is_dir():
				if (item / complete_marker).exists():
					self.submit(item)
			elif item.suffix.lower() in {".m4b", ".m4a", ".mp3"}:
				self.submit(item)
		time.sleep(0.1)
