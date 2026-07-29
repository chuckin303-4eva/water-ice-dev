import uuid
from datetime import date, datetime

from pydantic import BaseModel, model_validator


class CompetitorCreateRequest(BaseModel):
    """Either address, or (latitude and longitude), must be provided --
    same pattern as LocationCreateRequest. `name` (the rival brand/
    operator) is required -- an unnamed competitor pin isn't useful.
    """

    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    name: str
    serves_ice: bool = False
    serves_water: bool = False
    machine_type: str | None = None
    machine_size: str | None = None
    is_inside: bool | None = None
    ice_price: float | None = None
    water_price: float | None = None
    price_notes: str | None = None
    last_observed_date: date | None = None
    source: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_address_or_coordinates(self) -> "CompetitorCreateRequest":
        has_address = bool(self.address)
        has_coordinates = self.latitude is not None and self.longitude is not None
        if not has_address and not has_coordinates:
            raise ValueError("provide either address, or both latitude and longitude")
        return self


class CompetitorUpdateRequest(BaseModel):
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    name: str | None = None
    serves_ice: bool | None = None
    serves_water: bool | None = None
    machine_type: str | None = None
    machine_size: str | None = None
    is_inside: bool | None = None
    ice_price: float | None = None
    water_price: float | None = None
    price_notes: str | None = None
    last_observed_date: date | None = None
    source: str | None = None
    notes: str | None = None


class CompetitorResponse(BaseModel):
    id: uuid.UUID
    state_code: str
    county_name: str
    city_name: str
    address: str
    latitude: float
    longitude: float

    name: str
    serves_ice: bool
    serves_water: bool
    machine_type: str | None
    machine_size: str | None
    is_inside: bool | None
    ice_price: float | None
    water_price: float | None
    price_notes: str | None
    last_observed_date: date | None
    source: str | None
    notes: str | None

    created_at: datetime
    updated_at: datetime


class CompetitorSummary(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    latitude: float
    longitude: float
    serves_ice: bool
    serves_water: bool

    model_config = {"from_attributes": True}
