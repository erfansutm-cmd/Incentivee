"""FastAPI application entry point.

The backend NEVER creates or alters database tables — the configured
schema/table (DB_NAME / DB_TABLE) must already exist. If it doesn't (or
the database user has no access), every endpoint reports a proper error.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    NoSuchTableError,
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
)

from app.api.routes.cities import router as cities_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.errors import db_failure_detail


def _db_error_response(exc: SQLAlchemyError) -> JSONResponse:
    status_code, detail = db_failure_detail(exc, settings.db_table, settings.db_name)
    return JSONResponse(status_code=status_code, content={"detail": detail})


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

    @app.exception_handler(NoSuchTableError)
    async def missing_table_handler(request: Request, exc: NoSuchTableError) -> JSONResponse:
        """The configured table does not exist in the database."""
        return JSONResponse(
            status_code=404,
            content={
                "detail": (
                    f'Table "{settings.db_table}" does not exist in database '
                    f'"{settings.db_name}".'
                )
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Constraint violation (e.g. duplicate unique value)."""
        origin = getattr(exc, "orig", None) or exc
        return JSONResponse(status_code=409, content={"detail": f"Constraint violation: {origin}"})

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
        """DB connection/operational failure (server down, timeout, no access…)."""
        return _db_error_response(exc)

    @app.exception_handler(ProgrammingError)
    async def programming_error_handler(request: Request, exc: ProgrammingError) -> JSONResponse:
        """Missing table / access denied as reported by some drivers."""
        return _db_error_response(exc)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Fallback for any other database error."""
        return _db_error_response(exc)

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(cities_router, prefix=settings.api_prefix)

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "docs": f"{settings.api_prefix}/docs",
            "database": settings.db_name,
            "table": settings.db_table,
        }

    return app


app = create_app()
