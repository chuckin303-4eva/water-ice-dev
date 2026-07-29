import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Location(Base):
    """The central table. Field set and rationale are fully documented in
    docs/DATABASE.md -- see that file before adding or changing a column.

    `serves_ice`/`serves_water`/`machine_type` live here rather than in a
    per-industry module table per ADR-0003 (ice/water is the whole product
    today; a deliberate, deferred trade against ADR-0002's stricter
    industry-independent-core principle).

    `status`/`machine_type` are plain strings for now rather than a
    SQLAlchemy Enum -- enum values will firm up once the Location
    management CRUD/validation layer (Phase 1, item 3) is built; changing
    a Postgres enum type later is more awkward than changing a string
    column, so this is deliberately deferred, not an oversight.

    `competition_score`/`opportunity_score`/`confidence_score` are
    computed/derived values, snapshotted at last calculation -- nothing
    in this model computes them; that logic arrives with Basic scoring
    (Phase 1, item 5) and the Market Refresh Engine (ADR-0004).
    """

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True, nullable=False)
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), index=True, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True, nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)

    # Plain lat/lng per ADR-0002 (no PostGIS) -- radius/nearest queries use
    # bounding-box pre-filtering plus application-level distance calculation.
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), index=True, nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), index=True, nullable=False)

    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("brands.id"), index=True, nullable=True
    )

    serves_ice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    serves_water: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    machine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    host_business_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("host_businesses.id"), index=True, nullable=True
    )

    is_inside: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    visibility_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_score: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_income: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    growth_rate: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    competition_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    opportunity_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="prospect", index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Prospecting fields (docs/DECISIONS.md ADR-0006) ---
    # All manually entered. Property ownership has no free nationwide
    # lookup source (confirmed -- only paid parcel-data APIs exist); sewer
    # availability has no equivalent public dataset either. Power/water
    # utility auto-lookup is designed but deferred (ADR-0006), not built
    # here -- these columns hold whatever's found, by hand or later by a
    # provider, with the same meaning either way.
    property_owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    property_owner_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    property_management_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    property_management_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    property_management_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    primary_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    primary_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expected_unit_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    power_connection_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    power_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    power_voltage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    water_connection_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    water_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sewer_connection_availability: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sewer_connection_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pricing_estimate_monthly: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    pricing_estimate_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
