"""Brand (the parent franchise a location or competitor belongs to,
e.g. "Twice the Ice") create/read/update/delete.

Designed in ADR-0002 alongside the rest of the schema and referenced by
`locations.brand_id` since Phase 1, but never actually built -- no
service, no routes, no way to create one or link a location to one.
`organization_id` is nullable on the model (a private, tenant-owned
brand is a real possibility per the original design), but every brand
created through this service is shared/platform-wide (organization_id
left null) -- a franchise name isn't tenant-private data, and nothing
today needs a private-brand creation path. Revisit with a new decision
if that need appears.
"""

import uuid

from sqlalchemy.orm import Session

from app.api.schemas.brand import BrandCreateRequest, BrandResponse, BrandUpdateRequest
from app.core.models.brand import Brand
from app.core.models.location import Location

_UPDATABLE_FIELDS = ("name", "description", "logo_url")


class BrandInUseError(Exception):
    pass


def create_brand(db: Session, data: BrandCreateRequest) -> Brand:
    brand = Brand(name=data.name, description=data.description, logo_url=data.logo_url)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def get_brand(db: Session, brand_id: uuid.UUID) -> Brand | None:
    return db.get(Brand, brand_id)


def list_brands(db: Session, search: str | None = None) -> list[Brand]:
    query = db.query(Brand)
    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))
    return query.order_by(Brand.name).all()


def assemble_response(brand: Brand) -> BrandResponse:
    return BrandResponse(
        id=brand.id,
        name=brand.name,
        description=brand.description,
        logo_url=brand.logo_url,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
    )


def update_brand(db: Session, brand: Brand, data: BrandUpdateRequest) -> Brand:
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is not None:
            setattr(brand, field, new_value)
    db.commit()
    db.refresh(brand)
    return brand


def delete_brand(db: Session, brand: Brand) -> None:
    in_use = db.query(Location).filter(Location.brand_id == brand.id).first() is not None
    if in_use:
        raise BrandInUseError("This brand is still linked to at least one location")
    db.delete(brand)
    db.commit()
