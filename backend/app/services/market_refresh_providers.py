"""Market Refresh Engine provider interface (ADR-0004), scope narrowed
for v1 (ADR-0020): OpenStreetMap-based address verification and US
Census demographics only.

"New competitor POIs nearby" from ADR-0004's original OpenStreetMap
scope was dropped -- ADR-0008 already confirmed, via direct research,
that OSM has essentially no tagging coverage for ice/water vending
machines, so building that query would be known low-yield rather than
closing a genuine gap. "Business closed/moved" and "host business tag
changed" need a stable OSM node id captured at creation time to track a
specific POI over time, which this schema doesn't have -- deferred, not
built as a guess.

Same replaceable-module shape as ADR-0004 originally sketched: adding,
removing, or swapping a provider never touches the orchestration logic
in market_refresh_service.py.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NamedTuple, Protocol

from app.core.models.location import Location
from app.services import census_service, geocoding_service


@dataclass(frozen=True)
class LocationSnapshot:
    id: str
    address: str
    latitude: float
    longitude: float
    population: int | None
    median_income: float | None
    growth_rate: float | None


class FieldObservation(NamedTuple):
    field_name: str
    observed_value: object
    confidence: float
    source: str
    observed_at: datetime


class MarketDataProvider(Protocol):
    slug: str
    is_free: bool

    def check_location(self, snapshot: LocationSnapshot) -> list[FieldObservation]: ...


def snapshot_from_location(location: Location) -> LocationSnapshot:
    return LocationSnapshot(
        id=str(location.id),
        address=location.address,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        population=location.population,
        median_income=float(location.median_income) if location.median_income is not None else None,
        growth_rate=float(location.growth_rate) if location.growth_rate is not None else None,
    )


def _normalize_address(address: str) -> str:
    return " ".join(address.lower().split())


class OpenStreetMapProvider:
    """Address verification only for v1 (ADR-0020) -- reverse-geocodes
    the location's stored coordinates via the same Nominatim service
    already used for prospecting (ADR-0006) and flags a drift if the
    result differs from the stored address.
    """

    slug = "openstreetmap"
    is_free = True

    def check_location(self, snapshot: LocationSnapshot) -> list[FieldObservation]:
        try:
            geocode = geocoding_service.reverse_geocode(snapshot.latitude, snapshot.longitude)
        except geocoding_service.GeocodingError:
            return []
        if not geocode.address or _normalize_address(geocode.address) == _normalize_address(
            snapshot.address
        ):
            return []
        return [
            FieldObservation(
                field_name="address",
                observed_value=geocode.address,
                confidence=0.6,
                source=self.slug,
                observed_at=datetime.now(UTC),
            )
        ]


class CensusProvider:
    """Population, median household income, and growth rate from free
    ACS 5-year estimates (ADR-0004/ADR-0020)."""

    slug = "census"
    is_free = True

    def check_location(self, snapshot: LocationSnapshot) -> list[FieldObservation]:
        try:
            geography = census_service.geocode_to_tract(snapshot.latitude, snapshot.longitude)
            demographics = census_service.get_demographics(geography)
        except census_service.CensusLookupError:
            return []

        now = datetime.now(UTC)
        observations: list[FieldObservation] = []
        if demographics.population is not None and demographics.population != snapshot.population:
            observations.append(
                FieldObservation("population", demographics.population, 0.8, self.slug, now)
            )
        if (
            demographics.median_income is not None
            and demographics.median_income != snapshot.median_income
        ):
            observations.append(
                FieldObservation("median_income", demographics.median_income, 0.8, self.slug, now)
            )
        if demographics.growth_rate is not None and demographics.growth_rate != snapshot.growth_rate:
            observations.append(
                FieldObservation("growth_rate", demographics.growth_rate, 0.6, self.slug, now)
            )
        return observations


PROVIDERS: list[MarketDataProvider] = [OpenStreetMapProvider(), CensusProvider()]
