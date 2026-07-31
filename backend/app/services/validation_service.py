"""Validation workflow (Phase 2; ADR-0014): queue a non-admin's proposed
location create/update for admin review instead of writing it directly.

Opt-in per organization (`Organization.require_review_for_submissions`,
default False) -- see the route layer for where that check happens.
This module only knows how to propose/list/approve/reject; it doesn't
decide *whether* a given write should be queued at all.

Approving a queue entry dispatches to the exact same
`location_service.create_location`/`update_location` functions any
direct write already goes through, using the *original submitter* as
`created_by`/`updated_by` -- so `update_log` correctly attributes the
change to whoever proposed it, not whoever clicked approve.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.schemas.location import LocationCreateRequest, LocationUpdateRequest
from app.api.schemas.validation import ValidationQueueResponse
from app.core.models.location import Location
from app.core.models.user import User
from app.core.models.validation_queue import ValidationQueue
from app.services import location_service

_ENTITY_TYPE = "location"


class ValidationQueueNotFoundError(Exception):
    pass


class AlreadyReviewedError(Exception):
    pass


def propose_create_location(
    db: Session, data: LocationCreateRequest, submitted_by: int
) -> ValidationQueue:
    entry = ValidationQueue(
        entity_type=_ENTITY_TYPE,
        entity_id=None,
        proposed_changes=data.model_dump(mode="json"),
        submitted_by=submitted_by,
        status="pending",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def propose_update_location(
    db: Session,
    location_id: uuid.UUID,
    data: LocationUpdateRequest,
    submitted_by: int | None,
    reason: str | None = None,
) -> ValidationQueue:
    """`submitted_by=None` means a system-sourced proposal (the Market
    Refresh Engine, ADR-0020) rather than a specific user's edit --
    `reason` carries the provider's own explanation (e.g. "OpenStreetMap:
    address may have changed") for a reviewer, distinct from the
    rejection-reason use of this same column.
    """
    # Only the fields actually being changed, not every unset field --
    # keeps the diff shown to a reviewer meaningful.
    changes = data.model_dump(mode="json", exclude_none=True)
    entry = ValidationQueue(
        entity_type=_ENTITY_TYPE,
        entity_id=str(location_id),
        proposed_changes=changes,
        reason=reason,
        submitted_by=submitted_by,
        status="pending",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_queue_entry(db: Session, entry_id: int) -> ValidationQueue | None:
    return db.get(ValidationQueue, entry_id)


def assemble_response(db: Session, entry: ValidationQueue) -> ValidationQueueResponse:
    submitter_email = None
    if entry.submitted_by is not None:
        submitter = db.get(User, entry.submitted_by)
        submitter_email = submitter.email if submitter else None
    return ValidationQueueResponse(
        id=entry.id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        proposed_changes=entry.proposed_changes,
        reason=entry.reason,
        submitted_by=entry.submitted_by,
        submitted_by_email=submitter_email,
        status=entry.status,
        reviewed_by=entry.reviewed_by,
        reviewed_at=entry.reviewed_at,
        created_at=entry.created_at,
    )


def list_queue(db: Session, organization_id: int, status: str | None = "pending") -> list[ValidationQueue]:
    """A system-sourced entry (`submitted_by IS NULL`, e.g. from the
    Market Refresh Engine, ADR-0020) has no submitting user to scope by
    organization -- and unlike a member's own submission, it's about
    shared, platform-wide location data (ADR-0002), not one tenant's
    private write. So it's surfaced to every organization's admins,
    alongside that org's own member-submitted entries. Uses an outer
    join (not the inner join this originally had) specifically so those
    NULL-submitter rows survive the join instead of being silently
    dropped.
    """
    query = (
        db.query(ValidationQueue)
        .outerjoin(User, User.id == ValidationQueue.submitted_by)
        .filter(or_(ValidationQueue.submitted_by.is_(None), User.organization_id == organization_id))
    )
    if status is not None:
        query = query.filter(ValidationQueue.status == status)
    return query.order_by(ValidationQueue.created_at).all()


def approve(
    db: Session, entry: ValidationQueue, reviewer_id: int, change_source: str = "manual"
) -> Location:
    """`change_source` lets the Market Refresh Engine (ADR-0020) approve
    its own proposals with `change_source="verification"` so `update_log`
    reflects how the change was actually discovered, rather than every
    validation-queue approval reading as a plain "manual" edit.
    """
    if entry.status != "pending":
        raise AlreadyReviewedError(f"This submission was already {entry.status}")

    submitted_by = entry.submitted_by
    if entry.entity_id is None:
        data = LocationCreateRequest(**entry.proposed_changes)
        location = location_service.create_location(db, data, created_by=submitted_by)
    else:
        data = LocationUpdateRequest(**entry.proposed_changes)
        location = location_service.get_location(db, uuid.UUID(entry.entity_id))
        if location is None:
            raise ValidationQueueNotFoundError(
                f"Location {entry.entity_id} no longer exists"
            )
        location = location_service.update_location(
            db, location, data, updated_by=submitted_by, change_source=change_source
        )

    entry.status = "approved"
    entry.reviewed_by = reviewer_id
    entry.reviewed_at = datetime.now(UTC)
    db.commit()
    return location


def reject(db: Session, entry: ValidationQueue, reviewer_id: int, reason: str | None = None) -> ValidationQueue:
    if entry.status != "pending":
        raise AlreadyReviewedError(f"This submission was already {entry.status}")

    entry.status = "rejected"
    entry.reviewed_by = reviewer_id
    entry.reviewed_at = datetime.now(UTC)
    if reason:
        entry.reason = reason
    db.commit()
    db.refresh(entry)
    return entry
