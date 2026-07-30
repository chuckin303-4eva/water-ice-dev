"""Basic scoring (Phase 1, item 6; ADR-0009) and its refinement
(Phase 2, "Opportunity scoring (refined)"; ADR-0017).

Computes three of the five score-shaped columns already on `locations`
(designed in ADR-0003, unused until now):

- `competition_score`: real and automatic. Distance-weighted density of
  rows in `competitors` near this location -- app-level haversine, no
  PostGIS, per ADR-0002. Works even with zero nearby competitors (score
  0 is a real, confident answer: "no visible competition here").
  **Product-aware (ADR-0017)**: once a location has declared at least
  one capability (serves_ice/serves_water), only competitors sharing at
  least one of those capabilities count -- a water-only rival isn't
  real competition for an ice-only site. Same opt-in-narrowing rule
  already used for filters (ADR-0010): a location with neither
  capability set yet (a brand-new, unconfigured prospect) still counts
  every nearby competitor, unnarrowed, so a fresh prospect doesn't
  silently score as "no competition" just because nobody has filled in
  what it serves yet.
- `opportunity_score`: real, but requires input. A composite of
  `competition_score` plus `visibility_rating` and `traffic_score` --
  both manually-entered 1-10 ratings (ADR-0009; these two columns
  existed since Phase 1 with no defined scale or API exposure until
  now). Deliberately `None` until both ratings are set -- guessing a
  score from missing inputs would misrepresent confidence.
- `confidence_score`: how much of `opportunity_score`'s input is
  actually present (0/50/100), not a measure of the site itself.

`population`/`median_income`/`growth_rate` are NOT used here -- no free
demographic data source has been wired (that's the Market Refresh
Engine, ADR-0004, Phase 3). Leaving them out of the formula rather than
defaulting them to zero, which would silently bias every score low.

**Reactive recalculation (ADR-0017)**: `recalculate_scores_near` is
called by `competitor_service` after every competitor create/update/
delete, so a location's score doesn't go silently stale the way
ADR-0009 originally accepted as a known limitation -- creating or
moving a competitor near an already-scored location now updates that
location automatically, not just on its own next edit or a manual
`POST /locations/{id}/recalculate-score` call (which still exists for
any residual edge case).
"""

import math

from sqlalchemy.orm import Session

from app.core.models.competitor import Competitor
from app.core.models.location import Location

# Competitors farther than this don't meaningfully affect the score --
# keeps the query bounded and the result explainable.
COMPETITION_RADIUS_MILES = 10.0
EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _shares_a_product(serves_ice: bool, serves_water: bool, competitor: Competitor) -> bool:
    return (serves_ice and competitor.serves_ice) or (serves_water and competitor.serves_water)


def calculate_competition_score(
    db: Session, latitude: float, longitude: float, serves_ice: bool = False, serves_water: bool = False
) -> float:
    """0-100, higher = more nearby competition. Each qualifying
    competitor within COMPETITION_RADIUS_MILES contributes
    100/(1+distance) -- close competitors weigh heavily, distant ones
    taper off -- summed and capped at 100. See module docstring for the
    product-overlap narrowing rule.
    """
    # Coarse bounding box first (cheap, index-friendly per ADR-0002),
    # then exact haversine distance on the smaller candidate set.
    degree_pad = COMPETITION_RADIUS_MILES / 69.0  # ~69 miles per degree latitude
    candidates = (
        db.query(Competitor)
        .filter(
            Competitor.latitude.between(latitude - degree_pad, latitude + degree_pad),
            Competitor.longitude.between(longitude - degree_pad, longitude + degree_pad),
        )
        .all()
    )

    narrow_by_product = serves_ice or serves_water
    score = 0.0
    for competitor in candidates:
        if narrow_by_product and not _shares_a_product(serves_ice, serves_water, competitor):
            continue
        distance = haversine_miles(latitude, longitude, float(competitor.latitude), float(competitor.longitude))
        if distance <= COMPETITION_RADIUS_MILES:
            score += 100.0 / (1.0 + distance)
    return min(100.0, round(score, 3))


def calculate_opportunity_score(
    visibility_rating: int | None, traffic_score: float | None, competition_score: float
) -> float | None:
    """0-100, higher = better opportunity. None until both manual
    ratings are set -- see module docstring.
    """
    if visibility_rating is None or traffic_score is None:
        return None
    visibility_normalized = (visibility_rating / 10.0) * 100.0
    traffic_normalized = (float(traffic_score) / 10.0) * 100.0
    score = 0.35 * visibility_normalized + 0.35 * traffic_normalized + 0.30 * (100.0 - competition_score)
    return round(max(0.0, min(100.0, score)), 3)


def calculate_confidence_score(visibility_rating: int | None, traffic_score: float | None) -> float:
    """Confidence in opportunity_score's inputs, not in the site itself.
    0 if neither manual rating is set, 50 if one is, 100 if both are.
    """
    present = sum(1 for v in (visibility_rating, traffic_score) if v is not None)
    return {0: 0.0, 1: 50.0, 2: 100.0}[present]


def recalculate_scores(db: Session, location: Location) -> None:
    """Recomputes and persists all three scores for one location.
    Called after any create/update of the location itself, after any
    nearby competitor write (ADR-0017, via recalculate_scores_near),
    and available standalone (POST /locations/{id}/recalculate-score)
    for any residual edge case.
    """
    competition_score = calculate_competition_score(
        db, float(location.latitude), float(location.longitude), location.serves_ice, location.serves_water
    )
    opportunity_score = calculate_opportunity_score(
        location.visibility_rating, location.traffic_score, competition_score
    )
    confidence_score = calculate_confidence_score(location.visibility_rating, location.traffic_score)

    location.competition_score = competition_score
    location.opportunity_score = opportunity_score
    location.confidence_score = confidence_score
    db.commit()
    db.refresh(location)


def recalculate_scores_near(db: Session, latitude: float, longitude: float) -> None:
    """Recomputes every location within COMPETITION_RADIUS_MILES of the
    given point -- called after a competitor is created, updated, or
    deleted (ADR-0017), since any of those can change a nearby
    location's competition_score/opportunity_score. Same bounding-box
    pre-filter as calculate_competition_score, just inverted (locations
    near a competitor instead of competitors near a location).
    """
    degree_pad = COMPETITION_RADIUS_MILES / 69.0
    candidates = (
        db.query(Location)
        .filter(
            Location.latitude.between(latitude - degree_pad, latitude + degree_pad),
            Location.longitude.between(longitude - degree_pad, longitude + degree_pad),
        )
        .all()
    )
    for location in candidates:
        distance = haversine_miles(latitude, longitude, float(location.latitude), float(location.longitude))
        if distance <= COMPETITION_RADIUS_MILES:
            recalculate_scores(db, location)
