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


def test_create_host_business(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/host-businesses",
        json={"name": "Shell Station #42", "category": "gas_station", "phone": "555-1234"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Shell Station #42"
    assert body["category"] == "gas_station"
    assert body["phone"] == "555-1234"
    assert body["website"] is None


def test_create_host_business_requires_name(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post("/host-businesses", json={"category": "gas_station"}, headers=headers)
    assert response.status_code == 422


def test_list_host_businesses_search_matches_name_or_category(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    client.post("/host-businesses", json={"name": "Shell Station #42", "category": "gas_station"}, headers=headers)
    client.post("/host-businesses", json={"name": "Spin Cycle Laundromat", "category": "laundromat"}, headers=headers)

    by_name = client.get("/host-businesses", params={"search": "shell"}, headers=headers).json()
    assert [h["name"] for h in by_name] == ["Shell Station #42"]

    by_category = client.get("/host-businesses", params={"search": "laundromat"}, headers=headers).json()
    assert [h["name"] for h in by_category] == ["Spin Cycle Laundromat"]

    everything = client.get("/host-businesses", headers=headers).json()
    assert len(everything) == 2


def test_get_host_business(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/host-businesses", json={"name": "Shell Station #42"}, headers=headers).json()
    response = client.get(f"/host-businesses/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Shell Station #42"


def test_get_host_business_404(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.get("/host-businesses/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.status_code == 404


def test_update_host_business(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/host-businesses", json={"name": "Shell Station #42"}, headers=headers).json()
    response = client.put(
        f"/host-businesses/{created['id']}",
        json={"phone": "555-9999", "website": "https://shell.example.com"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Shell Station #42"
    assert body["phone"] == "555-9999"
    assert body["website"] == "https://shell.example.com"


def test_delete_unused_host_business(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    created = client.post("/host-businesses", json={"name": "Shell Station #42"}, headers=headers).json()
    response = client.delete(f"/host-businesses/{created['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/host-businesses/{created['id']}", headers=headers).status_code == 404


def test_delete_host_business_in_use_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    host_business = client.post("/host-businesses", json={"name": "Shell Station #42"}, headers=headers).json()
    client.post(
        "/locations",
        json={"address": "123 Main St, Denver, CO", "host_business_id": host_business["id"]},
        headers=headers,
    )
    response = client.delete(f"/host-businesses/{host_business['id']}", headers=headers)
    assert response.status_code == 409


def test_create_location_with_host_business_includes_name_and_category(
    client, test_user: User
) -> None:
    headers = auth_headers(client, test_user)
    host_business = client.post(
        "/host-businesses", json={"name": "Shell Station #42", "category": "gas_station"}, headers=headers
    ).json()
    response = client.post(
        "/locations",
        json={"address": "123 Main St, Denver, CO", "host_business_id": host_business["id"]},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["host_business_id"] == host_business["id"]
    assert body["host_business_name"] == "Shell Station #42"
    assert body["host_business_category"] == "gas_station"


def test_create_location_with_invalid_host_business_id_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={
            "address": "123 Main St, Denver, CO",
            "host_business_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_update_location_with_invalid_host_business_id_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = client.post("/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers).json()
    response = client.put(
        f"/locations/{location['id']}",
        json={"host_business_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_location_links_host_business(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = client.post("/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers).json()
    assert location["host_business_name"] is None
    host_business = client.post(
        "/host-businesses", json={"name": "Spin Cycle Laundromat", "category": "laundromat"}, headers=headers
    ).json()
    response = client.put(
        f"/locations/{location['id']}",
        json={"host_business_id": host_business["id"]},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["host_business_name"] == "Spin Cycle Laundromat"
    assert body["host_business_category"] == "laundromat"
