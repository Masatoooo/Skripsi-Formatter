from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    app_name: str = "Skripsi Formatter API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    storage_dir: Path = base_dir / "storage"
    profiles_dir: Path = base_dir.parent.parent / "profiles"

    # Security & File Limits
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    max_uncompressed_bytes: int = 200 * 1024 * 1024  # 200 MB (Zip-bomb prevention)
    max_zip_entries: int = 500
    temp_file_ttl_seconds: int = 3600  # 1 hour retention
    rate_limit_per_minute: int = 120  # Requests per minute per client IP

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_prefix="SKRIPSI_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
