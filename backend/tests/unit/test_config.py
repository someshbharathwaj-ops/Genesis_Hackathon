"""Unit tests verifying application settings and configuration constraints."""

import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_default_settings() -> None:
    settings = Settings()
    assert settings.PROJECT_NAME == "Recall"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.LLM_TIMEOUT_SECONDS == 45.0
    assert settings.PRIMARY_MODEL == "phi3:mini"
    assert isinstance(settings.ALLOWED_ORIGINS, list)


@pytest.mark.unit
def test_cors_origin_parsing_from_string() -> None:
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, https://recall.edu")
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "https://recall.edu"]


@pytest.mark.unit
def test_production_secret_key_validation() -> None:
    # Insecure or default SECRET_KEY should raise ValueError in production
    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev_secret_key_change_in_production_min_32_chars_12345",
        )

    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short_key_123",
        )

    # Valid strong key in production should succeed
    strong_prod = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_strong_production_signing_key_at_least_32_chars_long",
    )
    assert strong_prod.ENVIRONMENT == "production"
