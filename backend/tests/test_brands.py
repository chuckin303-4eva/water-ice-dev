import pytest

from app.core.models.user import User
from app.services import geocoding_service
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


def test_create_brand(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/brands", json={"name": "Twice the Ice", "description": "Franchise ice vending"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Twice the Ice"
    assert body["description"] == "Franchise ice vending"
    assert body["logo_url"] is None


def test_create_brand_requires_name(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post("/brands", json={"description": "no name"}, headers=headers)
    assert response.status_code == 422


def test_list_brands_search_matches_name(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    client.post("/brands", json={"name": "Twice the Ice"}, headers=headers)
    client.post("/brands", json={"name": "Kooler Ice"}, headers=headers)

    matches = client.get("/brands", params={"search": "twice"}, headers=headers).json()
    assert [b["name"] for b in matches] == ["Twice the Ice"]

    everything = client.get("/brands", headers=headers).json()
    assert len(everything) == 2


def test_get_brand(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/brands", json={"name": "Twice the Ice"}, headers=headers).json()
    response = client.get(f"/brands/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Twice the Ice"


def test_get_brand_404(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.get("/brands/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.status_code == 404


def test_update_brand(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/brands", json={"name": "Twice the Ice"}, headers=headers).json()
    response = client.put(
        f"/brands/{created['id']}", json={"logo_url": "https://example.com/logo.png"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Twice the Ice"
    assert body["logo_url"] == "https://example.com/logo.png"


def test_delete_unused_brand(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/brands", json={"name": "Twice the Ice"}, headers=headers).json()
    response = client.delete(f"/brands/{created['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/brands/{created['id']}", headers=headers).status_code == 404


def test_delete_brand_in_use_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    brand = client.post("/brands", json={"name": "Twice the Ice"}, headers=headers).json()
    client.post(
        "/locations",
        json={"address": "123 Main St, Denver, CO", "brand_id": brand["id"]},
        headers=headers,
    )
    response = client.delete(f"/brands/{brand['id']}", headers=headers)
    assert response.status_code == 409


def test_create_location_with_brand_includes_brand_name(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    brand = client.post("/brands", json={"name": "Twice the Ice"}, headers=headers).json()
    response = client.post(
        "/locations",
        json={"address": "123 Main St, Denver, CO", "brand_id": brand["id"]},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["brand_id"] == brand["id"]
    assert body["brand_name"] == "Twice the Ice"


def test_create_location_with_invalid_brand_id_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={
            "address": "123 Main St, Denver, CO",
            "brand_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_update_location_with_invalid_brand_id_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = client.post("/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers).json()
    response = client.put(
        f"/locations/{location['id']}",
        json={"brand_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_location_with_website_and_contact_email(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={
            "address": "123 Main St, Denver, CO",
            "website": "https://example.com",
            "primary_contact_email": "owner@example.com",
            "primary_contact_name": "Jane Owner",
            "primary_contact_phone": "555-1212",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["website"] == "https://example.com"
    assert body["primary_contact_email"] == "owner@example.com"
    assert body["primary_contact_name"] == "Jane Owner"
    assert body["primary_contact_phone"] == "555-1212"
