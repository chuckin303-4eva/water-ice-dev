"""Market Refresh Engine orchestration (ADR-0004, implemented ADR-0020).

Refresh -> Compare -> Create validation_queue entries -> human approval
-> update locations -> write update_log. A run never writes to
`locations` directly (except the housekeeping `last_verified_at`/
`verification_source` fields) -- matching ADR-0004's design exactly.

In-process and synchronous, no new infrastructure (no Redis/job queue) --
same "don't build infra ahead of a validated need" default already
applied to CSV import (ADR-0011) and billing (ADR-0019). A run is
bounded to MAX_LOCATIONS_PER_RUN so a single request has a predictable
worst-case duration (each location can cost up to ~4 external HTTP
calls -- one Nominatim reverse-geocode, one Census geocode, two ACS
lookups -- so 20 locations is tens of seconds, not instant, by design).
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.location import LocationUpdateRequest
from app.core.models.location import Location
from app.core.models.refresh_run import RefreshRun
from app.services import validation_service
from app.services.market_refresh_providers import PROVIDERS, snapshot_from_location

MAX_LOCATIONS_PER_RUN = 20

_FIELD_LABELS = {
    "address": "OpenStreetMap re-geocoding found a different address than what's stored.",
    "population": "US Census population estimate differs from the stored value.",
    "median_income": "US Census median household income estimate differs from the stored value.",
    "growth_rate": "US Census-derived population growth rate differs from the stored value.",
}


def _select_locations(db: Session, limit: int) -> list[Location]:
    """Oldest `last_verified_at` first (never-checked locations, where
    it's NULL, come first) per ADR-0004, so a full sweep across every
    location happens gradually over multiple runs instead of always
    re-checking the same handful.
    """
    return (
        db.query(Location)
        .filter(Location.status != "archived")
        .order_by(Location.last_verified_at.asc().nulls_first())
        .limit(limit)
        .all()
    )


def run_refresh(db: Session, triggered_by: int, max_locations: int = MAX_LOCATIONS_PER_RUN) -> RefreshRun:
    run = RefreshRun(
        status="running", triggered_by=triggered_by, providers_used=[p.slug for p in PROVIDERS]
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    locations = _select_locations(db, max_locations)
    changes_queued = 0
    locations_reviewed = 0
    try:
        for location in locations:
            snapshot = snapshot_from_location(location)
            changes: dict[str, object] = {}
            reasons: list[str] = []
            for provider in PROVIDERS:
                for obs in provider.check_location(snapshot):
                    changes[obs.field_name] = obs.observed_value
                    label = _FIELD_LABELS.get(obs.field_name, f"{obs.source} observed a different value.")
                    if label not in reasons:
                        reasons.append(label)

            # One combined proposal per location, not one per field --
            # a reviewer sees a single card with everything that
            # changed, not N separate cards for the same location.
            if changes:
                update = LocationUpdateRequest(**changes)
                validation_service.propose_update_location(
                    db, location.id, update, submitted_by=None, reason=" ".join(reasons)
                )
                changes_queued += 1

            location.last_verified_at = datetime.now(UTC)
            location.verification_source = ",".join(p.slug for p in PROVIDERS)
            db.commit()
            locations_reviewed += 1
        run.status = "completed"
    except Exception as exc:  # noqa: BLE001 -- a run recording its own failure, not swallowing it
        run.status = "failed"
        run.error_message = str(exc)[:1000]

    run.completed_at = datetime.now(UTC)
    run.locations_reviewed = locations_reviewed
    run.changes_queued = changes_queued
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session) -> list[RefreshRun]:
    return db.query(RefreshRun).order_by(RefreshRun.started_at.desc()).all()
