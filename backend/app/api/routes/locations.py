import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.location import (
    CalendarLinkResponse,
    LocationCallNoteCreateRequest,
    LocationCallNoteResponse,
    LocationCreateRequest,
    LocationImportRowError,
    LocationImportSummaryResponse,
    LocationResponse,
    LocationSummary,
    LocationUpdateRequest,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import (
    calendar_link_service,
    csv_import_service,
    geocoding_service,
    location_service,
    scoring_service,
)

router = APIRouter(prefix="/locations", tags=["locations"])


def _get_location_or_404(db: Session, location_id: uuid.UUID):
    location = location_service.get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    body: LocationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationResponse:
    try:
        location = location_service.create_location(db, body, created_by=current_user.id)
    except geocoding_service.GeocodingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return location_service.assemble_response(db, location)


@router.get("", response_model=list[LocationSummary])
def list_locations(
    statuses: list[str] | None = Query(None),
    serves_ice: bool | None = None,
    serves_water: bool | None = None,
    min_opportunity_score: float | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LocationSummary]:
    locations = location_service.list_locations(
        db,
        statuses=statuses,
        serves_ice=serves_ice,
        serves_water=serves_water,
        min_opportunity_score=min_opportunity_score,
    )
    return [LocationSummary.model_validate(loc) for loc in locations]


@router.post("/import", response_model=LocationImportSummaryResponse)
async def import_locations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationImportSummaryResponse:
    content = await file.read()
    try:
        result = csv_import_service.import_locations_from_csv(db, content, created_by=current_user.id)
    except csv_import_service.ImportTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return LocationImportSummaryResponse(
        total_rows=result.total_rows,
        created=result.created,
        errors=[LocationImportRowError(row=e.row, message=e.message) for e in result.errors],
    )


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationResponse:
    location = _get_location_or_404(db, location_id)
    return location_service.assemble_response(db, location)


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: uuid.UUID,
    body: LocationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationResponse:
    location = _get_location_or_404(db, location_id)
    location = location_service.update_location(db, location, body, updated_by=current_user.id)
    return location_service.assemble_response(db, location)


@router.post("/{location_id}/recalculate-score", response_model=LocationResponse)
def recalculate_score(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationResponse:
    """Recomputes competition_score/opportunity_score/confidence_score
    without touching any other field -- for when nearby competitor data
    changed rather than the location itself (which already triggers a
    recalculation automatically on create/update).
    """
    location = _get_location_or_404(db, location_id)
    scoring_service.recalculate_scores(db, location)
    return location_service.assemble_response(db, location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_location(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    location = _get_location_or_404(db, location_id)
    location_service.archive_location(db, location, updated_by=current_user.id)


@router.post(
    "/{location_id}/call-notes",
    response_model=LocationCallNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_call_note(
    location_id: uuid.UUID,
    body: LocationCallNoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationCallNoteResponse:
    _get_location_or_404(db, location_id)
    note = location_service.add_call_note(
        db, location_id, body.note_text, body.follow_up_at, created_by=current_user.id
    )
    return LocationCallNoteResponse.model_validate(note)


@router.get("/{location_id}/call-notes", response_model=list[LocationCallNoteResponse])
def list_call_notes(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LocationCallNoteResponse]:
    _get_location_or_404(db, location_id)
    return [
        LocationCallNoteResponse.model_validate(n)
        for n in location_service.list_call_notes(db, location_id)
    ]


@router.get(
    "/{location_id}/call-notes/{note_id}/calendar-link", response_model=CalendarLinkResponse
)
def get_calendar_link(
    location_id: uuid.UUID,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarLinkResponse:
    location = _get_location_or_404(db, location_id)
    note = location_service.get_call_note(db, location_id, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call note not found")
    if note.follow_up_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This call note has no follow-up date set"
        )

    title = f"Follow up: {location.address}"
    return CalendarLinkResponse(
        google=calendar_link_service.google_calendar_link(
            title, note.follow_up_at, note.note_text, location.address
        ),
        outlook=calendar_link_service.outlook_calendar_link(
            title, note.follow_up_at, note.note_text, location.address
        ),
    )
