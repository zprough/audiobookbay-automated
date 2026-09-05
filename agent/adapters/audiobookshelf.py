from __future__ import annotations

import requests

from agent.config import Settings
from agent.models.result import OperationResult


class AudiobookshelfAdapter:
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	def trigger_rescan(self) -> OperationResult:
		if not self.settings.enable_audiobookshelf_scan:
			return OperationResult(ok=True, message="Audiobookshelf scan disabled")
		if not self.settings.audiobookshelf_token:
			return OperationResult(ok=False, message="AUDIOBOOKSHELF_TOKEN missing")

		response = requests.post(
			f"{self.settings.audiobookshelf_url}/api/libraries/scan",
			headers={"Authorization": f"Bearer {self.settings.audiobookshelf_token}"},
			timeout=15,
		)
		if response.status_code >= 400:
			return OperationResult(
				ok=False,
				message="Audiobookshelf rescan failed",
				details={"status_code": str(response.status_code), "body": response.text[:500]},
			)
		return OperationResult(ok=True, message="Audiobookshelf scan triggered")
