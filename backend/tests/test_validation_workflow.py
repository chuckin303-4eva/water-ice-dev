import pytest

from app.services import geocoding_service
from app.services.geocoding_service import GeocodeResult

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
    from app.services import csv_import_service

    monkeypatch.setattr(csv_import_service.time, "sleep", lambda seconds: None)


def _register(client, org_name: str, email: str, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"organization_name": org_name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _add_member(client, admin_headers, email: str, password: str = "password123") -> dict[str, str]:
    create = client.post(
        "/organizations/users",
        json={"email": email, "password": password, "role": "member"},
        headers=admin_headers,
    )
    assert create.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _enable_review(client, admin_headers) -> None:
    response = client.put(
        "/organizations/settings", json={"require_review_for_submissions": True}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["require_review_for_submissions"] is True


def test_settings_default_off(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.get("/organizations/settings", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["require_review_for_submissions"] is False


def test_member_create_applies_directly_when_review_not_required(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")

    response = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    assert response.status_code == 201
    assert "id" in response.json()

    listing = client.get("/locations", headers=member_headers)
    assert len(listing.json()) == 1


def test_member_create_is_queued_when_review_required(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    response = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["submitted_by_email"] == "member@acme.com"

    # Nothing was actually created yet.
    listing = client.get("/locations", headers=member_headers)
    assert len(listing.json()) == 0


def test_admin_create_bypasses_review_even_when_required(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    _enable_review(client, admin_headers)

    response = client.post("/locations", json={"address": "123 Main St"}, headers=admin_headers)
    assert response.status_code == 201
    assert "id" in response.json()


def test_admin_can_approve_a_queued_creation(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    submit = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    entry_id = submit.json()["id"]

    approve = client.post(f"/validation-queue/{entry_id}/approve", headers=admin_headers)
    assert approve.status_code == 200
    assert approve.json()["address"] == "123 Main St"

    listing = client.get("/locations", headers=admin_headers)
    assert len(listing.json()) == 1


def test_admin_can_reject_a_queued_creation(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    submit = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    entry_id = submit.json()["id"]

    reject = client.post(
        f"/validation-queue/{entry_id}/reject",
        json={"reason": "duplicate of an existing site"},
        headers=admin_headers,
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"
    assert reject.json()["reason"] == "duplicate of an existing site"

    listing = client.get("/locations", headers=admin_headers)
    assert len(listing.json()) == 0


def test_cannot_review_the_same_entry_twice(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    submit = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    entry_id = submit.json()["id"]
    client.post(f"/validation-queue/{entry_id}/approve", headers=admin_headers)

    second_attempt = client.post(f"/validation-queue/{entry_id}/approve", headers=admin_headers)
    assert second_attempt.status_code == 409


def test_member_update_is_queued_and_approval_applies_it(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    create = client.post("/locations", json={"address": "123 Main St"}, headers=admin_headers)
    location_id = create.json()["id"]
    _enable_review(client, admin_headers)

    propose = client.put(
        f"/locations/{location_id}", json={"notes": "spoke with owner"}, headers=member_headers
    )
    assert propose.status_code == 202
    assert propose.json()["entity_id"] == location_id

    # Not applied yet.
    unchanged = client.get(f"/locations/{location_id}", headers=admin_headers)
    assert unchanged.json()["notes"] is None

    entry_id = propose.json()["id"]
    approved = client.post(f"/validation-queue/{entry_id}/approve", headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["notes"] == "spoke with owner"


def test_non_admin_cannot_list_or_review_the_queue(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    submit = client.post("/locations", json={"address": "123 Main St"}, headers=member_headers)
    entry_id = submit.json()["id"]

    assert client.get("/validation-queue", headers=member_headers).status_code == 403
    assert client.post(f"/validation-queue/{entry_id}/approve", headers=member_headers).status_code == 403


def test_queue_is_scoped_to_organization(client) -> None:
    acme_admin = _register(client, "Acme", "admin@acme.com")
    acme_member = _add_member(client, acme_admin, "member@acme.com")
    _enable_review(client, acme_admin)
    submit = client.post("/locations", json={"address": "123 Main St"}, headers=acme_member)
    entry_id = submit.json()["id"]

    widgets_admin = _register(client, "Widgets Inc", "admin@widgets.com")

    # Widgets' admin can't see or act on Acme's queue entry.
    listing = client.get("/validation-queue", headers=widgets_admin)
    assert listing.json() == []
    approve = client.post(f"/validation-queue/{entry_id}/approve", headers=widgets_admin)
    assert approve.status_code == 404


def test_csv_import_queues_rows_for_member_when_review_required(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")
    _enable_review(client, admin_headers)

    csv_content = "address\n123 Main St\n456 Oak Ave\n"
    response = client.post(
        "/locations/import",
        files={"file": ("locations.csv", csv_content.encode(), "text/csv")},
        headers=member_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 0
    assert body["queued"] == 2

    assert len(client.get("/locations", headers=admin_headers).json()) == 0
    assert len(client.get("/validation-queue", headers=admin_headers).json()) == 2


def test_csv_import_by_admin_still_creates_directly_when_review_required(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    _enable_review(client, admin_headers)

    csv_content = "address\n123 Main St\n"
    response = client.post(
        "/locations/import",
        files={"file": ("locations.csv", csv_content.encode(), "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["queued"] == 0
