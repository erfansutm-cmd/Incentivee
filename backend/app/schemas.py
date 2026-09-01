"""Pydantic request schemas.

There are no hardcoded parameter columns (no `parm1/parm2/parm3`).
Responses are plain dicts built from the real columns of the `cities`
table, so whatever columns exist in the database are returned as-is.

Create/update bodies accept extra fields; the routes validate them
against the actual table columns (unknown columns → 400).
"""

from pydantic import BaseModel, ConfigDict, Field


class CityCreate(BaseModel):
    """Body for POST /api/cities — `name` plus any real columns."""

    model_config = ConfigDict(extra="allow")

    name: str | None = Field(default=None, min_length=1, max_length=80)


class CityUpdate(BaseModel):
    """Body for PUT /api/cities/{id} — every field is optional."""

    model_config = ConfigDict(extra="allow")

    name: str | None = Field(default=None, min_length=1, max_length=80)
