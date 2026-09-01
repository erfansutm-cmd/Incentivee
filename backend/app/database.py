"""Database engine and session setup (MySQL via SQLAlchemy).

The engine is created lazily and connects only when first used. All
city data is read from and written to this database — there is no
mock or in-memory data anywhere: the `cities` table itself is the
single source of truth.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


def get_db():
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
