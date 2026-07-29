import uuid

from app.core.models.competitor import Competitor
from app.core.models.geography import City, County, State
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


def _make_competitor(db, state, county, city, lat, lon):
    competitor = Competitor(
        id=uuid.uuid4(),
        state_id=state.id,
        county_id=county.id,
        city_id=city.id,
        address="test address",
        latitude=lat,
        longitude=lon,
        name="Test Rival",
    )
    db.add(competitor)
    db.flush()
    return competitor


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
