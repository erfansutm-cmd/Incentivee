"""Pydantic request/response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CityBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    parm1: float = 0
    parm2: float = 0
    parm3: float = 0


class CityCreate(CityBase):
    """Body for POST /api/cities."""


class CityUpdate(BaseModel):
    """Body for PUT /api/cities/{id} — every field is optional."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    parm1: float | None = None
    parm2: float | None = None
    parm3: float | None = None


class CityRead(CityBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
