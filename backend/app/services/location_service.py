"""Location (prospect) create/read/update/archive, plus geography
resolution from geocoding results.

Locations are shared, platform-wide market intelligence per ADR-0002 --
no organization scoping here, unlike LPC's businesses. Any authenticated
user can create/view/edit a prospect.
"""

import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.schemas.location import LocationCreateRequest, LocationResponse, LocationUpdateRequest
from app.core.models.brand import Brand
from app.core.models.geography import City, County, State
from app.core.models.host_business import HostBusiness
from app.core.models.location import Location
from app.core.models.location_call_note import LocationCallNote
from app.core.models.update_log import UpdateLog
from app.services import geocoding_service, scoring_service
from app.services.geography_service import resolve_geography

_ENTITY_TYPE = "location"

_UPDATABLE_FIELDS = (
    "address",
    "latitude",
    "longitude",
    "status",
    "brand_id",
    "serves_ice",
    "serves_water",
    "machine_type",
    "host_business_id",
    "is_inside",
    "visibility_rating",
    "traffic_score",
    "property_owner_name",
    "property_owner_phone",
    "property_management_company",
    "property_management_contact_name",
    "property_management_contact_phone",
    "primary_contact_name",
    "primary_contact_phone",
    "primary_contact_email",
    "website",
    "expected_unit_size",
    "power_connection_location",
    "power_company",
    "power_voltage",
    "water_connection_location",
    "water_company",
    "sewer_connection_availability",
    "sewer_connection_location",
    "pricing_estimate_monthly",
    "pricing_estimate_notes",
    "notes",
    "population",
    "median_income",
    "growth_rate",
)


class LocationNotFoundError(Exception):
    pass


class InvalidHostBusinessError(Exception):
    pass


class InvalidBrandError(Exception):
    pass


def _validate_host_business(db: Session, host_business_id: uuid.UUID | None) -> None:
    """A raw FK IntegrityError would otherwise surface as an unhelpful
    500 if the caller passes a host_business_id that doesn't exist.
    """
    if host_business_id is not None and db.get(HostBusiness, host_business_id) is None:
        raise InvalidHostBusinessError(f"Host business {host_business_id} does not exist")


def _validate_brand(db: Session, brand_id: uuid.UUID | None) -> None:
    if brand_id is not None and db.get(Brand, brand_id) is None:
        raise InvalidBrandError(f"Brand {brand_id} does not exist")


def _log_change(
    db: Session,
    location_id: uuid.UUID,
    field_name: str,
    old_value: object,
    new_value: object,
    changed_by: int | None,
    change_source: str = "manual",
) -> None:
    db.add(
        UpdateLog(
            entity_type=_ENTITY_TYPE,
            entity_id=str(location_id),
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=changed_by,
            change_source=change_source,
        )
    )


def create_location(db: Session, data: LocationCreateRequest, created_by: int) -> Location:
    _validate_host_business(db, data.host_business_id)
    _validate_brand(db, data.brand_id)
    if data.address and data.latitude is not None and data.longitude is not None:
        # Both given -- still geocode once (reverse, from the trusted
        # coordinates) purely to get the state/county/city breakdown in
        # our normalized format; the caller's address/coordinates win.
        geocode = geocoding_service.reverse_geocode(data.latitude, data.longitude)
        address, latitude, longitude = data.address, data.latitude, data.longitude
    elif data.address:
        geocode = geocoding_service.geocode_address(data.address)
        address, latitude, longitude = data.address, geocode.latitude, geocode.longitude
    else:
        geocode = geocoding_service.reverse_geocode(data.latitude, data.longitude)
        address, latitude, longitude = geocode.address, data.latitude, data.longitude

    state, county, city = resolve_geography(db, geocode)

    location = Location(
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        zip_code=geocode.zip_code or "",
        address=address,
        latitude=latitude,
        longitude=longitude,
        brand_id=data.brand_id,
        serves_ice=data.serves_ice,
        serves_water=data.serves_water,
        machine_type=data.machine_type,
        host_business_id=data.host_business_id,
        is_inside=data.is_inside,
        visibility_rating=data.visibility_rating,
        traffic_score=data.traffic_score,
        property_owner_name=data.property_owner_name,
        property_owner_phone=data.property_owner_phone,
        property_management_company=data.property_management_company,
        property_management_contact_name=data.property_management_contact_name,
        property_management_contact_phone=data.property_management_contact_phone,
        primary_contact_name=data.primary_contact_name,
        primary_contact_phone=data.primary_contact_phone,
        primary_contact_email=data.primary_contact_email,
        website=data.website,
        expected_unit_size=data.expected_unit_size,
        power_connection_location=data.power_connection_location,
        power_company=data.power_company,
        power_voltage=data.power_voltage,
        water_connection_location=data.water_connection_location,
        water_company=data.water_company,
        sewer_connection_availability=data.sewer_connection_availability,
        sewer_connection_location=data.sewer_connection_location,
        pricing_estimate_monthly=data.pricing_estimate_monthly,
        pricing_estimate_notes=data.pricing_estimate_notes,
        notes=data.notes,
    )
    db.add(location)
    db.flush()
    _log_change(db, location.id, "status", None, location.status, created_by)
    db.commit()
    db.refresh(location)
    scoring_service.recalculate_scores(db, location)
    return location


def get_location(db: Session, location_id: uuid.UUID) -> Location | None:
    return db.query(Location).filter(Location.id == location_id).first()


def list_locations(
    db: Session,
    statuses: list[str] | None = None,
    serves_ice: bool | None = None,
    serves_water: bool | None = None,
    min_opportunity_score: float | None = None,
) -> list[Location]:
    """Filters (Phase 1, item 7). `serves_ice`/`serves_water` are opt-in
    narrowing, not exclusion -- passing True for one or both requires at
    least one of the checked capabilities (OR across them), leaving both
    unset applies no filter at all. A strict "must serve exactly this
    and not that" filter would hide every freshly-created prospect,
    since serves_ice/serves_water both default to False until someone
    fills them in.
    """
    query = db.query(Location)
    if statuses:
        query = query.filter(Location.status.in_(statuses))
    capability_conditions = []
    if serves_ice:
        capability_conditions.append(Location.serves_ice.is_(True))
    if serves_water:
        capability_conditions.append(Location.serves_water.is_(True))
    if capability_conditions:
        query = query.filter(or_(*capability_conditions))
    if min_opportunity_score is not None:
        query = query.filter(Location.opportunity_score >= min_opportunity_score)
    return query.order_by(Location.created_at.desc()).all()


def assemble_response(db: Session, location: Location) -> LocationResponse:
    state = db.get(State, location.state_id)
    county = db.get(County, location.county_id)
    city = db.get(City, location.city_id)
    host_business = db.get(HostBusiness, location.host_business_id) if location.host_business_id else None
    brand = db.get(Brand, location.brand_id) if location.brand_id else None
    return LocationResponse(
        id=location.id,
        state_code=state.code,
        county_name=county.name,
        city_name=city.name,
        zip_code=location.zip_code,
        address=location.address,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        brand_id=location.brand_id,
        brand_name=brand.name if brand else None,
        serves_ice=location.serves_ice,
        serves_water=location.serves_water,
        machine_type=location.machine_type,
        host_business_id=location.host_business_id,
        host_business_name=host_business.name if host_business else None,
        host_business_category=host_business.category if host_business else None,
        is_inside=location.is_inside,
        status=location.status,
        visibility_rating=location.visibility_rating,
        traffic_score=float(location.traffic_score) if location.traffic_score is not None else None,
        competition_score=float(location.competition_score) if location.competition_score is not None else None,
        opportunity_score=float(location.opportunity_score) if location.opportunity_score is not None else None,
        confidence_score=float(location.confidence_score) if location.confidence_score is not None else None,
        property_owner_name=location.property_owner_name,
        property_owner_phone=location.property_owner_phone,
        property_management_company=location.property_management_company,
        property_management_contact_name=location.property_management_contact_name,
        property_management_contact_phone=location.property_management_contact_phone,
        primary_contact_name=location.primary_contact_name,
        primary_contact_phone=location.primary_contact_phone,
        primary_contact_email=location.primary_contact_email,
        website=location.website,
        expected_unit_size=location.expected_unit_size,
        power_connection_location=location.power_connection_location,
        power_company=location.power_company,
        power_voltage=location.power_voltage,
        water_connection_location=location.water_connection_location,
        water_company=location.water_company,
        sewer_connection_availability=location.sewer_connection_availability,
        sewer_connection_location=location.sewer_connection_location,
        pricing_estimate_monthly=float(location.pricing_estimate_monthly)
        if location.pricing_estimate_monthly is not None
        else None,
        pricing_estimate_notes=location.pricing_estimate_notes,
        notes=location.notes,
        population=location.population,
        median_income=float(location.median_income) if location.median_income is not None else None,
        growth_rate=float(location.growth_rate) if location.growth_rate is not None else None,
        last_verified_at=location.last_verified_at,
        verification_source=location.verification_source,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


def update_location(
    db: Session,
    location: Location,
    data: LocationUpdateRequest,
    updated_by: int | None,
    change_source: str = "manual",
) -> Location:
    """`updated_by`/`change_source` are widened beyond the original
    human-write case to support the Market Refresh Engine (ADR-0020),
    which proposes updates with no specific user attached -- approving
    one of those replays this same function with `updated_by=None,
    change_source="verification"` so `update_log` records it honestly.
    """
    _validate_host_business(db, data.host_business_id)
    _validate_brand(db, data.brand_id)
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is None:
            continue
        old_value = getattr(location, field)
        if new_value != old_value:
            _log_change(db, location.id, field, old_value, new_value, updated_by, change_source)
            setattr(location, field, new_value)
    db.commit()
    db.refresh(location)
    scoring_service.recalculate_scores(db, location)
    return location


def archive_location(db: Session, location: Location, updated_by: int) -> None:
    old_status = location.status
    location.status = "archived"
    _log_change(db, location.id, "status", old_status, "archived", updated_by)
    db.commit()


def add_call_note(
    db: Session, location_id: uuid.UUID, note_text: str, follow_up_at: datetime | None, created_by: int
) -> LocationCallNote:
    note = LocationCallNote(
        location_id=location_id, note_text=note_text, follow_up_at=follow_up_at, created_by=created_by
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_call_notes(db: Session, location_id: uuid.UUID) -> list[LocationCallNote]:
    return (
        db.query(LocationCallNote)
        .filter(LocationCallNote.location_id == location_id)
        .order_by(LocationCallNote.call_date.desc())
        .all()
    )


def get_call_note(db: Session, location_id: uuid.UUID, note_id: int) -> LocationCallNote | None:
    return (
        db.query(LocationCallNote)
        .filter(LocationCallNote.id == note_id, LocationCallNote.location_id == location_id)
        .first()
    )
