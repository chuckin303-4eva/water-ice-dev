import httpx
import pytest

from app.services import geocoding_service


class _FakeResponse:
    def __init__(self, json_data, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


_NOMINATIM_RESULT = {
    "lat": "39.7392",
    "lon": "-104.9903",
    "display_name": "123 Main St, Denver, CO 80202",
    "address": {
        "city": "Denver",
        "county": "Denver County",
        "ISO3166-2-lvl4": "US-CO",
        "postcode": "80202",
    },
}


def test_geocode_address_parses_result(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse([_NOMINATIM_RESULT]))

    result = geocoding_service.geocode_address("123 Main St, Denver, CO")
    assert result.latitude == 39.7392
    assert result.longitude == -104.9903
    assert result.city_name == "Denver"
    assert result.county_name == "Denver"  # " County" suffix stripped
    assert result.state_code == "CO"
    assert result.zip_code == "80202"


def test_geocode_address_no_results_raises(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse([]))

    with pytest.raises(geocoding_service.GeocodingError):
        geocoding_service.geocode_address("nowhere at all")


def test_reverse_geocode_parses_result(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(_NOMINATIM_RESULT))

    result = geocoding_service.reverse_geocode(39.7392, -104.9903)
    assert result.city_name == "Denver"
    assert result.state_code == "CO"


def test_reverse_geocode_error_response_raises(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({"error": "Unable to geocode"}))

    with pytest.raises(geocoding_service.GeocodingError):
        geocoding_service.reverse_geocode(0.0, 0.0)


def test_missing_city_and_county_fall_back_gracefully(monkeypatch) -> None:
    sparse_result = {
        "lat": "40.0",
        "lon": "-100.0",
        "display_name": "Rural Route, KS",
        "address": {"ISO3166-2-lvl4": "US-KS"},
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse([sparse_result]))

    result = geocoding_service.geocode_address("rural route")
    assert result.city_name is None
    assert result.county_name is None
    assert result.state_code == "KS"
