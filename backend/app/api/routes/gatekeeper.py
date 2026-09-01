"""GateKeeper endpoints — city parameters.

Backed by a MySQL table (see app/db/models.py). Table creation and
seeding of the initial three cities happens once at startup in
app/main.py.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.models import CityModel
from app.db.session import get_db
from app.schemas import City, CityCreate, CityUpdate

router = APIRouter(prefix="/cities", tags=["gatekeeper"])


# ── Helpers ───────────────────────────────────────────────────
def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "city"


def _find(db: Session, city_id: str) -> CityModel:
    city = db.get(CityModel, city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City '{city_id}' not found")
    return city


# ── Routes ────────────────────────────────────────────────────
@router.get("", response_model=dict)
def list_cities(db: Session = Depends(get_db)) -> dict:
    """GET /api/cities — all cities with their parameters."""
    cities = db.query(CityModel).order_by(CityModel.name).all()
    return {"cities": [c.as_dict() for c in cities]}


@router.post("", response_model=City, status_code=201)
def create_city(payload: CityCreate, db: Session = Depends(get_db)) -> dict:
    """POST /api/cities — add a new city with default parameters."""
    city_id = _slugify(payload.name)

    # Ensure a unique id if the name collides with an existing city
    if db.get(CityModel, city_id) is not None:
        base = city_id
        i = 2
        while db.get(CityModel, f"{base}-{i}") is not None:
            i += 1
        city_id = f"{base}-{i}"

    city = CityModel(id=city_id, name=payload.name.strip(), parm1=0.0, parm2=0.0, parm3=0.0)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city.as_dict()


@router.put("/{city_id}", response_model=City)
def update_city(city_id: str, payload: CityUpdate, db: Session = Depends(get_db)) -> dict:
    """PUT /api/cities/{id} — partial update (rename and/or parameters).

    Only fields present in the body are changed. The id is kept
    stable on rename so existing references/bookmarks don't break.
    """
    city = _find(db, city_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
    for field, value in data.items():
        setattr(city, field, value)
    db.commit()
    db.refresh(city)
    return city.as_dict()


@router.delete("/{city_id}", status_code=204)
def delete_city(city_id: str, db: Session = Depends(get_db)) -> Response:
    """DELETE /api/cities/{id} — remove a city."""
    city = _find(db, city_id)
    db.delete(city)
    db.commit()
    return Response(status_code=204)
