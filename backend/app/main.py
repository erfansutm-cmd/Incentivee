"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.cities import router as cities_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.database import engine


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

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Return the real database error (e.g. unknown column) instead of a generic 500."""
        return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(cities_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def ensure_table() -> None:
        """Create the `cities` table if missing; never alter an existing one."""
        _ensure_cities_table()

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "docs": f"{settings.api_prefix}/docs",
        }

    return app


app = create_app()
