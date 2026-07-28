from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class County(Base):
    """A county is stored under one primary state; fips_code is optional
    since not every dataset supplies it. See docs/DATABASE.md.
    """

    __tablename__ = "counties"
    __table_args__ = (UniqueConstraint("state_id", "name", name="uq_counties_state_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True, nullable=False)
    fips_code: Mapped[str | None] = mapped_column(String(5), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class City(Base):
    """county_id is nullable and represents the city's primary county --
    real-world city/county boundaries occasionally overlap, deliberately
    not modeled as many-to-many (see docs/DATABASE.md).
    """

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True, nullable=False)
    county_id: Mapped[int | None] = mapped_column(
        ForeignKey("counties.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
