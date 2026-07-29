"""Host business (the business hosting a vending machine at a location --
gas station, laundromat, ...) create/read/update/delete.

Designed in ADR-0003 alongside the rest of the schema and referenced by
`locations.host_business_id` since Phase 1, but never actually built --
there was no way to create one or see its name/category anywhere. Same
shared, platform-wide reference-data pattern as `competitors`/`brands`
(ADR-0002): no organization scoping, any authenticated user can manage it.
"""

import uuid

from sqlalchemy.orm import Session

from app.api.schemas.host_business import (
    HostBusinessCreateRequest,
    HostBusinessResponse,
    HostBusinessUpdateRequest,
)
from app.core.models.host_business import HostBusiness
from app.core.models.location import Location

_UPDATABLE_FIELDS = ("name", "category", "phone", "website")


class HostBusinessInUseError(Exception):
    pass


def create_host_business(db: Session, data: HostBusinessCreateRequest) -> HostBusiness:
    host_business = HostBusiness(
        name=data.name,
        category=data.category,
        phone=data.phone,
        website=data.website,
    )
    db.add(host_business)
    db.commit()
    db.refresh(host_business)
    return host_business


def get_host_business(db: Session, host_business_id: uuid.UUID) -> HostBusiness | None:
    return db.get(HostBusiness, host_business_id)


def list_host_businesses(db: Session, search: str | None = None) -> list[HostBusiness]:
    """`search` matches name or category (case-insensitive, partial) --
    powers the location detail panel's "find or add a host business"
    picker, same role `brand` plays for competitors.
    """
    query = db.query(HostBusiness)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (HostBusiness.name.ilike(pattern)) | (HostBusiness.category.ilike(pattern))
        )
    return query.order_by(HostBusiness.name).all()


def assemble_response(host_business: HostBusiness) -> HostBusinessResponse:
    return HostBusinessResponse(
        id=host_business.id,
        name=host_business.name,
        category=host_business.category,
        phone=host_business.phone,
        website=host_business.website,
        created_at=host_business.created_at,
        updated_at=host_business.updated_at,
    )


def update_host_business(
    db: Session, host_business: HostBusiness, data: HostBusinessUpdateRequest
) -> HostBusiness:
    for field in _UPDATABLE_FIELDS:
        new_value = getattr(data, field)
        if new_value is not None:
            setattr(host_business, field, new_value)
    db.commit()
    db.refresh(host_business)
    return host_business


def delete_host_business(db: Session, host_business: HostBusiness) -> None:
    """Refuses to delete a host business still referenced by a location --
    `locations.host_business_id` has no ON DELETE behavior configured
    (a raw FK IntegrityError would otherwise surface as an unhelpful
    500), and silently nulling out every referencing location's field
    would be a silent data change nobody asked for.
    """
    in_use = db.query(Location).filter(Location.host_business_id == host_business.id).first() is not None
    if in_use:
        raise HostBusinessInUseError(
            "This host business is still linked to at least one location"
        )
    db.delete(host_business)
    db.commit()
