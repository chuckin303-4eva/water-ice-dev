"""Get-or-create helpers for the normalized state/county/city hierarchy,
shared by anything that resolves a geocoding result into these tables
(location_service, competitor_service).
"""

from sqlalchemy.orm import Session

from app.core.models.geography import City, County, State
from app.services import geocoding_service
from app.services.geocoding_service import GeocodeResult


def get_or_create_state(db: Session, code: str) -> State:
    state = db.query(State).filter(State.code == code).first()
    if state is None:
        # name defaults to the code itself -- geocoding doesn't reliably
        # give us the full state name separately from the code; good
        # enough to be useful, correctable by hand like everything else.
        state = State(code=code, name=code)
        db.add(state)
        db.flush()
    return state


def get_or_create_county(db: Session, state: State, name: str) -> County:
    county = db.query(County).filter(County.state_id == state.id, County.name == name).first()
    if county is None:
        county = County(state_id=state.id, name=name)
        db.add(county)
        db.flush()
    return county


def get_or_create_city(db: Session, state: State, county: County, name: str) -> City:
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


def resolve_geography(db: Session, geocode: GeocodeResult) -> tuple[State, County, City]:
    if not geocode.state_code:
        raise geocoding_service.GeocodingError("geocoding result had no resolvable state")
    state = get_or_create_state(db, geocode.state_code)
    county = get_or_create_county(db, state, geocode.county_name or "Unknown")
    city = get_or_create_city(db, state, county, geocode.city_name or "Unincorporated")
    return state, county, city
