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


def _register(client, org_name: str, email: str, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/register", json={"organization_name": org_name, "email": email, "password": password}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_location(client, headers) -> dict:
    return client.post("/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers).json()


def test_create_opportunity(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    response = client.post("/opportunities", json={"location_id": location["id"]}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["location_id"] == location["id"]
    assert body["location_address"] == location["address"]
    assert body["stage"] == "identified"
    assert body["assigned_user_id"] is None


def test_create_opportunity_with_invalid_location_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/opportunities",
        json={"location_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_opportunity_with_invalid_stage_is_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    response = client.post(
        "/opportunities", json={"location_id": location["id"], "stage": "bogus"}, headers=headers
    )
    assert response.status_code == 422


def test_create_opportunity_assigned_to_user_outside_org_is_rejected(client, test_user: User) -> None:
    other_org_headers = _register(client, "Other Org", "otheradmin@example.com")
    other_org_me = client.get("/auth/me", headers=other_org_headers).json()

    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    response = client.post(
        "/opportunities",
        json={"location_id": location["id"], "assigned_user_id": other_org_me["id"]},
        headers=headers,
    )
    assert response.status_code == 422


def test_list_opportunities_scoped_to_own_organization(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    client.post("/opportunities", json={"location_id": location["id"]}, headers=headers)

    other_org_headers = _register(client, "Other Org", "otheradmin2@example.com")
    other_location = _make_location(client, other_org_headers)
    client.post("/opportunities", json={"location_id": other_location["id"]}, headers=other_org_headers)

    mine = client.get("/opportunities", headers=headers).json()
    assert len(mine) == 1
    assert mine[0]["location_id"] == location["id"]

    theirs = client.get("/opportunities", headers=other_org_headers).json()
    assert len(theirs) == 1
    assert theirs[0]["location_id"] == other_location["id"]


def test_list_opportunities_filters_by_stage(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    loc_a = _make_location(client, headers)
    loc_b = _make_location(client, headers)
    opp_a = client.post("/opportunities", json={"location_id": loc_a["id"]}, headers=headers).json()
    client.post("/opportunities", json={"location_id": loc_b["id"]}, headers=headers)
    client.put(f"/opportunities/{opp_a['id']}", json={"stage": "won"}, headers=headers)

    won = client.get("/opportunities", params={"stage": "won"}, headers=headers).json()
    assert len(won) == 1
    assert won[0]["id"] == opp_a["id"]


def test_update_opportunity_stage(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    created = client.post("/opportunities", json={"location_id": location["id"]}, headers=headers).json()
    response = client.put(f"/opportunities/{created['id']}", json={"stage": "contacted"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["stage"] == "contacted"


def test_cannot_access_other_organizations_opportunity(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    created = client.post("/opportunities", json={"location_id": location["id"]}, headers=headers).json()

    other_org_headers = _register(client, "Other Org", "otheradmin3@example.com")
    response = client.get(f"/opportunities/{created['id']}", headers=other_org_headers)
    assert response.status_code == 404
    response = client.put(
        f"/opportunities/{created['id']}", json={"stage": "won"}, headers=other_org_headers
    )
    assert response.status_code == 404
    response = client.delete(f"/opportunities/{created['id']}", headers=other_org_headers)
    assert response.status_code == 404


def test_delete_opportunity(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    created = client.post("/opportunities", json={"location_id": location["id"]}, headers=headers).json()
    response = client.delete(f"/opportunities/{created['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/opportunities/{created['id']}", headers=headers).status_code == 404
