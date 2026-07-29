import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.host_business import (
    HostBusinessCreateRequest,
    HostBusinessResponse,
    HostBusinessUpdateRequest,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import host_business_service

router = APIRouter(prefix="/host-businesses", tags=["host-businesses"])


def _get_host_business_or_404(db: Session, host_business_id: uuid.UUID):
    host_business = host_business_service.get_host_business(db, host_business_id)
    if host_business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host business not found")
    return host_business


@router.post("", response_model=HostBusinessResponse, status_code=status.HTTP_201_CREATED)
def create_host_business(
    body: HostBusinessCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostBusinessResponse:
    host_business = host_business_service.create_host_business(db, body)
    return host_business_service.assemble_response(host_business)


@router.get("", response_model=list[HostBusinessResponse])
def list_host_businesses(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HostBusinessResponse]:
    host_businesses = host_business_service.list_host_businesses(db, search=search)
    return [host_business_service.assemble_response(h) for h in host_businesses]


@router.get("/{host_business_id}", response_model=HostBusinessResponse)
def get_host_business(
    host_business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostBusinessResponse:
    host_business = _get_host_business_or_404(db, host_business_id)
    return host_business_service.assemble_response(host_business)


@router.put("/{host_business_id}", response_model=HostBusinessResponse)
def update_host_business(
    host_business_id: uuid.UUID,
    body: HostBusinessUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostBusinessResponse:
    host_business = _get_host_business_or_404(db, host_business_id)
    host_business = host_business_service.update_host_business(db, host_business, body)
    return host_business_service.assemble_response(host_business)


@router.delete("/{host_business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_host_business(
    host_business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    host_business = _get_host_business_or_404(db, host_business_id)
    try:
        host_business_service.delete_host_business(db, host_business)
    except host_business_service.HostBusinessInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
