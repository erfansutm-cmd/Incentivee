"""ORM models."""

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CityModel(Base):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    parm1: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    parm2: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    parm3: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "parm1": self.parm1,
            "parm2": self.parm2,
            "parm3": self.parm3,
        }
