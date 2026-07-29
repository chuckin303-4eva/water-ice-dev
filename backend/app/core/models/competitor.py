import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Competitor(Base):
    """A rival ice/water vending machine observed at a specific address --
    site-level, not a company roster, per ADR-0003 (so map pins and future
    competition-density scoring have real coordinates to work with).

    Field set widened beyond ADR-0003's original design (ADR-0008):
    `is_inside`, `machine_size`, `ice_price`/`water_price`/`price_notes`
    added for the map's click-to-view competitor panel; `brand`,
    `website`, `phone`, `contact_name`, `contact_email`, `follow_up_at`
    added for a compact manual-entry form (ADR-0008 addendum) -- `name`
    is the specific site's own name/label, `brand` is the parent
    franchise (e.g. "Twice the Ice", "Kooler Ice", "Watermill Express"),
    kept as free text rather than a link to the shared `brands` table
    since this needs no more structure than an autocomplete suggestion
    list. There is no automated way to populate this table -- confirmed
    no free, scrapeable source exists for specific ice/water vending
    machine addresses (see ADR-0008) -- so every row here is either
    entered by hand from an operator's own market knowledge, or (later)
    a paid-API/Market-Refresh write, same honesty pattern as the
    deferred utility lookups in ADR-0006.
    """

    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True, nullable=False)
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), index=True, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)

    latitude: Mapped[float] = mapped_column(Numeric(9, 6), index=True, nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # specific site/location name
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)  # parent franchise
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    serves_ice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    serves_water: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    machine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    machine_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_inside: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    ice_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    water_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    estimated_market_share: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    last_observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
