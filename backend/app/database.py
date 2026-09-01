"""Database engine and session setup (MySQL via SQLAlchemy).

The engine is created lazily and connects only when first used, so
the app still runs with the in-memory mock data if the database is
unreachable or not configured yet.

Usage in a route:

    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.db import get_db

    @router.get("/things")
    def list_things(db: Session = Depends(get_db)):
        return db.execute(text("SELECT 1")).scalar()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # drop stale connections (MySQL closes idle ones)
    pool_recycle=3600,
    # MySQL-only options: fail fast if the DB is unreachable.
    connect_args={"connect_timeout": 5} if settings.database_url.startswith("mysql") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def get_db():
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
