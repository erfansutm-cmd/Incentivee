"""Application settings, overridable via environment variables.

Everything that might change between environments lives here so the
rest of the app only imports ``settings``.
"""

from urllib.parse import quote_plus

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

    # ── Database (MySQL) ────────────────────────────────────────
    # Provided via env vars / the root .env file.
    db_host: str = "172.21.41.75"
    db_port: int = 3306
    db_user: str = "erfan.mohamadi"
    db_password: str = ""
    db_name: str = "incentive"

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL, e.g. mysql+pymysql://user:pass@host:3306/db."""
        return (
            f"mysql+pymysql://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    # Origins allowed to call the API directly from a browser.
    # Behind nginx / the Vite proxy the front end is same-origin,
    # so CORS only matters if you open the API to another origin.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


settings = Settings()
