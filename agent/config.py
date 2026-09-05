from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


def _to_bool(value: str | None, default: bool = False) -> bool:
	if value is None:
		return default
	normalized = value.strip().lower()
	return normalized in {"1", "true", "yes", "on"}


def _to_float(value: str | None, default: float) -> float:
	if value is None:
		return default
	try:
		return float(value)
	except ValueError:
		return default


def _to_int(value: str | None, default: int) -> int:
	if value is None:
		return default
	try:
		return int(value)
	except ValueError:
		return default


@dataclass(slots=True)
class Settings:
	input_dir: Path
	library_dir: Path
	failed_dir: Path
	work_dir: Path
	log_level: str
	enable_llm: bool
	enable_picard: bool
	llm_provider: str
	ollama_base_url: str
	ollama_model: str
	llm_timeout_seconds: int
	llm_min_confidence: float
	enable_audiobookshelf_scan: bool
	audiobookshelf_url: str
	audiobookshelf_token: str
	scan_extensions: tuple[str, ...]

	@classmethod
	def from_env(cls) -> "Settings":
		input_dir = Path(os.getenv("INPUT_DIR", "/incoming")).expanduser().resolve()
		library_dir = Path(os.getenv("LIBRARY_DIR", "/library")).expanduser().resolve()
		failed_dir = Path(os.getenv("FAILED_DIR", "/failed")).expanduser().resolve()
		work_dir = Path(os.getenv("WORK_DIR", "/work")).expanduser().resolve()

		settings = cls(
			input_dir=input_dir,
			library_dir=library_dir,
			failed_dir=failed_dir,
			work_dir=work_dir,
			log_level=os.getenv("LOG_LEVEL", "INFO"),
			enable_llm=_to_bool(os.getenv("ENABLE_LLM"), default=False),
			# Picard is a GUI app with no reliable headless CLI mode; off by default.
			enable_picard=_to_bool(os.getenv("ENABLE_PICARD"), default=False),
			llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
			ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
			ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
			llm_timeout_seconds=_to_int(os.getenv("LLM_TIMEOUT_SECONDS"), default=45),
			llm_min_confidence=_to_float(os.getenv("LLM_MIN_CONFIDENCE"), default=0.8),
			enable_audiobookshelf_scan=_to_bool(
				os.getenv("ENABLE_AUDIOBOOKSHELF_SCAN"), default=False
			),
			audiobookshelf_url=os.getenv("AUDIOBOOKSHELF_URL", "http://audiobookshelf:80"),
			audiobookshelf_token=os.getenv("AUDIOBOOKSHELF_TOKEN", ""),
			scan_extensions=(".m4b", ".m4a", ".mp3"),
		)
		settings.validate()
		return settings

	def validate(self) -> None:
		if self.llm_min_confidence < 0 or self.llm_min_confidence > 1:
			raise ValueError("LLM_MIN_CONFIDENCE must be between 0 and 1")
		if self.llm_timeout_seconds <= 0:
			raise ValueError("LLM_TIMEOUT_SECONDS must be positive")

	def ensure_directories(self) -> None:
		for folder in (self.input_dir, self.library_dir, self.failed_dir, self.work_dir):
			folder.mkdir(parents=True, exist_ok=True)


def configure_logging(level: str = "INFO") -> None:
	normalized = level.upper()
	logging.basicConfig(
		level=getattr(logging, normalized, logging.INFO),
		format="%(asctime)s %(levelname)s %(name)s %(message)s",
	)
