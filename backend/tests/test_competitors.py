import pytest

from app.core.models.user import User
from app.services import geocoding_service
from app.services.geocoding_service import GeocodeResult
from tests.conftest import auth_headers

_FAKE_GEOCODE = GeocodeResult(
    latitude=39.7392,
    longitude=-104.9903,
    address="456 Rival Ave, Denver, CO 80202",
    city_name="Denver",
    county_name="Denver",
    state_code="CO",
    zip_code="80202",
)


@pytest.fixture(autouse=True)
def _mock_geocoding(monkeypatch):
    monkeypatch.setattr(geocoding_service, "geocode_address", lambda address: _FAKE_GEOCODE)
    monkeypatch.setattr(geocoding_service, "reverse_geocode", lambda lat, lon: _FAKE_GEOCODE)


def test_create_competitor_by_address(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/competitors",
        json={"address": "456 Rival Ave, Denver, CO", "name": "Twice the Ice", "serves_ice": True},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Twice the Ice"
    assert body["serves_ice"] is True
    assert body["serves_water"] is False
    assert body["state_code"] == "CO"


def test_create_competitor_requires_name(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/competitors", json={"address": "456 Rival Ave, Denver, CO"}, headers=headers
    )
    assert response.status_code == 422


def test_create_competitor_requires_address_or_coordinates(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post("/competitors", json={"name": "Twice the Ice"}, headers=headers)
    assert response.status_code == 422


def test_create_competitor_with_prices_and_size(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/competitors",
        json={
            "address": "456 Rival Ave, Denver, CO",
            "name": "Kooler Ice",
            "serves_ice": True,
            "serves_water": True,
            "machine_size": "Large kiosk",
            "is_inside": False,
            "ice_price": 1.75,
            "water_price": 0.35,
            "price_notes": "$1.75 per 16lb bag, $0.35/gallon filtered water",
            "source": "field visit 2026-07-29",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["ice_price"] == 1.75
    assert body["water_price"] == 0.35
    assert body["machine_size"] == "Large kiosk"
    assert body["is_inside"] is False
    assert body["source"] == "field visit 2026-07-29"


def test_get_and_list_competitors(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post(
        "/competitors", json={"address": "456 Rival Ave", "name": "Twice the Ice"}, headers=headers
    )
    competitor_id = create.json()["id"]

    get = client.get(f"/competitors/{competitor_id}", headers=headers)
    assert get.status_code == 200

    listing = client.get("/competitors", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_get_nonexistent_competitor_404s(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.get("/competitors/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.status_code == 404


def test_update_competitor(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post(
        "/competitors", json={"address": "456 Rival Ave", "name": "Twice the Ice"}, headers=headers
    )
    competitor_id = create.json()["id"]

    update = client.put(
        f"/competitors/{competitor_id}", json={"ice_price": 2.00}, headers=headers
    )
    assert update.status_code == 200
    assert update.json()["ice_price"] == 2.00


def test_delete_competitor(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post(
        "/competitors", json={"address": "456 Rival Ave", "name": "Twice the Ice"}, headers=headers
    )
    competitor_id = create.json()["id"]

    delete = client.delete(f"/competitors/{competitor_id}", headers=headers)
    assert delete.status_code == 204

    get = client.get(f"/competitors/{competitor_id}", headers=headers)
    assert get.status_code == 404


def test_create_competitor_with_contact_fields(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/competitors",
        json={
            "address": "456 Rival Ave, Denver, CO",
            "name": "Twice the Ice - King Soopers",
            "brand": "Twice the Ice",
            "website": "https://www.twicetheice.com",
            "phone": "555-0101",
            "contact_name": "Store Manager",
            "contact_email": "manager@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["brand"] == "Twice the Ice"
    assert body["website"] == "https://www.twicetheice.com"
    assert body["phone"] == "555-0101"
    assert body["contact_name"] == "Store Manager"
    assert body["contact_email"] == "manager@example.com"


def test_calendar_link_for_competitor_with_follow_up(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post(
        "/competitors",
        json={
            "address": "456 Rival Ave, Denver, CO",
            "name": "Twice the Ice",
            "follow_up_at": "2026-08-05T15:00:00Z",
        },
        headers=headers,
    )
    competitor_id = create.json()["id"]

    response = client.get(f"/competitors/{competitor_id}/calendar-link", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["google"].startswith("https://calendar.google.com/calendar/render?")
    assert "20260805T150000Z" in body["google"]
    assert body["outlook"].startswith("https://outlook.live.com/calendar/0/deeplink/compose?")


def test_calendar_link_without_follow_up_is_conflict(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post(
        "/competitors", json={"address": "456 Rival Ave", "name": "Twice the Ice"}, headers=headers
    )
    competitor_id = create.json()["id"]

    response = client.get(f"/competitors/{competitor_id}/calendar-link", headers=headers)
    assert response.status_code == 409
