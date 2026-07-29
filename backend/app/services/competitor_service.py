"""Competitor create/read/update/delete, plus geography resolution from
geocoding results -- same pattern as location_service.py.

Competitors are shared, platform-wide market intelligence per ADR-0002,
same as locations -- no organization scoping. Unlike locations, writes
here don't go through update_log: ADR-0003's "never overwrite historical
information" guarantee is about an operator's own prospecting history,
not observations of rival machines, and competitor rows are expected to
be corrected/replaced freely as better information comes in.
"""

import uuid

from sqlalchemy.orm import Session

from app.api.schemas.competitor import CompetitorCreateRequest, CompetitorResponse, CompetitorUpdateRequest
from app.core.models.competitor import Competitor
from app.core.models.geography import City, County, State
from app.services import geocoding_service
from app.services.geography_service import resolve_geography


class CompetitorNotFoundError(Exception):
    pass


def create_competitor(db: Session, data: CompetitorCreateRequest) -> Competitor:
    if data.address and data.latitude is not None and data.longitude is not None:
        geocode = geocoding_service.reverse_geocode(data.latitude, data.longitude)
        address, latitude, longitude = data.address, data.latitude, data.longitude
    elif data.address:
        geocode = geocoding_service.geocode_address(data.address)
        address, latitude, longitude = data.address, geocode.latitude, geocode.longitude
    else:
        geocode = geocoding_service.reverse_geocode(data.latitude, data.longitude)
        address, latitude, longitude = geocode.address, data.latitude, data.longitude

    state, county, city = resolve_geography(db, geocode)

    competitor = Competitor(
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        address=address,
        latitude=latitude,
        longitude=longitude,
        name=data.name,
        brand=data.brand,
        website=data.website,
        phone=data.phone,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        follow_up_at=data.follow_up_at,
        serves_ice=data.serves_ice,
        serves_water=data.serves_water,
        machine_type=data.machine_type,
        machine_size=data.machine_size,
        is_inside=data.is_inside,
        ice_price=data.ice_price,
        water_price=data.water_price,
        price_notes=data.price_notes,
        last_observed_date=data.last_observed_date,
        source=data.source,
        notes=data.notes,
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


def get_competitor(db: Session, competitor_id: uuid.UUID) -> Competitor | None:
    return db.query(Competitor).filter(Competitor.id == competitor_id).first()


def list_competitors(db: Session) -> list[Competitor]:
    return db.query(Competitor).order_by(Competitor.created_at.desc()).all()


def assemble_response(db: Session, competitor: Competitor) -> CompetitorResponse:
    state = db.get(State, competitor.state_id)
    county = db.get(County, competitor.county_id)
    city = db.get(City, competitor.city_id)
    return CompetitorResponse(
        id=competitor.id,
        state_code=state.code,
        county_name=county.name,
        city_name=city.name,
        address=competitor.address,
        latitude=float(competitor.latitude),
        longitude=float(competitor.longitude),
        name=competitor.name,
        brand=competitor.brand,
        website=competitor.website,
        phone=competitor.phone,
        contact_name=competitor.contact_name,
        contact_email=competitor.contact_email,
        follow_up_at=competitor.follow_up_at,
        serves_ice=competitor.serves_ice,
        serves_water=competitor.serves_water,
        machine_type=competitor.machine_type,
        machine_size=competitor.machine_size,
        is_inside=competitor.is_inside,
        ice_price=float(competitor.ice_price) if competitor.ice_price is not None else None,
        water_price=float(competitor.water_price) if competitor.water_price is not None else None,
        price_notes=competitor.price_notes,
        last_observed_date=competitor.last_observed_date,
        source=competitor.source,
        notes=competitor.notes,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
    )


_UPDATABLE_FIELDS = (
    "address",
    "latitude",
    "longitude",
    "name",
    "brand",
    "website",
    "phone",
    "contact_name",
    "contact_email",
    "follow_up_at",
    "serves_ice",
    "serves_water",
    "machine_type",
    "machine_size",
    "is_inside",
    "ice_price",
    "water_price",
    "price_notes",
    "last_observed_date",
    "source",
    "notes",
)


def update_competitor(db: Session, competitor: Competitor, data: CompetitorUpdateRequest) -> Competitor:
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is not None:
            setattr(competitor, field, new_value)
    db.commit()
    db.refresh(competitor)
    return competitor


def delete_competitor(db: Session, competitor: Competitor) -> None:
    db.delete(competitor)
    db.commit()
