import os

from agent.config import Settings


def test_settings_from_env_defaults(monkeypatch) -> None:
    for key in [
        "INPUT_DIR",
        "LIBRARY_DIR",
        "FAILED_DIR",
        "WORK_DIR",
        "ENABLE_LLM",
        "ENABLE_AUDIOBOOKSHELF_SCAN",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert str(settings.input_dir).endswith("incoming")
    assert settings.enable_llm is False
    assert settings.enable_audiobookshelf_scan is False


def test_settings_confidence_validation(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MIN_CONFIDENCE", "2.0")

    try:
        Settings.from_env()
        raised = False
    except ValueError:
        raised = True

    assert raised
