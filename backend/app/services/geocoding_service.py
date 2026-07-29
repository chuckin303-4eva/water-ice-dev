"""Geocoding via Nominatim (OpenStreetMap) -- free, no API key, consistent
with this project's "prioritize free sources" default (ADR-0004).

Nominatim's usage policy caps public-instance traffic at ~1 request/second
and requires a real User-Agent identifying the app -- fine for this
product's usage pattern (one geocode per prospect created/looked up by a
human, not a bulk operation). If prospecting volume ever makes that a
real constraint, that's a self-hosted-Nominatim or paid-geocoder decision
for a future ADR, not something to design around now.

Callers get back one of our own normalized geography rows (State/County/
City), resolved via get-or-create -- Nominatim's address breakdown is the
input, not the source of truth for how we store geography.
"""

from typing import NamedTuple

import httpx

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "water-ice-dev/0.1 (Ice & Water Intelligence location prospecting)"


class GeocodeResult(NamedTuple):
    latitude: float
    longitude: float
    address: str
    city_name: str | None
    county_name: str | None
    state_code: str | None
    zip_code: str | None


class GeocodingError(Exception):
    pass


def _parse_nominatim_result(result: dict) -> GeocodeResult:
    addr = result.get("address", {})
    city_name = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("hamlet")
    county_name = addr.get("county")
    if county_name and county_name.lower().endswith(" county"):
        county_name = county_name[: -len(" county")]
    return GeocodeResult(
        latitude=float(result["lat"]),
        longitude=float(result["lon"]),
        address=result.get("display_name", ""),
        city_name=city_name,
        county_name=county_name,
        state_code=addr.get("ISO3166-2-lvl4", "").split("-")[-1] or None,
        zip_code=addr.get("postcode"),
    )


def geocode_address(address: str) -> GeocodeResult:
    """Address -> coordinates + normalized geography breakdown."""
    response = httpx.get(
        f"{NOMINATIM_BASE}/search",
        params={"q": address, "format": "jsonv2", "addressdetails": 1, "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=10.0,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise GeocodingError(f"no geocoding result for address: {address!r}")
    return _parse_nominatim_result(results[0])


def reverse_geocode(latitude: float, longitude: float) -> GeocodeResult:
    """Coordinates -> address + normalized geography breakdown."""
    response = httpx.get(
        f"{NOMINATIM_BASE}/reverse",
        params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=10.0,
    )
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise GeocodingError(f"no geocoding result for coordinates: {latitude}, {longitude}")
    return _parse_nominatim_result(result)
