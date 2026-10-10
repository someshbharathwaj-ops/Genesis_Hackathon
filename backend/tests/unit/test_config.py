"""Unit tests verifying application settings and configuration constraints."""

import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_default_settings() -> None:
    settings = Settings()
    assert settings.PROJECT_NAME == "Recall"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.LLM_TIMEOUT_SECONDS == 15.0
    assert settings.PRIMARY_MODEL == "qwen2.5:3b"
    assert isinstance(settings.ALLOWED_ORIGINS, list)


@pytest.mark.unit
def test_cors_origin_parsing_from_string() -> None:
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, https://recall.edu")
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "https://recall.edu"]
