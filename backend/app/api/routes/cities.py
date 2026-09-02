"""Cities CRUD API — driven entirely by the real `cities` table.

There is NO mock data and the backend NEVER creates or alters tables.
The schema (database) and table names come from the environment
(DB_NAME / DB_TABLE). The table structure is reflected from the
database on first use; every row is returned with all of its columns
and their real values.

Endpoints
---------
GET    /api/cities          list all cities (all real columns/values)
GET    /api/cities/status   table status (exists / accessible, columns)
GET    /api/cities/schema   describe the real table in the DB
POST   /api/cities          create a city
GET    /api/cities/{id}     get one city
PUT    /api/cities/{id}     update a city (full or partial)
DELETE /api/cities/{id}     delete a city

Error statuses are meaningful:
- 404  table or city does not exist
- 403  no access to the table / database
- 400  column in the payload does not exist in the table
- 409  duplicate name / constraint violation
- 422  missing or invalid input values
- 503  database unreachable
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import MetaData, Table, delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError, NoSuchTableError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import db_failure_detail
from app.database import engine, get_db
from app.schemas import CityCreate, CityUpdate

router = APIRouter(prefix="/cities", tags=["cities"])

# The table structure is reflected from the database and cached briefly;
# the cache re-reads the real schema after TTL so columns added/removed
# in the DB are picked up without a restart.
_META = MetaData()
_REFLECT_TTL_SECONDS = 30.0
_reflected_at = 0.0


def _cities_table() -> Table:
    """The real table (settings.db_table), reflected from the database.

    Raises HTTPException with a proper status if the table is missing
    (404), not accessible (403), or the database is unreachable (503).
    """
    global _reflected_at
    now = time.monotonic()
    if _META.tables and now - _reflected_at > _REFLECT_TTL_SECONDS:
        _META.clear()  # force a fresh reflection of the current DB schema
    try:
        if settings.db_table not in _META.tables:
            _reflected_at = now
            return Table(settings.db_table, _META, autoload_with=engine)
        return _META.tables[settings.db_table]
    except NoSuchTableError:
        raise HTTPException(
            status_code=404,
            detail=(
                f'Table "{settings.db_table}" does not exist in database '
                f'"{settings.db_name}".'
            ),
        )
    except SQLAlchemyError as exc:
        status_code, detail = db_failure_detail(exc, settings.db_table, settings.db_name)
        raise HTTPException(status_code=status_code, detail=detail)


def _cities_table_fresh() -> Table:
    """Reflect the configured table RIGHT NOW, bypassing the cache.

    Used by the status/schema endpoints so they always report the live
    state of the database (same proper errors as `_cities_table`).
    """
    global _reflected_at
    _META.clear()
    _reflected_at = time.monotonic()
    try:
        return Table(settings.db_table, _META, autoload_with=engine)
    except NoSuchTableError:
        raise HTTPException(
            status_code=404,
            detail=(
                f'Table "{settings.db_table}" does not exist in database '
                f'"{settings.db_name}".'
            ),
        )
    except SQLAlchemyError as exc:
        status_code, detail = db_failure_detail(exc, settings.db_table, settings.db_name)
        raise HTTPException(status_code=status_code, detail=detail)


def _check_table_access() -> None:
    """Verify live access with `SELECT * FROM <table> LIMIT 0`.

    Confirms the table exists and the database user can actually read it
    (MySQL raises 1146 when it's missing, 1142 when access is denied).
    """
    try:
        with engine.connect() as conn:
            quoted = conn.dialect.identifier_preparer.quote(settings.db_table)
            conn.execute(text(f"SELECT * FROM {quoted} LIMIT 0")).close()
    except SQLAlchemyError as exc:
        status_code, detail = db_failure_detail(exc, settings.db_table, settings.db_name)
        raise HTTPException(status_code=status_code, detail=detail)


def _primary_key(table: Table) -> str | None:
    pk_cols = list(table.primary_key.columns)
    return pk_cols[0].name if pk_cols else None


def _require_known_columns(table: Table, data: dict) -> None:
    """Reject fields that don't exist in the real table (typo guard)."""
    unknown = sorted(key for key in data if key not in table.columns)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Column(s) {', '.join(unknown)} do not exist in the "
                f'"{settings.db_table}" table. Existing columns: '
                f"{', '.join(c.name for c in table.columns)}."
            ),
        )


def _ensure_unique_name(db: Session, table: Table, name: str, exclude_id=None) -> None:
    """Raise 409 if another city already uses this name."""
    if "name" not in table.columns:
        return
    pk = _primary_key(table)
    stmt = select(table).where(table.c.name == name)
    if exclude_id is not None and pk is not None:
        stmt = stmt.where(table.c[pk] != exclude_id)
    if db.execute(stmt.limit(1)).first() is not None:
        raise HTTPException(status_code=409, detail=f'City "{name}" already exists')


def _get_city_or_404(city_id: int, db: Session, table: Table) -> dict:
    pk = _primary_key(table)
    if pk is None:
        raise HTTPException(
            status_code=404,
            detail=f'The "{settings.db_table}" table has no primary key',
        )
    row = db.execute(select(table).where(table.c[pk] == city_id)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")
    return dict(row)


def _column_default(col) -> str | None:
    """Human-readable default value of a column (or None if there is none)."""
    default = getattr(col, "default", None)
    if default is None or getattr(default, "arg", None) is None:
        return None
    return str(default.arg)


def _table_info(table: Table) -> dict:
    return {
        "database": settings.db_name,
        "table": settings.db_table,
        "status": "ok",
        "primary_key": _primary_key(table),
        "column_names": [col.name for col in table.columns],
    }


@router.get("/status")
def city_table_status() -> dict:
    """Live status of the configured table: exists and is accessible.

    Always checks the database right now (never cached).
    404 if the table does not exist, 403 if the database user has no
    access to it, 503 if the database is unreachable.
    """
    table = _cities_table_fresh()
    _check_table_access()
    return _table_info(table)


@router.get("/schema")
def city_table_schema() -> dict:
    """Describe the actual table as it exists in the database right now.

    The UI uses this to render the table dynamically — the database is
    the single source of truth for which columns exist. The structure
    comes from SQLAlchemy reflection (no database-specific SQL).
    """
    table = _cities_table_fresh()
    _check_table_access()
    info = _table_info(table)
    info["columns"] = [
        {
            "name": col.name,
            "type": str(col.type),
            "nullable": bool(col.nullable),
            "is_pk": bool(col.primary_key),
            "default": _column_default(col),
        }
        for col in table.columns
    ]
    return info


@router.get("")
def list_cities(db: Session = Depends(get_db)) -> list[dict]:
    """All rows with all of their real columns, ordered by primary key."""
    table = _cities_table()
    pk = _primary_key(table)
    stmt = select(table).order_by(table.c[pk]) if pk else select(table)
    return [dict(row) for row in db.execute(stmt).mappings().all()]


@router.get("/{city_id}")
def get_city(city_id: int, db: Session = Depends(get_db)) -> dict:
    return _get_city_or_404(city_id, db, _cities_table())


@router.post("", status_code=201)
def create_city(payload: CityCreate, db: Session = Depends(get_db)) -> dict:
    """Insert a new city using only columns that really exist."""
    table = _cities_table()
    data = payload.model_dump(exclude_none=True)
    _require_known_columns(table, data)

    if "name" in table.columns:
        name = data.get("name")
        if not name or not str(name).strip():
            raise HTTPException(status_code=422, detail="name is required")
        data["name"] = str(name).strip()
        _ensure_unique_name(db, table, data["name"])

    try:
        result = db.execute(insert(table).values(**data))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Could not create city: {exc.orig or exc}")

    pk = _primary_key(table)
    new_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
    if pk is not None and new_id is not None:
        row = db.execute(select(table).where(table.c[pk] == new_id)).mappings().first()
        if row is not None:
            return dict(row)
    return data


@router.put("/{city_id}")
def update_city(city_id: int, payload: CityUpdate, db: Session = Depends(get_db)) -> dict:
    """Partial update using only columns that really exist."""
    table = _cities_table()
    existing = _get_city_or_404(city_id, db, table)

    data = payload.model_dump(exclude_unset=True)
    _require_known_columns(table, data)

    if "name" in data and data["name"] is not None:
        data["name"] = str(data["name"]).strip()
        if not data["name"]:
            raise HTTPException(status_code=422, detail="name cannot be empty")
        _ensure_unique_name(db, table, data["name"], exclude_id=city_id)

    if data:
        pk = _primary_key(table)
        try:
            db.execute(update(table).where(table.c[pk] == city_id).values(**data))
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=f"Could not update city: {exc.orig or exc}")
        return _get_city_or_404(city_id, db, table)
    return existing


@router.delete("/{city_id}", status_code=204)
def delete_city(city_id: int, db: Session = Depends(get_db)) -> None:
    table = _cities_table()
    _get_city_or_404(city_id, db, table)
    pk = _primary_key(table)
    try:
        db.execute(delete(table).where(table.c[pk] == city_id))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Could not delete city: {exc.orig or exc}")
