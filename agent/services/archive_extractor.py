from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Written by the web app alongside the download (see app/clients/metadata_sidecar.py);
# must match META_FILENAME there.
SIDECAR_FILENAME = ".abb-meta.json"

# AudiobookBay frequently packages downloads (especially multi-book bundles)
# as archives rather than raw audio files; the inspector only recognizes
# .m4b/.m4a/.mp3, so these need to be unpacked before the pipeline can see
# the audio inside.
ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z"}

# Trailing volumes of a split archive (book.part2.rar, book.r00, ...); only
# the first volume needs to be handed to the extractor, it locates the rest.
_SPLIT_VOLUME = re.compile(r"\.part0*[2-9]\d*\.rar$|\.r\d{2,}$", re.IGNORECASE)


class ArchiveExtractorService:
	"""Extracts .rar/.zip/.7z downloads into a work directory using 7-Zip."""

	def __init__(self, binary: str = "7zz") -> None:
		self.binary = binary

	def extract_if_archive(self, source_path: Path, work_dir: Path) -> Path:
		"""Return the path the inspector should scan: `source_path` unchanged
		if it contains no archives, otherwise a work_dir subfolder holding
		everything extracted from them."""
		archives = self._find_archives(source_path)
		if not archives:
			return source_path

		extract_dir = work_dir / "extracted"
		extract_dir.mkdir(parents=True, exist_ok=True)
		for archive in archives:
			self._extract_one(archive, extract_dir)

		# The inspector reads title/author from the sidecar next to whatever
		# path it's given; since it's now given extract_dir, carry the
		# original download folder's sidecar along so that still works.
		if source_path.is_dir():
			sidecar = source_path / SIDECAR_FILENAME
			if sidecar.exists():
				shutil.copy2(sidecar, extract_dir / SIDECAR_FILENAME)
		return extract_dir

	def _find_archives(self, source_path: Path) -> list[Path]:
		if source_path.is_file():
			return [source_path] if source_path.suffix.lower() in ARCHIVE_EXTENSIONS else []

		found = []
		for path in sorted(source_path.iterdir()):
			if not path.is_file() or path.suffix.lower() not in ARCHIVE_EXTENSIONS:
				continue
			if _SPLIT_VOLUME.search(path.name):
				continue
			found.append(path)
		return found

	def _extract_one(self, archive: Path, extract_dir: Path) -> None:
		result = subprocess.run(
			[self.binary, "x", "-y", f"-o{extract_dir}", str(archive)],
			capture_output=True,
			text=True,
			timeout=600,
		)
		if result.returncode != 0:
			detail = result.stderr.strip() or result.stdout.strip()
			raise RuntimeError(f"Failed to extract archive '{archive.name}': {detail}")
		logger.info("archive_extracted archive=%s dest=%s", archive.name, extract_dir)
