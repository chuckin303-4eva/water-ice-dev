import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.competitor import (
    CalendarLinkResponse,
    CompetitorCreateRequest,
    CompetitorResponse,
    CompetitorSummary,
    CompetitorUpdateRequest,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import calendar_link_service, competitor_service, geocoding_service

router = APIRouter(prefix="/competitors", tags=["competitors"])


def _get_competitor_or_404(db: Session, competitor_id: uuid.UUID):
    competitor = competitor_service.get_competitor(db, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return competitor


@router.post("", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
def create_competitor(
    body: CompetitorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorResponse:
    try:
        competitor = competitor_service.create_competitor(db, body)
    except geocoding_service.GeocodingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return competitor_service.assemble_response(db, competitor)


@router.get("", response_model=list[CompetitorSummary])
def list_competitors(
    serves_ice: bool | None = None,
    serves_water: bool | None = None,
    brand: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompetitorSummary]:
    competitors = competitor_service.list_competitors(
        db, serves_ice=serves_ice, serves_water=serves_water, brand=brand
    )
    return [CompetitorSummary.model_validate(c) for c in competitors]


@router.get("/{competitor_id}", response_model=CompetitorResponse)
def get_competitor(
    competitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorResponse:
    competitor = _get_competitor_or_404(db, competitor_id)
    return competitor_service.assemble_response(db, competitor)


@router.put("/{competitor_id}", response_model=CompetitorResponse)
def update_competitor(
    competitor_id: uuid.UUID,
    body: CompetitorUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorResponse:
    competitor = _get_competitor_or_404(db, competitor_id)
    competitor = competitor_service.update_competitor(db, competitor, body)
    return competitor_service.assemble_response(db, competitor)


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(
    competitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    competitor = _get_competitor_or_404(db, competitor_id)
    competitor_service.delete_competitor(db, competitor)


@router.get("/{competitor_id}/calendar-link", response_model=CalendarLinkResponse)
def get_calendar_link(
    competitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarLinkResponse:
    competitor = _get_competitor_or_404(db, competitor_id)
    if competitor.follow_up_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This competitor has no follow-up date set"
        )

    title = f"Follow up: {competitor.name}"
    details = competitor.notes or f"Follow-up with {competitor.name}"
    return CalendarLinkResponse(
        google=calendar_link_service.google_calendar_link(
            title, competitor.follow_up_at, details, competitor.address
        ),
        outlook=calendar_link_service.outlook_calendar_link(
            title, competitor.follow_up_at, details, competitor.address
        ),
    )
