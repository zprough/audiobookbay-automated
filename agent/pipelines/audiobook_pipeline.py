from __future__ import annotations

import logging
import shutil
from pathlib import Path

from agent.adapters.audiobookshelf import AudiobookshelfAdapter
from agent.models.job import Job
from agent.models.result import PipelineResult
from agent.services.archive_extractor import ArchiveExtractorService
from agent.services.converter import ConverterService
from agent.services.cover_art import CoverArtService
from agent.services.decision_service import DecisionService
from agent.services.filesystem import FilesystemService
from agent.services.inspector import InspectorService
from agent.services.metadata_service import MetadataService
from agent.services.organizer import OrganizerService
from agent.services.validator import ValidatorService

logger = logging.getLogger(__name__)


class AudiobookPipeline:
	def __init__(
		self,
		filesystem: FilesystemService,
		inspector: InspectorService,
		decisions: DecisionService,
		converter: ConverterService,
		metadata: MetadataService,
		cover_art: CoverArtService,
		organizer: OrganizerService,
		validator: ValidatorService,
		audiobookshelf: AudiobookshelfAdapter,
		archives: ArchiveExtractorService,
		work_root: Path,
		failed_root: Path,
	) -> None:
		self.filesystem = filesystem
		self.inspector = inspector
		self.decisions = decisions
		self.converter = converter
		self.metadata = metadata
		self.cover_art = cover_art
		self.organizer = organizer
		self.validator = validator
		self.audiobookshelf = audiobookshelf
		self.archives = archives
		self.work_root = work_root
		self.failed_root = failed_root

	def run(self, job: Job) -> PipelineResult:
		job.mark_running()
		logger.info("job_start id=%s source=%s", job.id, job.source_path)
		work_dir = None
		try:
			work_dir = self.filesystem.create_job_work_dir(self.work_root, job.source_path)
			effective_source = self.archives.extract_if_archive(job.source_path, work_dir)
			context = self.inspector.inspect(effective_source)
			decision = self.decisions.decide(context)

			conversion = self.converter.run(context, decision, work_dir)
			if not conversion.ok or conversion.output_path is None:
				raise RuntimeError(conversion.message)

			metadata_result = self.metadata.enrich(conversion.output_path, decision)
			if not metadata_result.ok or metadata_result.output_path is None:
				raise RuntimeError(metadata_result.message)

			organized = self.organizer.organize(metadata_result.output_path, decision)
			if not organized.ok or organized.output_path is None:
				raise RuntimeError(organized.message)

			self.cover_art.attach_cover_if_found(job.source_path, organized.output_path.parent)
			validated = self.validator.validate_output(organized.output_path.parent)
			if not validated.ok:
				raise RuntimeError(validated.message)

			self.audiobookshelf.trigger_rescan()
			self._cleanup_source(job.source_path)
			job.mark_succeeded()
			return PipelineResult(
				success=True,
				job_id=job.id,
				message="Processed successfully",
				final_path=organized.output_path,
				needs_human_review=decision.needs_human_review,
			)
		except Exception as error:
			job.mark_failed()
			self._move_to_failed(job.source_path)
			return PipelineResult(
				success=False,
				job_id=job.id,
				message=f"Processing failed: {error}",
				needs_human_review=True,
			)
		finally:
			if work_dir is not None:
				shutil.rmtree(work_dir, ignore_errors=True)

	def _cleanup_source(self, source_path: Path) -> None:
		# Prevents bootstrap_existing/watcher from reprocessing a finished folder
		# whose .abb-complete marker would otherwise still be sitting in INPUT_DIR.
		if not source_path.exists():
			return
		try:
			if source_path.is_dir():
				shutil.rmtree(source_path)
			else:
				source_path.unlink()
		except OSError as error:
			logger.warning("source_cleanup_failed source=%s error=%s", source_path, error)

	def _move_to_failed(self, source_path: Path) -> None:
		if not source_path.exists():
			return
		destination = self.failed_root / source_path.name
		if destination.exists():
			destination = self.failed_root / f"{source_path.stem}.failed{source_path.suffix}"
		self.filesystem.safe_move(source_path, destination)
