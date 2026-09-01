"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import (
    IntegrityError,
    NoSuchTableError,
    OperationalError,
    SQLAlchemyError,
)

from app.api.routes.cities import router as cities_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.database import engine

logger = logging.getLogger(__name__)


def _ensure_cities_table() -> None:
    """Create the `cities` table only if it doesn't exist yet.

    The database schema is the single source of truth:

    - an existing table is NEVER altered — the API serves whatever
      columns and values it really contains;
    - a brand-new database gets a minimal table (just `id` + `name`),
      with no hardcoded parameter columns.
    """
    with engine.begin() as conn:
        inspector = inspect(conn)
        if inspector.has_table("cities"):
            return
        if settings.database_url.startswith("mysql"):
            ddl = (
                "CREATE TABLE cities ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "name VARCHAR(80) NOT NULL UNIQUE"
                ")"
            )
        else:  # SQLite (local development)
            ddl = (
                "CREATE TABLE cities ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "name VARCHAR(80) NOT NULL UNIQUE"
                ")"
            )
        conn.execute(text(ddl))


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

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
        """DB connection/operational failure (server down, timeout, auth…)."""
        message = str(exc.orig or exc)
        lowered = message.lower()
        if "no such table" in lowered or ("cities" in lowered and "doesn't exist" in lowered):
            return JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        'The "cities" table does not exist in the database. It is normally '
                        "created automatically on startup — check the database connection "
                        "and restart the backend."
                    )
                },
            )
        return JSONResponse(
            status_code=503,
            content={"detail": f"Database unreachable or operation failed: {message}"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Constraint violation (e.g. duplicate unique value)."""
        origin = getattr(exc, "orig", None) or exc
        return JSONResponse(status_code=409, content={"detail": f"Constraint violation: {origin}"})

    @app.exception_handler(NoSuchTableError)
    async def missing_table_handler(request: Request, exc: NoSuchTableError) -> JSONResponse:
        """The `cities` table is missing (startup could not create it)."""
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    'The "cities" table does not exist in the database. It is normally '
                    "created automatically on startup — check the database connection "
                    "and restart the backend."
                )
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Fallback for any other database error (e.g. unknown column)."""
        return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(cities_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def ensure_table() -> None:
        """Create the `cities` table if missing; never alter an existing one.

        A failing database must not crash the server: the app still starts
        and every endpoint answers with a proper 503 error instead.
        """
        try:
            _ensure_cities_table()
        except SQLAlchemyError as exc:
            logger.warning("Could not ensure the 'cities' table at startup: %s", exc)

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "docs": f"{settings.api_prefix}/docs",
        }

    return app


app = create_app()
