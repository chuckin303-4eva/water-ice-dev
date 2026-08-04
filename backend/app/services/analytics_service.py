"""Aggregate analytics over locations, competitors, and opportunities
(ADR-0021, Phase 4).

Location/competitor/demographic aggregates are platform-wide (ADR-0002:
locations are shared market intelligence, not per-tenant data) -- every
organization sees the same portfolio-level numbers. The pipeline funnel
is the one org-scoped piece, since `opportunities` tracks a specific
organization's pursuit of a location.

Pure aggregation over data already collected by Phases 1-3 (scoring,
Market Refresh demographics, competitor tracking) -- no new external
calls, no new cost.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models.competitor import Competitor
from app.core.models.geography import City, State
from app.core.models.location import Location
from app.core.models.opportunity import Opportunity

_SCORE_BUCKETS = (("0-25", 0, 25), ("25-50", 25, 50), ("50-75", 50, 75), ("75-100", 75, 100))
_STAGES = ("identified", "contacted", "negotiating", "won", "lost")
_TOP_N = 10


def _location_rows(db: Session):
    """Base query joining in the denormalized city/state display fields
    every row needs -- avoids an N+1 lookup per result row.
    """
    return db.query(Location, City.name, State.code).join(City, Location.city_id == City.id).join(
        State, Location.state_id == State.id
    )


def _to_row_dicts(rows) -> list[dict]:
    return [
        {
            "id": location.id,
            "address": location.address,
            "city_name": city_name,
            "state_code": state_code,
            "opportunity_score": location.opportunity_score,
            "competition_score": location.competition_score,
            "growth_rate": location.growth_rate,
            "population": location.population,
        }
        for location, city_name, state_code in rows
    ]


def status_breakdown(db: Session) -> dict[str, int]:
    rows = db.query(Location.status, func.count(Location.id)).group_by(Location.status).all()
    return {status: count for status, count in rows}


def score_distribution(db: Session) -> tuple[float | None, int, dict[str, int]]:
    """Returns (average_opportunity_score, unscored_count, bucket_counts)."""
    average = db.query(func.avg(Location.opportunity_score)).filter(
        Location.opportunity_score.isnot(None)
    ).scalar()
    unscored_count = db.query(func.count(Location.id)).filter(Location.opportunity_score.is_(None)).scalar()
    buckets: dict[str, int] = {}
    for label, low, high in _SCORE_BUCKETS:
        query = db.query(func.count(Location.id)).filter(Location.opportunity_score >= low)
        query = query.filter(Location.opportunity_score <= high if high == 100 else Location.opportunity_score < high)
        buckets[label] = query.scalar()
    return (float(average) if average is not None else None, unscored_count, buckets)


def top_prospects(db: Session, limit: int = _TOP_N) -> list[dict]:
    rows = (
        _location_rows(db)
        .filter(Location.opportunity_score.isnot(None), Location.status == "prospect")
        .order_by(Location.opportunity_score.desc())
        .limit(limit)
        .all()
    )
    return _to_row_dicts(rows)


def growth_markets(db: Session, limit: int = _TOP_N) -> list[dict]:
    rows = (
        _location_rows(db)
        .filter(Location.growth_rate.isnot(None))
        .order_by(Location.growth_rate.desc())
        .limit(limit)
        .all()
    )
    return _to_row_dicts(rows)


def most_contested_markets(db: Session, limit: int = _TOP_N) -> list[dict]:
    rows = (
        _location_rows(db)
        .filter(Location.competition_score.isnot(None))
        .order_by(Location.competition_score.desc())
        .limit(limit)
        .all()
    )
    return _to_row_dicts(rows)


def competitor_landscape(db: Session) -> tuple[int, float | None]:
    """Returns (total_competitors, average_competition_score)."""
    total = db.query(func.count(Competitor.id)).scalar()
    average = db.query(func.avg(Location.competition_score)).filter(
        Location.competition_score.isnot(None)
    ).scalar()
    return (total, float(average) if average is not None else None)


def pipeline_funnel(db: Session, organization_id: int) -> dict[str, int]:
    rows = (
        db.query(Opportunity.stage, func.count(Opportunity.id))
        .filter(Opportunity.organization_id == organization_id)
        .group_by(Opportunity.stage)
        .all()
    )
    counts = dict.fromkeys(_STAGES, 0)
    counts.update({stage: count for stage, count in rows})
    return counts
