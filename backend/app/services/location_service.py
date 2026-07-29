"""Location (prospect) create/read/update/archive, plus geography
resolution from geocoding results.

Locations are shared, platform-wide market intelligence per ADR-0002 --
no organization scoping here, unlike LPC's businesses. Any authenticated
user can create/view/edit a prospect.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.api.schemas.location import LocationCreateRequest, LocationResponse, LocationUpdateRequest
from app.core.models.geography import City, County, State
from app.core.models.location import Location
from app.core.models.location_call_note import LocationCallNote
from app.core.models.update_log import UpdateLog
from app.services import geocoding_service
from app.services.geocoding_service import GeocodeResult

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
    "property_owner_name",
    "property_owner_phone",
    "property_management_company",
    "property_management_contact_name",
    "property_management_contact_phone",
    "primary_contact_name",
    "primary_contact_phone",
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
)


class LocationNotFoundError(Exception):
    pass


def _get_or_create_state(db: Session, code: str) -> State:
    state = db.query(State).filter(State.code == code).first()
    if state is None:
        # name defaults to the code itself -- geocoding doesn't reliably
        # give us the full state name separately from the code; good
        # enough to be useful, correctable by hand like everything else.
        state = State(code=code, name=code)
        db.add(state)
        db.flush()
    return state


def _get_or_create_county(db: Session, state: State, name: str) -> County:
    county = db.query(County).filter(County.state_id == state.id, County.name == name).first()
    if county is None:
        county = County(state_id=state.id, name=name)
        db.add(county)
        db.flush()
    return county


def _get_or_create_city(db: Session, state: State, county: County, name: str) -> City:
    city = (
        db.query(City)
        .filter(City.state_id == state.id, City.county_id == county.id, City.name == name)
        .first()
    )
    if city is None:
        city = City(state_id=state.id, county_id=county.id, name=name)
        db.add(city)
        db.flush()
    return city


def _resolve_geography(db: Session, geocode: GeocodeResult) -> tuple[State, County, City]:
    if not geocode.state_code:
        raise geocoding_service.GeocodingError("geocoding result had no resolvable state")
    state = _get_or_create_state(db, geocode.state_code)
    county = _get_or_create_county(db, state, geocode.county_name or "Unknown")
    city = _get_or_create_city(db, state, county, geocode.city_name or "Unincorporated")
    return state, county, city


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

    state, county, city = _resolve_geography(db, geocode)

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
        property_owner_name=data.property_owner_name,
        property_owner_phone=data.property_owner_phone,
        property_management_company=data.property_management_company,
        property_management_contact_name=data.property_management_contact_name,
        property_management_contact_phone=data.property_management_contact_phone,
        primary_contact_name=data.primary_contact_name,
        primary_contact_phone=data.primary_contact_phone,
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
    return location


def get_location(db: Session, location_id: uuid.UUID) -> Location | None:
    return db.query(Location).filter(Location.id == location_id).first()


def list_locations(db: Session, status: str | None = None) -> list[Location]:
    query = db.query(Location)
    if status is not None:
        query = query.filter(Location.status == status)
    return query.order_by(Location.created_at.desc()).all()


def assemble_response(db: Session, location: Location) -> LocationResponse:
    state = db.get(State, location.state_id)
    county = db.get(County, location.county_id)
    city = db.get(City, location.city_id)
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
        serves_ice=location.serves_ice,
        serves_water=location.serves_water,
        machine_type=location.machine_type,
        host_business_id=location.host_business_id,
        is_inside=location.is_inside,
        status=location.status,
        property_owner_name=location.property_owner_name,
        property_owner_phone=location.property_owner_phone,
        property_management_company=location.property_management_company,
        property_management_contact_name=location.property_management_contact_name,
        property_management_contact_phone=location.property_management_contact_phone,
        primary_contact_name=location.primary_contact_name,
        primary_contact_phone=location.primary_contact_phone,
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
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


def update_location(
    db: Session, location: Location, data: LocationUpdateRequest, updated_by: int
) -> Location:
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is None:
            continue
        old_value = getattr(location, field)
        if new_value != old_value:
            _log_change(db, location.id, field, old_value, new_value, updated_by)
            setattr(location, field, new_value)
    db.commit()
    db.refresh(location)
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
