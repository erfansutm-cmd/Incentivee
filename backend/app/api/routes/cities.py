"""Cities CRUD API — driven entirely by the real `cities` table.

There are no hardcoded parameter columns and no mock rows anywhere.
The actual columns of the `cities` table are introspected on first use;
every row is returned with all of its columns and their real values,
and create/update only accept fields that really exist in the table.

Endpoints
---------
GET    /api/cities          list all cities (all real columns/values)
GET    /api/cities/schema   describe the real `cities` table in the DB
POST   /api/cities          create a city
GET    /api/cities/{id}     get one city
PUT    /api/cities/{id}     update a city (full or partial)
DELETE /api/cities/{id}     delete a city
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import MetaData, Table, delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError, NoSuchTableError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
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
    """The real `cities` table, reflected straight from the database."""
    global _reflected_at
    now = time.monotonic()
    if _META.tables and now - _reflected_at > _REFLECT_TTL_SECONDS:
        _META.clear()  # force a fresh reflection of the current DB schema
    try:
        if "cities" not in _META.tables:
            _reflected_at = now
            return Table("cities", _META, autoload_with=engine)
        return _META.tables["cities"]
    except NoSuchTableError:
        raise HTTPException(
            status_code=500,
            detail=(
                'The "cities" table does not exist in the database. It is normally '
                "created automatically on startup — check the database connection "
                "and restart the backend."
            ),
        )
    except SQLAlchemyError as exc:
        origin = getattr(exc, "orig", None) or exc
        raise HTTPException(
            status_code=503,
            detail=f'Could not read the "cities" table from the database: {origin}',
        )


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
                f'"cities" table. Existing columns: '
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
        raise HTTPException(status_code=404, detail='The "cities" table has no primary key')
    row = db.execute(select(table).where(table.c[pk] == city_id)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")
    return dict(row)


@router.get("")
def list_cities(db: Session = Depends(get_db)) -> list[dict]:
    """All rows with all of their real columns, ordered by primary key."""
    table = _cities_table()
    pk = _primary_key(table)
    stmt = select(table).order_by(table.c[pk]) if pk else select(table)
    return [dict(row) for row in db.execute(stmt).mappings().all()]


@router.get("/schema")
def city_table_schema(db: Session = Depends(get_db)) -> dict:
    """Describe the actual `cities` table as it exists in the database.

    The UI uses this to render the table dynamically — the database is
    the single source of truth for which columns exist.
    """
    if settings.database_url.startswith("mysql"):
        sql = text(
            "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cities' "
            "ORDER BY ORDINAL_POSITION"
        )
        rows = db.execute(sql).all()
        columns = [
            {
                "name": r[0],
                "type": r[1],
                "nullable": r[2] == "YES",
                "is_pk": r[3] == "PRI",
                "default": r[4],
            }
            for r in rows
        ]
    else:  # SQLite (local development)
        rows = db.execute(text("PRAGMA table_info(cities)")).all()
        columns = [
            {
                "name": r[1],
                "type": r[2],
                "nullable": not r[3],
                "is_pk": bool(r[5]),
                "default": r[4],
            }
            for r in rows
        ]
    primary_key = next((c["name"] for c in columns if c["is_pk"]), None)
    if not columns:
        raise HTTPException(
            status_code=500,
            detail=(
                'The "cities" table does not exist in the database. It is normally '
                "created automatically on startup — check the database connection "
                "and restart the backend."
            ),
        )
    return {"table": "cities", "primary_key": primary_key, "columns": columns}


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
