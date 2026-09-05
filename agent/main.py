from __future__ import annotations

import logging
import threading

from agent.adapters.audiobookshelf import AudiobookshelfAdapter
from agent.adapters.m4b_tool import M4BToolAdapter
from agent.adapters.picard import PicardAdapter
from agent.adapters.tone import ToneAdapter
from agent.config import Settings, configure_logging
from agent.pipelines.audiobook_pipeline import AudiobookPipeline
from agent.services.converter import ConverterService
from agent.services.cover_art import CoverArtService
from agent.services.decision_service import DecisionService
from agent.services.filesystem import FilesystemService
from agent.services.inspector import InspectorService
from agent.services.metadata_service import MetadataService
from agent.services.organizer import OrganizerService
from agent.services.validator import ValidatorService
from agent.services.watcher import WatcherService
from agent.worker import Worker


def build_worker(settings: Settings) -> tuple[Worker, WatcherService]:
	filesystem = FilesystemService()
	inspector = InspectorService(filesystem)
	decisions = DecisionService(settings)
	converter = ConverterService(M4BToolAdapter())
	metadata = MetadataService(PicardAdapter(), ToneAdapter(), enable_picard=settings.enable_picard)
	cover = CoverArtService()
	organizer = OrganizerService(filesystem, settings.library_dir)
	validator = ValidatorService()
	audiobookshelf = AudiobookshelfAdapter(settings)

	pipeline = AudiobookPipeline(
		filesystem=filesystem,
		inspector=inspector,
		decisions=decisions,
		converter=converter,
		metadata=metadata,
		cover_art=cover,
		organizer=organizer,
		validator=validator,
		audiobookshelf=audiobookshelf,
		work_root=settings.work_dir,
		failed_root=settings.failed_dir,
	)

	worker = Worker(pipeline)
	watcher = WatcherService(settings.input_dir, worker.submit)
	return worker, watcher


def main() -> None:
	settings = Settings.from_env()
	configure_logging(settings.log_level)
	settings.ensure_directories()

	worker, watcher = build_worker(settings)
	worker.bootstrap_existing(settings.input_dir)

	worker_thread = threading.Thread(target=worker.run_forever, daemon=True)
	worker_thread.start()

	logging.getLogger(__name__).info("audiobook_agent_started")
	watcher.run_forever()


if __name__ == "__main__":
	main()
