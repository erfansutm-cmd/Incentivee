"""SQLAlchemy ORM models."""

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class City(Base):
    """A city and its parameters."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    parm1: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    parm2: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    parm3: Mapped[float] = mapped_column(Float, nullable=False, default=0)
