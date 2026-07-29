from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.schemas.location import LocationResponse
from app.api.schemas.validation import RejectRequest, ValidationQueueResponse
from app.core.models.user import User
from app.db.session import get_db
from app.services import location_service, validation_service

router = APIRouter(prefix="/validation-queue", tags=["validation"])


def _get_entry_or_404(db: Session, entry_id: int, organization_id: int):
    entry = validation_service.get_queue_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    submitted_by_user = db.get(User, entry.submitted_by) if entry.submitted_by is not None else None
    if submitted_by_user is None or submitted_by_user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return entry


@router.get("", response_model=list[ValidationQueueResponse])
def list_queue(
    status_filter: str | None = "pending",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[ValidationQueueResponse]:
    entries = validation_service.list_queue(db, current_user.organization_id, status=status_filter)
    return [validation_service.assemble_response(db, e) for e in entries]


@router.post("/{entry_id}/approve", response_model=LocationResponse)
def approve(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LocationResponse:
    entry = _get_entry_or_404(db, entry_id, current_user.organization_id)
    try:
        location = validation_service.approve(db, entry, reviewer_id=current_user.id)
    except validation_service.AlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except validation_service.ValidationQueueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return location_service.assemble_response(db, location)


@router.post("/{entry_id}/reject", response_model=ValidationQueueResponse)
def reject(
    entry_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ValidationQueueResponse:
    entry = _get_entry_or_404(db, entry_id, current_user.organization_id)
    try:
        entry = validation_service.reject(db, entry, reviewer_id=current_user.id, reason=body.reason)
    except validation_service.AlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return validation_service.assemble_response(db, entry)
