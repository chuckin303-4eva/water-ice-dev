import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class LocationCreateRequest(BaseModel):
    """Either address, or (latitude and longitude), must be provided --
    whichever is missing gets filled in by geocoding. state/county/city
    are never supplied directly; they're always resolved from whichever
    of the two the caller gives (see location_service.create_location).
    """

    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    brand_id: uuid.UUID | None = None
    serves_ice: bool = False
    serves_water: bool = False
    machine_type: str | None = None
    host_business_id: uuid.UUID | None = None
    is_inside: bool | None = None

    # Manual 1-10 ratings feeding Basic Scoring (ADR-0009) -- these
    # columns existed since Phase 1 with no defined scale or API
    # exposure until now.
    visibility_rating: int | None = Field(default=None, ge=1, le=10)
    traffic_score: float | None = Field(default=None, ge=1, le=10)

    property_owner_name: str | None = None
    property_owner_phone: str | None = None
    property_management_company: str | None = None
    property_management_contact_name: str | None = None
    property_management_contact_phone: str | None = None
    primary_contact_name: str | None = None
    primary_contact_phone: str | None = None
    expected_unit_size: str | None = None
    power_connection_location: str | None = None
    power_company: str | None = None
    power_voltage: str | None = None
    water_connection_location: str | None = None
    water_company: str | None = None
    sewer_connection_availability: str | None = None
    sewer_connection_location: str | None = None
    pricing_estimate_monthly: float | None = None
    pricing_estimate_notes: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_address_or_coordinates(self) -> "LocationCreateRequest":
        has_address = bool(self.address)
        has_coordinates = self.latitude is not None and self.longitude is not None
        if not has_address and not has_coordinates:
            raise ValueError("provide either address, or both latitude and longitude")
        return self


class LocationUpdateRequest(BaseModel):
    """All fields optional -- only keys present in the request are
    touched. Re-geocoding on update is deliberately not automatic (a
    manually-corrected address/pin shouldn't silently get overwritten by
    another geocode call) -- moving a pin is a new address/coordinates
    pair the caller supplies directly.
    """

    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None
    brand_id: uuid.UUID | None = None
    serves_ice: bool | None = None
    serves_water: bool | None = None
    machine_type: str | None = None
    host_business_id: uuid.UUID | None = None
    is_inside: bool | None = None

    visibility_rating: int | None = Field(default=None, ge=1, le=10)
    traffic_score: float | None = Field(default=None, ge=1, le=10)

    property_owner_name: str | None = None
    property_owner_phone: str | None = None
    property_management_company: str | None = None
    property_management_contact_name: str | None = None
    property_management_contact_phone: str | None = None
    primary_contact_name: str | None = None
    primary_contact_phone: str | None = None
    expected_unit_size: str | None = None
    power_connection_location: str | None = None
    power_company: str | None = None
    power_voltage: str | None = None
    water_connection_location: str | None = None
    water_company: str | None = None
    sewer_connection_availability: str | None = None
    sewer_connection_location: str | None = None
    pricing_estimate_monthly: float | None = None
    pricing_estimate_notes: str | None = None
    notes: str | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    state_code: str
    county_name: str
    city_name: str
    zip_code: str
    address: str
    latitude: float
    longitude: float
    brand_id: uuid.UUID | None
    serves_ice: bool
    serves_water: bool
    machine_type: str | None
    host_business_id: uuid.UUID | None
    host_business_name: str | None
    host_business_category: str | None
    is_inside: bool | None
    status: str

    visibility_rating: int | None
    traffic_score: float | None
    competition_score: float | None
    opportunity_score: float | None
    confidence_score: float | None

    property_owner_name: str | None
    property_owner_phone: str | None
    property_management_company: str | None
    property_management_contact_name: str | None
    property_management_contact_phone: str | None
    primary_contact_name: str | None
    primary_contact_phone: str | None
    expected_unit_size: str | None
    power_connection_location: str | None
    power_company: str | None
    power_voltage: str | None
    water_connection_location: str | None
    water_company: str | None
    sewer_connection_availability: str | None
    sewer_connection_location: str | None
    pricing_estimate_monthly: float | None
    pricing_estimate_notes: str | None
    notes: str | None

    created_at: datetime
    updated_at: datetime


class LocationSummary(BaseModel):
    id: uuid.UUID
    address: str
    latitude: float
    longitude: float
    status: str
    opportunity_score: float | None = None

    model_config = {"from_attributes": True}


class LocationCallNoteCreateRequest(BaseModel):
    note_text: str
    follow_up_at: datetime | None = None


class LocationCallNoteResponse(BaseModel):
    id: int
    note_text: str
    call_date: datetime
    follow_up_at: datetime | None
    created_by: int

    model_config = {"from_attributes": True}


class CalendarLinkResponse(BaseModel):
    google: str
    outlook: str


class LocationImportRowError(BaseModel):
    row: int
    message: str


class LocationImportSummaryResponse(BaseModel):
    total_rows: int
    created: int
    queued: int = 0
    errors: list[LocationImportRowError]
