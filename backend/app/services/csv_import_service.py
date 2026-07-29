"""CSV import for locations (Phase 1, item 8; ADR-0011).

Minimal v1 column set -- `address` (or `latitude`+`longitude`),
`serves_ice`, `serves_water`, `notes` -- everything else is filled in
later via the detail panel, the same "minimal add, fill in the rest"
split used everywhere else a prospect gets created (ADR-0007).

Rows are geocoded one at a time with a fixed delay between them to
respect Nominatim's documented ~1 request/second usage policy
(geocoding_service.py) -- normal single-prospect creation never needed
this, but a bulk import is exactly the "more than occasional" traffic
pattern that policy exists for. A row cap keeps a single import request
bounded in duration rather than open-ended.

Validation workflow (ADR-0014): when the caller's organization requires
review and they're not an admin, rows are queued via
`validation_service.propose_create_location` instead of created
directly. Queueing doesn't geocode at all (that happens once, at
approval time) so queued rows skip the rate-limit delay entirely --
there's no external request to rate-limit yet.
"""

import csv
import io
import time
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.schemas.location import LocationCreateRequest
from app.services import geocoding_service, location_service, validation_service

MAX_IMPORT_ROWS = 100
ROW_DELAY_SECONDS = 1.1

_TRUTHY = {"true", "1", "yes", "y"}


@dataclass
class RowError:
    row: int
    message: str


@dataclass
class ImportResult:
    total_rows: int
    created: int
    queued: int = 0
    errors: list[RowError] = field(default_factory=list)


class ImportTooLargeError(Exception):
    pass


def _parse_bool(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


def _row_to_request(row: dict) -> LocationCreateRequest:
    address = (row.get("address") or "").strip() or None
    lat_raw = (row.get("latitude") or "").strip()
    lon_raw = (row.get("longitude") or "").strip()
    latitude = float(lat_raw) if lat_raw else None
    longitude = float(lon_raw) if lon_raw else None
    return LocationCreateRequest(
        address=address,
        latitude=latitude,
        longitude=longitude,
        serves_ice=_parse_bool(row.get("serves_ice")),
        serves_water=_parse_bool(row.get("serves_water")),
        notes=(row.get("notes") or "").strip() or None,
    )


def import_locations_from_csv(
    db: Session, file_content: bytes, created_by: int, require_review: bool = False
) -> ImportResult:
    text = file_content.decode("utf-8-sig")  # -sig strips the BOM Excel likes to add
    rows = list(csv.DictReader(io.StringIO(text)))

    if len(rows) > MAX_IMPORT_ROWS:
        raise ImportTooLargeError(
            f"CSV has {len(rows)} rows; the limit per import is {MAX_IMPORT_ROWS}"
        )

    result = ImportResult(total_rows=len(rows), created=0)
    for index, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            request = _row_to_request(row)
        except (ValidationError, ValueError) as exc:
            result.errors.append(RowError(row=index, message=str(exc)))
            continue  # no geocode attempted -- no rate-limit delay needed

        if require_review:
            validation_service.propose_create_location(db, request, submitted_by=created_by)
            result.queued += 1
            continue  # no geocode happens until approval -- nothing to rate-limit yet

        try:
            location_service.create_location(db, request, created_by=created_by)
            result.created += 1
        except geocoding_service.GeocodingError as exc:
            result.errors.append(RowError(row=index, message=f"Could not geocode: {exc}"))
        time.sleep(ROW_DELAY_SECONDS)

    return result
