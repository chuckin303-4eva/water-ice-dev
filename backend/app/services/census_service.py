"""US Census demographic lookups (Market Refresh Engine; ADR-0004/0020).

Two endpoints, with different auth requirements discovered against the
real API (the original "no key needed" assumption was wrong for one of
them):
- Census Geocoder: coordinates -> state/county/tract FIPS codes. Keyless.
- ACS 5-Year Estimates: population (B01003_001E) and median household
  income (B19013_001E) for a given tract. Requires a free key (signup at
  https://api.census.gov/data/key_signup.html) -- without one the API
  302-redirects to an error page instead of returning data. If
  settings.census_api_key is unset, get_demographics raises
  CensusLookupError, which CensusProvider.check_location treats the same
  as any other lookup failure: this location is skipped for this run,
  not an error that fails the whole refresh.

Growth rate is derived, not a single Census field -- computed as the
percent change in population between two ACS 5-year vintages five years
apart. CURRENT_ACS_YEAR/EARLIER_ACS_YEAR should be bumped periodically
as the Census Bureau releases new ACS5 datasets; nothing else about
this integration needs to change when that happens.
"""

from typing import NamedTuple

import httpx

from app.core.config import settings

GEOCODER_BASE = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
ACS_BASE = "https://api.census.gov/data"
CURRENT_ACS_YEAR = 2022
EARLIER_ACS_YEAR = 2017

# Census's documented sentinel for a suppressed/unavailable value in ACS
# tables (small-population tracts commonly have one).
_MISSING_VALUE = "-666666666"


class CensusGeography(NamedTuple):
    state_fips: str
    county_fips: str
    tract_fips: str


class CensusDemographics(NamedTuple):
    population: int | None
    median_income: float | None
    growth_rate: float | None


class CensusLookupError(Exception):
    pass


def _parse_numeric(raw: str | None) -> str | None:
    return None if raw in (None, "", _MISSING_VALUE) else raw


def geocode_to_tract(latitude: float, longitude: float) -> CensusGeography:
    try:
        response = httpx.get(
            GEOCODER_BASE,
            params={
                "x": longitude,
                "y": latitude,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise CensusLookupError(f"Census geocoder request failed: {exc}") from exc

    tracts = data.get("result", {}).get("geographies", {}).get("Census Tracts", [])
    if not tracts:
        raise CensusLookupError(f"No Census tract found for coordinates: {latitude}, {longitude}")
    tract = tracts[0]
    return CensusGeography(state_fips=tract["STATE"], county_fips=tract["COUNTY"], tract_fips=tract["TRACT"])


def _fetch_acs(year: int, fields: str, geography: CensusGeography) -> list[str]:
    params = {
        "get": fields,
        "for": f"tract:{geography.tract_fips}",
        "in": f"state:{geography.state_fips} county:{geography.county_fips}",
    }
    if settings.census_api_key:
        params["key"] = settings.census_api_key
    try:
        response = httpx.get(f"{ACS_BASE}/{year}/acs/acs5", params=params, timeout=10.0)
        response.raise_for_status()
        # A tract with no data for this vintage comes back as 204 No
        # Content (success status, empty body) rather than an HTTP error --
        # discovered against the real API, not documented behavior assumed
        # up front. json.JSONDecodeError also covers any other malformed
        # body the same way.
        if not response.content:
            raise CensusLookupError(f"No ACS {year} data for tract {geography.tract_fips}")
        rows = response.json()
    except httpx.HTTPError as exc:
        raise CensusLookupError(f"ACS request failed for {year}: {exc}") from exc
    except ValueError as exc:
        raise CensusLookupError(f"ACS {year} response was not valid JSON: {exc}") from exc

    if len(rows) < 2:
        raise CensusLookupError(f"No ACS {year} data for tract {geography.tract_fips}")
    return rows[1]


def get_demographics(geography: CensusGeography) -> CensusDemographics:
    if not settings.census_api_key:
        raise CensusLookupError("CENSUS_API_KEY not configured -- see .env.example")
    pop_raw, income_raw = _fetch_acs(CURRENT_ACS_YEAR, "B01003_001E,B19013_001E", geography)[:2]
    population_str = _parse_numeric(pop_raw)
    median_income_str = _parse_numeric(income_raw)
    population = int(population_str) if population_str is not None else None
    median_income = float(median_income_str) if median_income_str is not None else None

    growth_rate = None
    if population is not None:
        try:
            earlier_raw = _fetch_acs(EARLIER_ACS_YEAR, "B01003_001E", geography)[0]
            earlier_str = _parse_numeric(earlier_raw)
            earlier_population = int(earlier_str) if earlier_str is not None else None
            if earlier_population:
                growth_rate = round(
                    ((population - earlier_population) / earlier_population) * 100, 3
                )
        except CensusLookupError:
            growth_rate = None  # a nice-to-have -- don't fail the whole lookup over it

    return CensusDemographics(population=population, median_income=median_income, growth_rate=growth_rate)
