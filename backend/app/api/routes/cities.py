"""Cities CRUD API.

Endpoints
---------
GET    /api/cities          list all cities
GET    /api/cities/schema   describe the real `cities` table in the DB
POST   /api/cities          create a city
GET    /api/cities/{id}     get one city
PUT    /api/cities/{id}     update a city (full or partial)
DELETE /api/cities/{id}     delete a city
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import City
from app.schemas import CityCreate, CityRead, CityUpdate

router = APIRouter(prefix="/cities", tags=["cities"])


def _get_city_or_404(city_id: int, db: Session) -> City:
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found")
    return city


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    """Raise 409 if another city already uses this name."""
    stmt = select(City).where(City.name == name)
    if exclude_id is not None:
        stmt = stmt.where(City.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"City \"{name}\" already exists")


@router.get("", response_model=list[CityRead])
def list_cities(db: Session = Depends(get_db)) -> list[City]:
    return list(db.execute(select(City).order_by(City.id)).scalars().all())


@router.get("/schema")
def city_table_schema(db: Session = Depends(get_db)) -> dict:
    """Describe the actual `cities` table as it exists in the database.

    Handy when the table already exists with different columns — the UI
    shows this so you can see what the DB really contains.
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
                "key": r[3] or None,
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
                "key": "PK" if r[5] else None,
                "default": r[4],
            }
            for r in rows
        ]
    return {"table": "cities", "columns": columns}


@router.get("/{city_id}", response_model=CityRead)
def get_city(city_id: int, db: Session = Depends(get_db)) -> City:
    return _get_city_or_404(city_id, db)


@router.post("", response_model=CityRead, status_code=201)
def create_city(payload: CityCreate, db: Session = Depends(get_db)) -> City:
    _ensure_unique_name(db, payload.name)
    city = City(name=payload.name, parm1=payload.parm1, parm2=payload.parm2, parm3=payload.parm3)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


@router.put("/{city_id}", response_model=CityRead)
def update_city(city_id: int, payload: CityUpdate, db: Session = Depends(get_db)) -> City:
    city = _get_city_or_404(city_id, db)
    updates = payload.model_dump(exclude_unset=True)

    new_name = updates.get("name")
    if new_name is not None:
        _ensure_unique_name(db, new_name, exclude_id=city.id)
        city.name = new_name
    for field in ("parm1", "parm2", "parm3"):
        if field in updates:
            setattr(city, field, updates[field])

    db.commit()
    db.refresh(city)
    return city


@router.delete("/{city_id}", status_code=204)
def delete_city(city_id: int, db: Session = Depends(get_db)) -> None:
    city = _get_city_or_404(city_id, db)
    db.delete(city)
    db.commit()
