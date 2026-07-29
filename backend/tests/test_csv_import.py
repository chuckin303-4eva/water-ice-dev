import io

import pytest

from app.core.models.user import User
from app.services import csv_import_service, geocoding_service
from app.services.geocoding_service import GeocodeResult
from tests.conftest import auth_headers

_FAKE_GEOCODE = GeocodeResult(
    latitude=39.7392,
    longitude=-104.9903,
    address="123 Main St, Denver, CO 80202",
    city_name="Denver",
    county_name="Denver",
    state_code="CO",
    zip_code="80202",
)


@pytest.fixture(autouse=True)
def _mock_geocoding(monkeypatch):
    monkeypatch.setattr(geocoding_service, "geocode_address", lambda address: _FAKE_GEOCODE)
    monkeypatch.setattr(geocoding_service, "reverse_geocode", lambda lat, lon: _FAKE_GEOCODE)


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """The service sleeps between rows to respect Nominatim's rate
    limit -- real in production, pure overhead in a test with mocked
    geocoding.
    """
    monkeypatch.setattr(csv_import_service.time, "sleep", lambda seconds: None)


def _csv_file(content: str):
    return {"file": ("locations.csv", io.BytesIO(content.encode()), "text/csv")}


def test_import_creates_locations_from_valid_rows(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    csv_content = "address,serves_ice,serves_water\n123 Main St,true,false\n456 Oak Ave,false,true\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert body["created"] == 2
    assert body["errors"] == []

    listing = client.get("/locations", headers=headers)
    assert len(listing.json()) == 2


def test_import_by_coordinates(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    csv_content = "latitude,longitude\n39.7392,-104.9903\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_import_reports_row_errors_without_aborting(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    # Row 2 is missing both address and coordinates -- invalid.
    csv_content = "address,latitude,longitude\n123 Main St,,\n,,\n456 Oak Ave,,\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    assert body["created"] == 2
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 3  # header is row 1, first data row is row 2


def test_import_reports_geocoding_failures(client, test_user: User, monkeypatch) -> None:
    headers = auth_headers(client, test_user)

    def _raise(address):
        raise geocoding_service.GeocodingError("no result")

    monkeypatch.setattr(geocoding_service, "geocode_address", _raise)
    csv_content = "address\nnot a real place\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 0
    assert len(body["errors"]) == 1
    assert "geocode" in body["errors"][0]["message"].lower()


def test_import_rejects_files_over_the_row_cap(client, test_user: User, monkeypatch) -> None:
    headers = auth_headers(client, test_user)
    monkeypatch.setattr(csv_import_service, "MAX_IMPORT_ROWS", 2)
    csv_content = "address\n1 Main St\n2 Main St\n3 Main St\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 422


def test_import_handles_bom_and_missing_optional_columns(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    csv_content = "﻿address\n123 Main St\n"

    response = client.post("/locations/import", files=_csv_file(csv_content), headers=headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1
