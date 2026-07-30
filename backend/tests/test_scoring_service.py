import uuid

from app.core.models.competitor import Competitor
from app.core.models.geography import City, County, State
from app.core.models.location import Location
from app.services import scoring_service


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


def _make_competitor(db, state, county, city, lat, lon, serves_ice=False, serves_water=False):
    competitor = Competitor(
        id=uuid.uuid4(),
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        address="test address",
        latitude=lat,
        longitude=lon,
        name="Test Rival",
        serves_ice=serves_ice,
        serves_water=serves_water,
    )
    db.add(competitor)
    db.flush()
    return competitor


def _make_location(db, state, county, city, lat, lon, serves_ice=False, serves_water=False):
    location = Location(
        id=uuid.uuid4(),
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        zip_code="80202",
        address="test prospect address",
        latitude=lat,
        longitude=lon,
        serves_ice=serves_ice,
        serves_water=serves_water,
    )
    db.add(location)
    db.flush()
    return location


def test_haversine_zero_distance():
    assert scoring_service.haversine_miles(39.7392, -104.9903, 39.7392, -104.9903) == 0.0


def test_haversine_known_distance_denver_boulder():
    # Denver to Boulder, CO is roughly 25 miles.
    distance = scoring_service.haversine_miles(39.7392, -104.9903, 40.0150, -105.2705)
    assert 20 < distance < 30


def test_competition_score_zero_with_no_competitors(db_session):
    score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903)
    assert score == 0.0


def test_competition_score_increases_with_closer_competitors(db_session):
    state, county, city = _seed_geography(db_session)
    _make_competitor(db_session, state, county, city, 39.7392, -104.9903)  # same spot
    close_score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903)
    assert close_score > 0

    db_session.query(Competitor).delete()
    db_session.flush()
    _make_competitor(db_session, state, county, city, 39.85, -105.05)  # several miles away
    far_score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903)
    assert 0 < far_score < close_score


def test_competition_score_ignores_far_away_competitors(db_session):
    state, county, city = _seed_geography(db_session)
    _make_competitor(db_session, state, county, city, 45.0, -110.0)  # far outside the radius
    score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903)
    assert score == 0.0


def test_opportunity_score_none_without_both_ratings():
    assert scoring_service.calculate_opportunity_score(None, None, 0.0) is None
    assert scoring_service.calculate_opportunity_score(8, None, 0.0) is None
    assert scoring_service.calculate_opportunity_score(None, 7.0, 0.0) is None


def test_opportunity_score_computed_with_both_ratings():
    score = scoring_service.calculate_opportunity_score(10, 10, 0.0)
    assert score == 100.0

    score_with_competition = scoring_service.calculate_opportunity_score(10, 10, 100.0)
    assert score_with_competition < score


def test_confidence_score_reflects_input_completeness():
    assert scoring_service.calculate_confidence_score(None, None) == 0.0
    assert scoring_service.calculate_confidence_score(5, None) == 50.0
    assert scoring_service.calculate_confidence_score(None, 5.0) == 50.0
    assert scoring_service.calculate_confidence_score(5, 5.0) == 100.0


def test_competition_score_counts_everything_when_location_capability_unset(db_session):
    """A brand-new, unconfigured prospect (serves_ice=serves_water=False)
    still counts every nearby competitor, regardless of what they serve
    -- narrowing only kicks in once the location has actually declared
    a capability (ADR-0017).
    """
    state, county, city = _seed_geography(db_session)
    _make_competitor(db_session, state, county, city, 39.7392, -104.9903, serves_water=True)
    score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903, False, False)
    assert score > 0


def test_competition_score_narrows_to_matching_product_once_declared(db_session):
    state, county, city = _seed_geography(db_session)
    # A few miles out each, so neither alone saturates the 0-100 cap --
    # otherwise "both > ice_only" couldn't show a real difference.
    _make_competitor(db_session, state, county, city, 39.78, -104.95, serves_ice=True)
    _make_competitor(db_session, state, county, city, 39.70, -105.03, serves_water=True)

    ice_only_score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903, True, False)
    both_scores = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903, True, True)

    # Only the ice competitor should count for an ice-only location --
    # the water-only rival isn't real competition for it.
    assert ice_only_score > 0
    # Declaring both capabilities picks up the water competitor too, so
    # the combined score is strictly higher than the ice-only narrowing.
    assert both_scores > ice_only_score


def test_competition_score_excludes_non_overlapping_competitor_entirely(db_session):
    state, county, city = _seed_geography(db_session)
    _make_competitor(db_session, state, county, city, 39.7392, -104.9903, serves_water=True)
    score = scoring_service.calculate_competition_score(db_session, 39.7392, -104.9903, True, False)
    assert score == 0.0


def test_recalculate_scores_near_updates_locations_within_radius(db_session):
    state, county, city = _seed_geography(db_session)
    near = _make_location(db_session, state, county, city, 39.7392, -104.9903, serves_ice=True)
    far = _make_location(db_session, state, county, city, 45.0, -110.0, serves_ice=True)
    db_session.commit()

    _make_competitor(db_session, state, county, city, 39.7392, -104.9903, serves_ice=True)
    db_session.commit()
    scoring_service.recalculate_scores_near(db_session, 39.7392, -104.9903)
    db_session.refresh(near)
    db_session.refresh(far)
    assert near.competition_score is not None and near.competition_score > 0
    assert far.competition_score is None  # outside the radius, never touched
