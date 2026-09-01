"""Application settings, overridable via environment variables.

Everything that might change between environments lives here so the
rest of the app only imports ``settings``.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Project identity ────────────────────────────────────────
    app_name: str = "Incentive"

    # development | production
    environment: str = "development"

    # ── Main URL / routing ──────────────────────────────────────
    # Base path every API route is mounted under. Change it here
    # (or via the API_PREFIX env var) to move the whole API, e.g.
    # API_PREFIX="/api/v1".
    api_prefix: str = "/api"

    # Origins allowed to call the API directly from a browser.
    # Behind nginx / the Vite proxy the front end is same-origin,
    # so CORS only matters if you open the API to another origin.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # ── Database (MySQL) ─────────────────────────────────────────
    # All values are overridable via env vars / .env. Never commit
    # real credentials — .env is already git-ignored.
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "incentive"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
