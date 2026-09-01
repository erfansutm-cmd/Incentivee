"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.cities import router as cities_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 — register ORM models on Base

# Columns the app expects, with DB-specific ADD COLUMN definitions
# (used only when the column is missing from an existing table).
_REQUIRED_COLUMNS_MYSQL = {
    "name": "VARCHAR(80) NULL",
    "parm1": "DOUBLE NOT NULL DEFAULT 0",
    "parm2": "DOUBLE NOT NULL DEFAULT 0",
    "parm3": "DOUBLE NOT NULL DEFAULT 0",
}
_REQUIRED_COLUMNS_SQLITE = {
    "name": "VARCHAR(80)",
    "parm1": "FLOAT NOT NULL DEFAULT 0",
    "parm2": "FLOAT NOT NULL DEFAULT 0",
    "parm3": "FLOAT NOT NULL DEFAULT 0",
}


def _sync_table_schema() -> None:
    """Make the `cities` table usable by the app without destroying data.

    - Creates the table if it doesn't exist (with the expected schema).
    - If the table already exists (e.g. created earlier with fewer or
      other columns), only ADD the missing expected columns — existing
      columns and data are left untouched, and extra columns are kept.
    """
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)

        if settings.database_url.startswith("mysql"):
            cols = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cities'"
                    )
                )
            }
            required = _REQUIRED_COLUMNS_MYSQL
        else:  # SQLite (local development)
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cities)"))}
            required = _REQUIRED_COLUMNS_SQLITE

        for column, ddl in required.items():
            if column not in cols:
                conn.execute(text(f'ALTER TABLE cities ADD COLUMN "{column}" {ddl}'))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Return the real database error (e.g. unknown column) instead of a generic 500."""
        return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(cities_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def create_tables() -> None:
        """Create or align the `cities` table (simple bootstrap; use Alembic for migrations)."""
        _sync_table_schema()

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "docs": f"{settings.api_prefix}/docs",
        }

    return app


app = create_app()
