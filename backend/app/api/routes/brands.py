import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.brand import BrandCreateRequest, BrandResponse, BrandUpdateRequest
from app.core.models.user import User
from app.db.session import get_db
from app.services import brand_service

router = APIRouter(prefix="/brands", tags=["brands"])


def _get_brand_or_404(db: Session, brand_id: uuid.UUID):
    brand = brand_service.get_brand(db, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    body: BrandCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandResponse:
    brand = brand_service.create_brand(db, body)
    return brand_service.assemble_response(brand)


@router.get("", response_model=list[BrandResponse])
def list_brands(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrandResponse]:
    brands = brand_service.list_brands(db, search=search)
    return [brand_service.assemble_response(b) for b in brands]


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandResponse:
    brand = _get_brand_or_404(db, brand_id)
    return brand_service.assemble_response(brand)


@router.put("/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandResponse:
    brand = _get_brand_or_404(db, brand_id)
    brand = brand_service.update_brand(db, brand, body)
    return brand_service.assemble_response(brand)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    brand = _get_brand_or_404(db, brand_id)
    try:
        brand_service.delete_brand(db, brand)
    except brand_service.BrandInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
