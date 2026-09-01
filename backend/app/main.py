"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.gatekeeper import router as gatekeeper_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.db.models import CityModel
from app.db.session import Base, SessionLocal, engine

SEED_CITIES = [
    {"id": "tehran", "name": "Tehran", "parm1": 10.0, "parm2": 25.0, "parm3": 5.0},
    {"id": "milan", "name": "Milan", "parm1": 12.0, "parm2": 30.0, "parm3": 8.0},
    {"id": "istanbul", "name": "Istanbul", "parm1": 9.0, "parm2": 22.0, "parm3": 6.0},
]


def _init_db() -> None:
    """Create tables if missing and seed initial cities once."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(CityModel).count() == 0:
            db.add_all(CityModel(**c) for c in SEED_CITIES)
            db.commit()


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

    app.include_router(gatekeeper_router, prefix=settings.api_prefix)
    app.include_router(health_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        _init_db()

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "docs": f"{settings.api_prefix}/docs",
        }

    return app


app = create_app()
