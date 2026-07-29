from datetime import UTC, datetime

import pytest

from app.core.models.update_log import UpdateLog
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
    """No real network calls in the test suite -- geocoding is tested
    against a live Nominatim call only manually (see the session's
    end-to-end verification), same policy as every other external
    integration in this project.
    """
    monkeypatch.setattr(geocoding_service, "geocode_address", lambda address: _FAKE_GEOCODE)
    monkeypatch.setattr(
        geocoding_service, "reverse_geocode", lambda lat, lon: _FAKE_GEOCODE
    )


def test_create_location_by_address(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["state_code"] == "CO"
    assert body["county_name"] == "Denver"
    assert body["city_name"] == "Denver"
    assert body["zip_code"] == "80202"
    assert body["status"] == "prospect"


def test_create_location_by_coordinates(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations", json={"latitude": 39.7392, "longitude": -104.9903}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["latitude"] == 39.7392
    assert body["longitude"] == -104.9903
    assert body["address"] == _FAKE_GEOCODE.address


def test_create_location_requires_address_or_coordinates(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post("/locations", json={}, headers=headers)
    assert response.status_code == 422


def test_create_location_with_both_keeps_caller_values(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={"address": "My Custom Address", "latitude": 1.0, "longitude": 2.0},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    # caller's own address/coordinates win; geocoding is only consulted
    # for the state/county/city breakdown
    assert body["address"] == "My Custom Address"
    assert body["latitude"] == 1.0
    assert body["longitude"] == 2.0


def test_create_location_with_prospect_fields(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={
            "address": "123 Main St, Denver, CO",
            "property_owner_name": "Jane Landlord",
            "property_owner_phone": "555-0100",
            "expected_unit_size": "10x10 ft",
            "power_company": "Xcel Energy",
            "power_voltage": "208V",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["property_owner_name"] == "Jane Landlord"
    assert body["power_company"] == "Xcel Energy"
    assert body["power_voltage"] == "208V"


def test_geocoding_failure_returns_422(client, test_user: User, monkeypatch) -> None:
    def _raise(address):
        raise geocoding_service.GeocodingError("no result")

    monkeypatch.setattr(geocoding_service, "geocode_address", _raise)
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations", json={"address": "not a real place"}, headers=headers
    )
    assert response.status_code == 422


def test_get_and_list_locations(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]

    get = client.get(f"/locations/{location_id}", headers=headers)
    assert get.status_code == 200

    listing = client.get("/locations", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_get_nonexistent_location_404s(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.get("/locations/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.status_code == 404


def test_update_location_logs_changes(client, test_user: User, db_session) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]

    update = client.put(
        f"/locations/{location_id}",
        json={"power_company": "Xcel Energy", "status": "active"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["power_company"] == "Xcel Energy"
    assert update.json()["status"] == "active"

    logs = (
        db_session.query(UpdateLog)
        .filter(UpdateLog.entity_id == location_id, UpdateLog.field_name == "power_company")
        .all()
    )
    assert len(logs) == 1
    assert logs[0].new_value == "Xcel Energy"
    assert logs[0].old_value is None


def test_archive_location(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]

    delete = client.delete(f"/locations/{location_id}", headers=headers)
    assert delete.status_code == 204

    get = client.get(f"/locations/{location_id}", headers=headers)
    assert get.json()["status"] == "archived"


def test_add_and_list_call_notes(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]

    note = client.post(
        f"/locations/{location_id}/call-notes",
        json={"note_text": "Spoke with owner, interested", "follow_up_at": "2026-08-05T15:00:00Z"},
        headers=headers,
    )
    assert note.status_code == 201
    assert note.json()["note_text"] == "Spoke with owner, interested"

    listing = client.get(f"/locations/{location_id}/call-notes", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_calendar_link_for_note_with_follow_up(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]
    note = client.post(
        f"/locations/{location_id}/call-notes",
        json={"note_text": "Follow up next week", "follow_up_at": "2026-08-05T15:00:00Z"},
        headers=headers,
    )
    note_id = note.json()["id"]

    response = client.get(
        f"/locations/{location_id}/call-notes/{note_id}/calendar-link", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["google"].startswith("https://calendar.google.com/calendar/render?")
    assert "20260805T150000Z" in body["google"]
    assert body["outlook"].startswith("https://outlook.live.com/calendar/0/deeplink/compose?")


def test_calendar_link_without_follow_up_is_conflict(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]
    note = client.post(
        f"/locations/{location_id}/call-notes",
        json={"note_text": "No follow-up needed"},
        headers=headers,
    )
    note_id = note.json()["id"]

    response = client.get(
        f"/locations/{location_id}/call-notes/{note_id}/calendar-link", headers=headers
    )
    assert response.status_code == 409


def test_new_location_has_competition_score_but_no_opportunity_score(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    body = response.json()
    assert body["competition_score"] == 0.0
    assert body["opportunity_score"] is None
    assert body["confidence_score"] == 0.0


def test_location_with_ratings_gets_opportunity_score(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations",
        json={"address": "123 Main St", "visibility_rating": 8, "traffic_score": 7},
        headers=headers,
    )
    body = response.json()
    assert body["visibility_rating"] == 8
    assert body["traffic_score"] == 7
    assert body["opportunity_score"] is not None
    assert body["confidence_score"] == 100.0


def test_visibility_rating_out_of_range_rejected(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations", json={"address": "123 Main St", "visibility_rating": 11}, headers=headers
    )
    assert response.status_code == 422


def test_recalculate_score_picks_up_new_competitor(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    create = client.post("/locations", json={"address": "123 Main St"}, headers=headers)
    location_id = create.json()["id"]
    assert create.json()["competition_score"] == 0.0

    client.post(
        "/competitors",
        json={"address": "456 Rival Ave", "name": "Rival Ice", "latitude": 39.7392, "longitude": -104.9903},
        headers=headers,
    )

    recalculated = client.post(f"/locations/{location_id}/recalculate-score", headers=headers)
    assert recalculated.status_code == 200
    assert recalculated.json()["competition_score"] > 0
