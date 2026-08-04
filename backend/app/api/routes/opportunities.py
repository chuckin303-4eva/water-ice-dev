import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.opportunity import (
    OpportunityCreateRequest,
    OpportunityResponse,
    OpportunityUpdateRequest,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import opportunity_service

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _get_opportunity_or_404(db: Session, opportunity_id: uuid.UUID, organization_id: int):
    opportunity = opportunity_service.get_opportunity(db, opportunity_id)
    if opportunity is None or opportunity.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opportunity


def _handle_validation_errors(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    body: OpportunityCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityResponse:
    try:
        opportunity = opportunity_service.create_opportunity(db, current_user.organization_id, body)
    except (
        opportunity_service.InvalidLocationError,
        opportunity_service.InvalidStageError,
        opportunity_service.InvalidAssigneeError,
    ) as exc:
        raise _handle_validation_errors(exc) from exc
    return opportunity_service.assemble_response(db, opportunity)


@router.get("", response_model=list[OpportunityResponse])
def list_opportunities(
    stage: str | None = None,
    location_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OpportunityResponse]:
    opportunities = opportunity_service.list_opportunities(
        db, current_user.organization_id, stage=stage, location_id=location_id
    )
    return [opportunity_service.assemble_response(db, o) for o in opportunities]


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityResponse:
    opportunity = _get_opportunity_or_404(db, opportunity_id, current_user.organization_id)
    return opportunity_service.assemble_response(db, opportunity)


@router.put("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(
    opportunity_id: uuid.UUID,
    body: OpportunityUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityResponse:
    opportunity = _get_opportunity_or_404(db, opportunity_id, current_user.organization_id)
    try:
        opportunity = opportunity_service.update_opportunity(db, opportunity, body)
    except (opportunity_service.InvalidStageError, opportunity_service.InvalidAssigneeError) as exc:
        raise _handle_validation_errors(exc) from exc
    return opportunity_service.assemble_response(db, opportunity)


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    opportunity = _get_opportunity_or_404(db, opportunity_id, current_user.organization_id)
    opportunity_service.delete_opportunity(db, opportunity)
