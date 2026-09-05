from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import requests

from agent.models.result import OperationResult

logger = logging.getLogger(__name__)

# Written by the web app alongside the download (see app/clients/metadata_sidecar.py);
# must match META_FILENAME there.
SIDECAR_FILENAME = ".abb-meta.json"


class CoverArtService:
	def attach_cover_if_found(self, source_path: Path, output_dir: Path) -> OperationResult:
		candidates = []
		if source_path.is_dir():
			candidates.extend(source_path.glob("cover.*"))
			candidates.extend(source_path.glob("folder.*"))
		else:
			candidates.extend(source_path.parent.glob("cover.*"))
			candidates.extend(source_path.parent.glob("folder.*"))

		image_candidates = [
			item for item in candidates if item.suffix.lower() in {".jpg", ".jpeg", ".png"}
		]
		output_dir.mkdir(parents=True, exist_ok=True)
		destination = output_dir / "cover.jpg"

		if image_candidates:
			shutil.copy2(image_candidates[0], destination)
			return OperationResult(ok=True, message="Cover art copied", output_path=destination)

		cover_url = self._read_cover_url(source_path)
		if cover_url and self._download_cover(cover_url, destination):
			return OperationResult(ok=True, message="Cover art downloaded", output_path=destination)

		return OperationResult(ok=True, message="No cover art found")

	def _read_cover_url(self, source_path: Path) -> str | None:
		sidecar_dir = source_path if source_path.is_dir() else source_path.parent
		sidecar_path = sidecar_dir / SIDECAR_FILENAME
		if not sidecar_path.exists():
			return None
		try:
			data = json.loads(sidecar_path.read_text())
		except (OSError, json.JSONDecodeError):
			return None
		return data.get("cover_url") or None

	def _download_cover(self, url: str, destination: Path) -> bool:
		try:
			response = requests.get(url, timeout=15)
			response.raise_for_status()
		except requests.RequestException as exc:
			logger.warning("cover_download_failed url=%s error=%s", url, exc)
			return False
		destination.write_bytes(response.content)
		return True
