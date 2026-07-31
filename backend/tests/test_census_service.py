import httpx
import pytest

from app.services import census_service

_GEOCODER_RESPONSE = {
    "result": {"geographies": {"Census Tracts": [{"STATE": "08", "COUNTY": "031", "TRACT": "003200"}]}}
}
_ACS_CURRENT = [
    ["B01003_001E", "B19013_001E", "state", "county", "tract"],
    ["4523", "65432", "08", "031", "003200"],
]
_ACS_EARLIER = [["B01003_001E", "state", "county", "tract"], ["4000", "08", "031", "003200"]]
_ACS_MISSING = [
    ["B01003_001E", "B19013_001E", "state", "county", "tract"],
    ["-666666666", "-666666666", "08", "031", "003200"],
]


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.content = b"" if json_data is None else b"non-empty"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def _make_fake_get(acs_current=_ACS_CURRENT, acs_earlier=_ACS_EARLIER, geocoder=_GEOCODER_RESPONSE):
    def fake_get(url, params=None, timeout=None):
        if "geographies/coordinates" in url:
            return _FakeResponse(geocoder)
        if f"/{census_service.CURRENT_ACS_YEAR}/" in url:
            return _FakeResponse(acs_current)
        if f"/{census_service.EARLIER_ACS_YEAR}/" in url:
            return _FakeResponse(acs_earlier)
        raise AssertionError(f"unexpected URL: {url}")

    return fake_get


def test_geocode_to_tract_parses_response(monkeypatch):
    monkeypatch.setattr(census_service.httpx, "get", _make_fake_get())
    geography = census_service.geocode_to_tract(39.7392, -104.9903)
    assert geography.state_fips == "08"
    assert geography.county_fips == "031"
    assert geography.tract_fips == "003200"


def test_geocode_to_tract_raises_when_no_tract_found(monkeypatch):
    monkeypatch.setattr(
        census_service.httpx, "get", _make_fake_get(geocoder={"result": {"geographies": {}}})
    )
    with pytest.raises(census_service.CensusLookupError):
        census_service.geocode_to_tract(0.0, 0.0)


def test_get_demographics_computes_growth_rate(monkeypatch):
    monkeypatch.setattr(census_service.settings, "census_api_key", "test-key")
    monkeypatch.setattr(census_service.httpx, "get", _make_fake_get())
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    demographics = census_service.get_demographics(geography)
    assert demographics.population == 4523
    assert demographics.median_income == 65432.0
    assert demographics.growth_rate == pytest.approx(13.075, abs=0.001)


def test_get_demographics_treats_sentinel_as_missing(monkeypatch):
    monkeypatch.setattr(census_service.settings, "census_api_key", "test-key")
    monkeypatch.setattr(census_service.httpx, "get", _make_fake_get(acs_current=_ACS_MISSING))
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    demographics = census_service.get_demographics(geography)
    assert demographics.population is None
    assert demographics.median_income is None
    assert demographics.growth_rate is None


def test_get_demographics_survives_missing_earlier_vintage(monkeypatch):
    monkeypatch.setattr(census_service.settings, "census_api_key", "test-key")
    monkeypatch.setattr(
        census_service.httpx, "get", _make_fake_get(acs_earlier=[["B01003_001E"], ["-666666666"]])
    )
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    demographics = census_service.get_demographics(geography)
    assert demographics.population == 4523
    assert demographics.growth_rate is None


def test_get_demographics_raises_when_api_key_unset(monkeypatch):
    monkeypatch.setattr(census_service.settings, "census_api_key", None)
    monkeypatch.setattr(census_service.httpx, "get", _make_fake_get())
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    with pytest.raises(census_service.CensusLookupError):
        census_service.get_demographics(geography)


def test_fetch_acs_includes_api_key_param(monkeypatch):
    monkeypatch.setattr(census_service.settings, "census_api_key", "test-key")
    seen_params = {}

    def fake_get(url, params=None, timeout=None):
        seen_params.update(params)
        return _FakeResponse(_ACS_CURRENT)

    monkeypatch.setattr(census_service.httpx, "get", fake_get)
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    census_service._fetch_acs(census_service.CURRENT_ACS_YEAR, "B01003_001E", geography)
    assert seen_params["key"] == "test-key"


def test_fetch_acs_raises_on_empty_204_response(monkeypatch):
    # Discovered against the real API: a tract with no data for a given
    # vintage comes back 204 No Content with an empty body, not an HTTP
    # error and not a JSON array -- e.g. non-residential tracts lacking
    # earlier-vintage ACS5 data.
    monkeypatch.setattr(census_service.settings, "census_api_key", "test-key")

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(None, status_code=204)

    monkeypatch.setattr(census_service.httpx, "get", fake_get)
    geography = census_service.CensusGeography(state_fips="08", county_fips="031", tract_fips="003200")
    with pytest.raises(census_service.CensusLookupError):
        census_service._fetch_acs(census_service.CURRENT_ACS_YEAR, "B01003_001E", geography)


def test_http_error_becomes_census_lookup_error(monkeypatch):
    def failing_get(url, params=None, timeout=None):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(census_service.httpx, "get", failing_get)
    with pytest.raises(census_service.CensusLookupError):
        census_service.geocode_to_tract(39.7392, -104.9903)
