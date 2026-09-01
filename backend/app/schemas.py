"""Pydantic request/response models.

NOTE: parm1/parm2/parm3 are placeholders for the real GateKeeper
parameters — rename/retype them here once the business parameters
are known; everything else (routes, UI) follows the schema.
"""

from pydantic import BaseModel, Field


class CityParams(BaseModel):
    """Editable parameters of a city."""

    parm1: float = 0
    parm2: float = 0
    parm3: float = 0


class CityCreate(BaseModel):
    """Body for POST /cities — just a name, params get defaults."""

    name: str = Field(min_length=1, max_length=80)


class CityUpdate(BaseModel):
    """Body for PUT /cities/{id} — partial update.

    Any combination of fields may be sent: used both for saving
    parameters (parm1/2/3) and renaming (name).
    """

    name: str | None = Field(default=None, min_length=1, max_length=80)
    parm1: float | None = None
    parm2: float | None = None
    parm3: float | None = None


class City(CityParams):
    """A city as returned by the API."""

    id: str
    name: str
