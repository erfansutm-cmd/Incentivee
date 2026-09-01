"""Health-check / smoke-test endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/db")
def db_check(db: Session = Depends(get_db)) -> dict:
    """Verify the MySQL connection and show the current database/user."""
    try:
        row = db.execute(text("SELECT DATABASE(), CURRENT_USER(), VERSION()")).one()
    except Exception as exc:  # noqa: BLE001 — surface any connection error
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}") from exc
    return {
        "status": "ok",
        "database": row[0],
        "user": row[1],
        "server_version": row[2],
    }
