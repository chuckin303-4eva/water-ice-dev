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

    # JWT signing. secret_key has no default -- generate one with
    # `python -c "import secrets; print(secrets.token_urlsafe(32))"` and put
    # it in .env. Never commit a real value (see docs/SECURITY.md).
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Comma-separated list of allowed browser origins for the frontend.
    # Defaults to the Vite dev server; override in .env for other envs.
    cors_origins: str = "http://localhost:5173"

    # Photo uploads (ADR-0018): local disk for now, same MVP decision
    # already made and proven in the sibling LPC project -- revisit with
    # a new ADR before this needs to survive an ephemeral filesystem
    # (e.g. once the backend itself is containerized/deployed).
    upload_dir: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
