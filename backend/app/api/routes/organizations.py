from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.schemas.organization import CreateOrgUserRequest, OrgUserResponse, UpdateOrgUserRequest
from app.core.models.user import User
from app.db.session import get_db
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _to_response(db: Session, user: User) -> OrgUserResponse:
    return OrgUserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=organization_service.get_user_role_name(db, user),
        created_at=user.created_at,
    )


@router.get("/users", response_model=list[OrgUserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrgUserResponse]:
    """Any authenticated org member can see their own teammate roster --
    only creating/modifying users is admin-gated.
    """
    users = organization_service.list_organization_users(db, current_user.organization_id)
    return [_to_response(db, u) for u in users]


@router.post("/users", response_model=OrgUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateOrgUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> OrgUserResponse:
    """No email is sent -- there's no email service to send one (see
    ADR-0012). The admin sets and shares this password with the new
    teammate directly.
    """
    try:
        user = organization_service.create_organization_user(
            db, current_user.organization_id, body.email, body.password, body.role
        )
    except organization_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(db, user)


@router.put("/users/{user_id}", response_model=OrgUserResponse)
def update_user(
    user_id: int,
    body: UpdateOrgUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> OrgUserResponse:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot modify your own account here"
        )
    user = db.get(User, user_id)
    if user is None or user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.is_active is not None:
        user = organization_service.set_user_active(db, user, body.is_active)
    if body.role is not None:
        user = organization_service.set_user_role(db, user, body.role)

    return _to_response(db, user)
