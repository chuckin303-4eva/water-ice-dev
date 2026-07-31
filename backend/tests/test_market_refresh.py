import uuid
from datetime import UTC, datetime

import pytest

from app.api.schemas.location import LocationUpdateRequest
from app.core.models.geography import City, County, State
from app.core.models.location import Location
from app.core.models.validation_queue import ValidationQueue
from app.services import census_service, geocoding_service, market_refresh_service, validation_service
from app.services.census_service import CensusDemographics, CensusGeography
from app.services.geocoding_service import GeocodeResult
from app.services.market_refresh_providers import CensusProvider, LocationSnapshot, OpenStreetMapProvider
from tests.conftest import auth_headers

_FAKE_GEOCODE = GeocodeResult(
    latitude=39.7392,
    longitude=-104.9903,
    address="1 Main St, Denver, CO 80202",
    city_name="Denver",
    county_name="Denver",
    state_code="CO",
    zip_code="80202",
)


@pytest.fixture(autouse=True)
def _mock_geocoding(monkeypatch):
    monkeypatch.setattr(geocoding_service, "geocode_address", lambda address: _FAKE_GEOCODE)


def _seed_geography(db):
    state = State(code="CO", name="Colorado")
    db.add(state)
    db.flush()
    county = County(state_id=state.id, name="Denver")
    db.add(county)
    db.flush()
    city = City(state_id=state.id, county_id=county.id, name="Denver")
    db.add(city)
    db.flush()
    return state, county, city


def _make_location(db, state, county, city, **overrides):
    defaults = dict(
        id=uuid.uuid4(),
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        zip_code="80202",
        address="1 Main St, Denver, CO",
        latitude=39.7392,
        longitude=-104.9903,
    )
    defaults.update(overrides)
    location = Location(**defaults)
    db.add(location)
    db.flush()
    return location


def _register(client, org_name: str, email: str, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/register", json={"organization_name": org_name, "email": email, "password": password}
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


def _unreachable_geocoding(monkeypatch):
    def raise_geocoding_error(lat, lon):
        raise geocoding_service.GeocodingError("unreachable in this test")

    def raise_census_error(lat, lon):
        raise census_service.CensusLookupError("unreachable in this test")

    monkeypatch.setattr(geocoding_service, "reverse_geocode", raise_geocoding_error)
    monkeypatch.setattr(census_service, "geocode_to_tract", raise_census_error)


# ---------------------------------------------------------------------------
# OpenStreetMapProvider
# ---------------------------------------------------------------------------


def test_osm_provider_flags_address_drift(monkeypatch):
    monkeypatch.setattr(
        geocoding_service,
        "reverse_geocode",
        lambda lat, lon: GeocodeResult(
            latitude=lat,
            longitude=lon,
            address="456 New Address, Denver, CO",
            city_name="Denver",
            county_name="Denver",
            state_code="CO",
            zip_code="80202",
        ),
    )
    snapshot = LocationSnapshot(
        id="x", address="1 Main St, Denver, CO", latitude=39.7392, longitude=-104.9903,
        population=None, median_income=None, growth_rate=None,
    )
    observations = OpenStreetMapProvider().check_location(snapshot)
    assert len(observations) == 1
    assert observations[0].field_name == "address"
    assert observations[0].observed_value == "456 New Address, Denver, CO"
    assert observations[0].source == "openstreetmap"


def test_osm_provider_silent_when_address_matches(monkeypatch):
    monkeypatch.setattr(
        geocoding_service,
        "reverse_geocode",
        lambda lat, lon: GeocodeResult(
            latitude=lat, longitude=lon, address="1 Main St, Denver, CO",
            city_name="Denver", county_name="Denver", state_code="CO", zip_code="80202",
        ),
    )
    # Case/whitespace differences shouldn't count as drift.
    snapshot = LocationSnapshot(
        id="x", address="1   MAIN st, denver, co", latitude=39.7392, longitude=-104.9903,
        population=None, median_income=None, growth_rate=None,
    )
    assert OpenStreetMapProvider().check_location(snapshot) == []


def test_osm_provider_swallows_geocoding_errors(monkeypatch):
    def raise_error(lat, lon):
        raise geocoding_service.GeocodingError("nope")

    monkeypatch.setattr(geocoding_service, "reverse_geocode", raise_error)
    snapshot = LocationSnapshot(
        id="x", address="1 Main St", latitude=0, longitude=0,
        population=None, median_income=None, growth_rate=None,
    )
    assert OpenStreetMapProvider().check_location(snapshot) == []


# ---------------------------------------------------------------------------
# CensusProvider
# ---------------------------------------------------------------------------


def test_census_provider_flags_changed_demographics(monkeypatch):
    monkeypatch.setattr(census_service, "geocode_to_tract", lambda lat, lon: CensusGeography("08", "031", "003200"))
    monkeypatch.setattr(
        census_service,
        "get_demographics",
        lambda geo: CensusDemographics(population=5000, median_income=60000.0, growth_rate=2.5),
    )
    snapshot = LocationSnapshot(
        id="x", address="1 Main St", latitude=39.7392, longitude=-104.9903,
        population=None, median_income=None, growth_rate=None,
    )
    observations = CensusProvider().check_location(snapshot)
    fields = {o.field_name: o.observed_value for o in observations}
    assert fields == {"population": 5000, "median_income": 60000.0, "growth_rate": 2.5}
    assert all(o.source == "census" for o in observations)


def test_census_provider_silent_when_unchanged(monkeypatch):
    monkeypatch.setattr(census_service, "geocode_to_tract", lambda lat, lon: CensusGeography("08", "031", "003200"))
    monkeypatch.setattr(
        census_service,
        "get_demographics",
        lambda geo: CensusDemographics(population=5000, median_income=60000.0, growth_rate=2.5),
    )
    snapshot = LocationSnapshot(
        id="x", address="1 Main St", latitude=39.7392, longitude=-104.9903,
        population=5000, median_income=60000.0, growth_rate=2.5,
    )
    assert CensusProvider().check_location(snapshot) == []


def test_census_provider_swallows_lookup_errors(monkeypatch):
    def raise_error(lat, lon):
        raise census_service.CensusLookupError("nope")

    monkeypatch.setattr(census_service, "geocode_to_tract", raise_error)
    snapshot = LocationSnapshot(
        id="x", address="1 Main St", latitude=0, longitude=0,
        population=None, median_income=None, growth_rate=None,
    )
    assert CensusProvider().check_location(snapshot) == []


# ---------------------------------------------------------------------------
# Orchestration (market_refresh_service.run_refresh)
# ---------------------------------------------------------------------------


def test_run_refresh_creates_one_combined_proposal_per_location(db_session, monkeypatch):
    state, county, city = _seed_geography(db_session)
    location = _make_location(db_session, state, county, city)
    db_session.commit()

    monkeypatch.setattr(
        geocoding_service,
        "reverse_geocode",
        lambda lat, lon: GeocodeResult(
            latitude=lat, longitude=lon, address="1 New St, Denver, CO",
            city_name="Denver", county_name="Denver", state_code="CO", zip_code="80202",
        ),
    )
    monkeypatch.setattr(census_service, "geocode_to_tract", lambda lat, lon: CensusGeography("08", "031", "003200"))
    monkeypatch.setattr(
        census_service,
        "get_demographics",
        lambda geo: CensusDemographics(population=5000, median_income=60000.0, growth_rate=2.5),
    )

    run = market_refresh_service.run_refresh(db_session, triggered_by=None)

    assert run.status == "completed"
    assert run.locations_reviewed == 1
    assert run.changes_queued == 1
    assert set(run.providers_used) == {"openstreetmap", "census"}
    assert run.completed_at is not None

    entries = db_session.query(ValidationQueue).all()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.entity_type == "location"
    assert entry.entity_id == str(location.id)
    assert entry.submitted_by is None
    assert entry.status == "pending"
    assert entry.proposed_changes["address"] == "1 New St, Denver, CO"
    assert entry.proposed_changes["population"] == 5000
    assert entry.proposed_changes["median_income"] == 60000.0
    assert entry.proposed_changes["growth_rate"] == 2.5
    assert entry.reason  # a human-readable explanation was set

    db_session.refresh(location)
    assert location.last_verified_at is not None
    assert location.verification_source == "openstreetmap,census"


def test_run_refresh_queues_nothing_when_no_drift_found(db_session, monkeypatch):
    state, county, city = _seed_geography(db_session)
    _make_location(db_session, state, county, city)
    db_session.commit()
    _unreachable_geocoding(monkeypatch)  # providers swallow these and return []

    run = market_refresh_service.run_refresh(db_session, triggered_by=None)

    assert run.status == "completed"
    assert run.locations_reviewed == 1
    assert run.changes_queued == 0
    assert db_session.query(ValidationQueue).count() == 0


def test_run_refresh_skips_archived_locations(db_session, monkeypatch):
    state, county, city = _seed_geography(db_session)
    _make_location(db_session, state, county, city, status="archived")
    db_session.commit()
    _unreachable_geocoding(monkeypatch)

    run = market_refresh_service.run_refresh(db_session, triggered_by=None)
    assert run.locations_reviewed == 0


def test_run_refresh_prioritizes_never_checked_then_oldest(db_session, monkeypatch):
    state, county, city = _seed_geography(db_session)
    recently_checked = _make_location(
        db_session, state, county, city, address="Recent", last_verified_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    long_ago_checked = _make_location(
        db_session, state, county, city, address="Long ago", last_verified_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    never_checked = _make_location(db_session, state, county, city, address="Never")
    db_session.commit()
    _unreachable_geocoding(monkeypatch)

    run = market_refresh_service.run_refresh(db_session, triggered_by=None, max_locations=2)
    assert run.locations_reviewed == 2

    db_session.refresh(recently_checked)
    db_session.refresh(long_ago_checked)
    db_session.refresh(never_checked)
    # The two oldest (NULL counts as oldest) got processed and now have a
    # fresh last_verified_at; the recently-checked one was left alone.
    # (SQLite drops tzinfo on round-trip, so compare naive here -- a
    # test-DB artifact, not something that happens on the real Postgres
    # backend.)
    assert never_checked.last_verified_at is not None
    assert long_ago_checked.last_verified_at.replace(tzinfo=UTC) > datetime(2020, 1, 1, tzinfo=UTC)
    assert recently_checked.last_verified_at.replace(tzinfo=UTC) == datetime(2026, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Validation-queue integration: system-sourced entries cross organizations
# ---------------------------------------------------------------------------


def test_system_sourced_entries_visible_to_every_org_admin(client, db_session):
    admin_a = _register(client, "Org A", "admina@example.com")
    admin_b = _register(client, "Org B", "adminb@example.com")

    location = client.post("/locations", json={"address": "1 Main St, Denver, CO"}, headers=admin_a).json()
    entry = validation_service.propose_update_location(
        db_session,
        uuid.UUID(location["id"]),
        LocationUpdateRequest(population=5000),
        submitted_by=None,
        reason="US Census population estimate differs from the stored value.",
    )
    db_session.commit()

    for headers in (admin_a, admin_b):
        response = client.get("/validation-queue", headers=headers)
        assert response.status_code == 200
        assert entry.id in [item["id"] for item in response.json()]


def test_member_submitted_entries_stay_scoped_to_their_own_org(client, db_session):
    """The join fix must not accidentally leak a real member's own
    submission to a different organization's admin."""
    admin_a = _register(client, "Org A", "admina2@example.com")
    member_a = _add_member(client, admin_a, "membera2@example.com")
    admin_b = _register(client, "Org B", "adminb2@example.com")

    put_settings = client.put(
        "/organizations/settings", json={"require_review_for_submissions": True}, headers=admin_a
    )
    assert put_settings.status_code == 200
    queued = client.post("/locations", json={"address": "1 Main St, Denver, CO"}, headers=member_a)
    assert queued.status_code == 202

    assert any(item["status"] == "pending" for item in client.get("/validation-queue", headers=admin_a).json())
    assert client.get("/validation-queue", headers=admin_b).json() == []


def test_admin_can_approve_system_sourced_proposal(client, db_session):
    admin_headers = _register(client, "Acme", "admin3@example.com")
    location = client.post(
        "/locations", json={"address": "1 Main St, Denver, CO"}, headers=admin_headers
    ).json()
    entry = validation_service.propose_update_location(
        db_session,
        uuid.UUID(location["id"]),
        LocationUpdateRequest(population=5000),
        submitted_by=None,
        reason="test",
    )
    db_session.commit()

    response = client.post(f"/validation-queue/{entry.id}/approve", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["population"] == 5000


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_market_refresh_routes_are_admin_only(client):
    admin_headers = _register(client, "Acme", "admin4@example.com")
    member_headers = _add_member(client, admin_headers, "member4@example.com")
    assert client.post("/market-refresh/runs", headers=member_headers).status_code == 403
    assert client.get("/market-refresh/runs", headers=member_headers).status_code == 403


def test_trigger_refresh_via_api_returns_run_summary_and_history(client, monkeypatch):
    admin_headers = _register(client, "Acme", "admin5@example.com")
    _unreachable_geocoding(monkeypatch)

    response = client.post("/market-refresh/runs", headers=admin_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert set(body["providers_used"]) == {"openstreetmap", "census"}

    history = client.get("/market-refresh/runs", headers=admin_headers).json()
    assert len(history) == 1
    assert history[0]["id"] == body["id"]
