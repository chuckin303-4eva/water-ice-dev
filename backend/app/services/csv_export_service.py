"""CSV export for locations and competitors (Phase 1, item 10; ADR-0013).

Unlike import (ADR-0011), export needs no geocoding and no rate-limit
delay -- it's a straight read of whatever's already in the database, so
it's synchronous and fast regardless of row count. Exports the full
field set (not the minimal import columns) since this is a portability/
backup operation, not a manual-entry form -- more data is strictly
better here. Reuses each entity's existing `assemble_response` so the
exported columns can never drift from what the API itself considers a
location/competitor's full shape.
"""

import csv
import io

from sqlalchemy.orm import Session

from app.api.schemas.competitor import CompetitorResponse
from app.api.schemas.location import LocationResponse
from app.services import competitor_service, location_service


def _rows_to_csv(fieldnames: list[str], rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_locations_csv(
    db: Session,
    statuses: list[str] | None = None,
    serves_ice: bool | None = None,
    serves_water: bool | None = None,
    min_opportunity_score: float | None = None,
) -> str:
    locations = location_service.list_locations(
        db,
        statuses=statuses,
        serves_ice=serves_ice,
        serves_water=serves_water,
        min_opportunity_score=min_opportunity_score,
    )
    fieldnames = list(LocationResponse.model_fields.keys())
    rows = [location_service.assemble_response(db, loc).model_dump(mode="json") for loc in locations]
    return _rows_to_csv(fieldnames, rows)


def export_competitors_csv(
    db: Session,
    serves_ice: bool | None = None,
    serves_water: bool | None = None,
    brand: str | None = None,
) -> str:
    competitors = competitor_service.list_competitors(
        db, serves_ice=serves_ice, serves_water=serves_water, brand=brand
    )
    fieldnames = list(CompetitorResponse.model_fields.keys())
    rows = [
        competitor_service.assemble_response(db, comp).model_dump(mode="json") for comp in competitors
    ]
    return _rows_to_csv(fieldnames, rows)
