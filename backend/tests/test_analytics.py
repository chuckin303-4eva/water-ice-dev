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


def test_status_breakdown_and_totals(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    client.post("/locations", json={"address": "A"}, headers=headers)
    scored = client.post(
        "/locations", json={"address": "B", "visibility_rating": 5, "traffic_score": 5}, headers=headers
    ).json()
    client.put(f"/locations/{scored['id']}", json={"status": "active"}, headers=headers)

    response = client.get("/analytics/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_locations"] == 2
    assert body["status_breakdown"]["prospect"] == 1
    assert body["status_breakdown"]["active"] == 1


def test_score_distribution(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    client.post("/locations", json={"address": "Unscored"}, headers=headers)
    client.post(
        "/locations", json={"address": "Low", "visibility_rating": 2, "traffic_score": 2}, headers=headers
    )
    client.post(
        "/locations", json={"address": "High", "visibility_rating": 10, "traffic_score": 10}, headers=headers
    )

    body = client.get("/analytics/summary", headers=headers).json()
    assert body["unscored_count"] == 1
    assert body["average_opportunity_score"] is not None
    assert body["score_buckets"]["75-100"] >= 1
    assert sum(body["score_buckets"].values()) == 2


def test_top_prospects_only_includes_scored_prospects(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    won = client.post(
        "/locations", json={"address": "Won deal", "visibility_rating": 10, "traffic_score": 10}, headers=headers
    ).json()
    client.put(f"/locations/{won['id']}", json={"status": "active"}, headers=headers)
    prospect = client.post(
        "/locations", json={"address": "Good prospect", "visibility_rating": 9, "traffic_score": 9}, headers=headers
    ).json()

    body = client.get("/analytics/summary", headers=headers).json()
    top_ids = [row["id"] for row in body["top_prospects"]]
    assert prospect["id"] in top_ids
    assert won["id"] not in top_ids


def test_growth_markets_only_includes_locations_with_growth_rate(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    no_growth = client.post("/locations", json={"address": "No data"}, headers=headers).json()
    growing = client.post("/locations", json={"address": "Growing"}, headers=headers).json()
    client.put(f"/locations/{growing['id']}", json={"growth_rate": 12.5}, headers=headers)

    body = client.get("/analytics/summary", headers=headers).json()
    growth_ids = [row["id"] for row in body["growth_markets"]]
    assert growing["id"] in growth_ids
    assert no_growth["id"] not in growth_ids
    assert body["growth_markets"][0]["growth_rate"] == 12.5


def test_competitor_landscape(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    client.post("/locations", json={"address": "Near competitor"}, headers=headers)
    client.post(
        "/competitors",
        json={"name": "Ice Co", "address": "Nearby", "serves_ice": True},
        headers=headers,
    )

    body = client.get("/analytics/summary", headers=headers).json()
    assert body["total_competitors"] == 1
    assert body["average_competition_score"] is not None


def test_pipeline_funnel_scoped_to_own_organization(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = client.post("/locations", json={"address": "Pursuit target"}, headers=headers).json()
    opp = client.post("/opportunities", json={"location_id": location["id"]}, headers=headers).json()
    client.put(f"/opportunities/{opp['id']}", json={"stage": "negotiating"}, headers=headers)

    other_headers = _register(client, "Other Org", "otheranalytics@example.com")
    other_location = client.post("/locations", json={"address": "Other pursuit"}, headers=other_headers).json()
    client.post("/opportunities", json={"location_id": other_location["id"]}, headers=other_headers)

    mine = client.get("/analytics/summary", headers=headers).json()
    assert mine["pipeline_funnel"]["negotiating"] == 1
    assert mine["pipeline_funnel"]["identified"] == 0

    theirs = client.get("/analytics/summary", headers=other_headers).json()
    assert theirs["pipeline_funnel"]["identified"] == 1
    assert theirs["pipeline_funnel"]["negotiating"] == 0


def test_analytics_visible_to_non_admin_member(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.get("/analytics/summary", headers=headers)
    assert response.status_code == 200
