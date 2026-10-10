"""Application configuration loaded from environment variables."""


from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    PROJECT_NAME: str = Field(default="Recall", description="Project Name")
    VERSION: str = Field(default="0.1.0", description="API Version")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/recall_db",
        description="Async PostgreSQL database connection URL",
    )
    TEST_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///:memory:",
        description="Test database URL",
    )

    # Security
    SECRET_KEY: str = Field(
        default="dev_secret_key_change_in_production_min_32_chars_12345",
        description="Cryptographic secret key for token signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Token validity in minutes")
    ALLOWED_ORIGINS: str | list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS allowed origins",
    )

    # LLM / Primary Model Adapter
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama service base endpoint",
    )
    PRIMARY_MODEL: str = Field(default="qwen2.5:3b", description="Primary bounded language model")
    EMBEDDING_MODEL: str = Field(default="nomic-embed-text", description="Vector embedding model")
    LLM_TIMEOUT_SECONDS: float = Field(default=15.0, description="Strict LLM inference timeout")
    USE_MOCK_LLM: bool = Field(
        default=True,
        description="Whether to use mock LLM provider for deterministic tests",
    )

    # Ingestion & Documents
    UPLOAD_DIR: str = Field(default="./uploads", description="Directory for document uploads")
    MAX_FILE_SIZE_MB: int = Field(default=25, description="Maximum upload size limit")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
