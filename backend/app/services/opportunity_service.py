"""Opportunity (pursuit-workflow) create/read/update/delete.

Designed in ADR-0003 alongside the rest of the schema and referenced by
docs/DATABASE.md since Phase 1, but never actually built until now
(ADR-0021, Phase 4) -- it fell through Phase 1/2/3 without ever being a
numbered roadmap item, unlike host_businesses/brands/photos which had
the same "designed but unbuilt" gap and got closed when a feature
actually needed them (this one is needed by Advanced Analytics's
pipeline-funnel view).

Org-scoped (unlike `locations` itself, ADR-0002): the same location can
be pursued independently by more than one organization, so listing/
updating/deleting is always filtered to the caller's own organization.
"""

import uuid

from sqlalchemy.orm import Session

from app.api.schemas.opportunity import OpportunityCreateRequest, OpportunityResponse, OpportunityUpdateRequest
from app.core.models.location import Location
from app.core.models.opportunity import Opportunity
from app.core.models.user import User

_UPDATABLE_FIELDS = ("stage", "assigned_user_id", "priority", "target_action_date", "outcome_notes")
_STAGES = ("identified", "contacted", "negotiating", "won", "lost")


class InvalidLocationError(Exception):
    pass


class InvalidStageError(Exception):
    pass


class InvalidAssigneeError(Exception):
    pass


def _validate_location(db: Session, location_id: uuid.UUID) -> None:
    if db.get(Location, location_id) is None:
        raise InvalidLocationError(f"Location {location_id} does not exist")


def _validate_stage(stage: str | None) -> None:
    if stage is not None and stage not in _STAGES:
        raise InvalidStageError(f"Stage must be one of {_STAGES}, got {stage!r}")


def _validate_assignee(db: Session, organization_id: int, assigned_user_id: int | None) -> None:
    """A raw FK IntegrityError would otherwise surface as an unhelpful 500
    for a nonexistent user id; scoping the lookup to the caller's own
    organization also rejects assigning to a user who couldn't act on it.
    """
    if assigned_user_id is None:
        return
    user = db.get(User, assigned_user_id)
    if user is None or user.organization_id != organization_id:
        raise InvalidAssigneeError(f"User {assigned_user_id} is not a member of this organization")


def create_opportunity(db: Session, organization_id: int, data: OpportunityCreateRequest) -> Opportunity:
    _validate_location(db, data.location_id)
    _validate_stage(data.stage)
    _validate_assignee(db, organization_id, data.assigned_user_id)
    opportunity = Opportunity(
        location_id=data.location_id,
        organization_id=organization_id,
        stage=data.stage,
        assigned_user_id=data.assigned_user_id,
        priority=data.priority,
        target_action_date=data.target_action_date,
        outcome_notes=data.outcome_notes,
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


def get_opportunity(db: Session, opportunity_id: uuid.UUID) -> Opportunity | None:
    return db.get(Opportunity, opportunity_id)


def list_opportunities(
    db: Session, organization_id: int, stage: str | None = None, location_id: uuid.UUID | None = None
) -> list[Opportunity]:
    query = db.query(Opportunity).filter(Opportunity.organization_id == organization_id)
    if stage is not None:
        query = query.filter(Opportunity.stage == stage)
    if location_id is not None:
        query = query.filter(Opportunity.location_id == location_id)
    return query.order_by(Opportunity.created_at.desc()).all()


def update_opportunity(db: Session, opportunity: Opportunity, data: OpportunityUpdateRequest) -> Opportunity:
    _validate_stage(data.stage)
    if data.assigned_user_id is not None:
        _validate_assignee(db, opportunity.organization_id, data.assigned_user_id)
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is not None:
            setattr(opportunity, field, new_value)
    db.commit()
    db.refresh(opportunity)
    return opportunity


def delete_opportunity(db: Session, opportunity: Opportunity) -> None:
    db.delete(opportunity)
    db.commit()


def assemble_response(db: Session, opportunity: Opportunity) -> OpportunityResponse:
    # Locations are never hard-deleted (DELETE archives, ADR-0006), so this
    # is always found for a valid opportunity row.
    location = db.get(Location, opportunity.location_id)
    assigned_user = db.get(User, opportunity.assigned_user_id) if opportunity.assigned_user_id else None
    return OpportunityResponse(
        id=opportunity.id,
        location_id=opportunity.location_id,
        location_address=location.address,
        organization_id=opportunity.organization_id,
        stage=opportunity.stage,
        assigned_user_id=opportunity.assigned_user_id,
        assigned_user_email=assigned_user.email if assigned_user else None,
        priority=opportunity.priority,
        target_action_date=opportunity.target_action_date,
        outcome_notes=opportunity.outcome_notes,
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at,
    )
