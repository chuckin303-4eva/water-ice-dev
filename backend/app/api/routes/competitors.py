import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.competitor import (
    CompetitorCreateRequest,
    CompetitorResponse,
    CompetitorSummary,
    CompetitorUpdateRequest,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import competitor_service, geocoding_service

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompetitorSummary]:
    return [CompetitorSummary.model_validate(c) for c in competitor_service.list_competitors(db)]


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
