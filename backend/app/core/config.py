from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env.

    Looks for .env in both the backend/ directory and the repo root so it
    works whether the app is run from backend/ (local dev) or the repo
    root (docker compose, CI). Missing files are silently skipped.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    environment: str = "development"


settings = Settings()
