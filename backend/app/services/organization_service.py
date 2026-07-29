"""Organization/user management for the Admin dashboard (Phase 1, item 9;
ADR-0012): self-serve registration (new org + first admin user) and
letting an org's admin manage their own teammates.

Two system-wide roles ("admin", "member") are get-or-created lazily,
the same pattern geography rows already use (geography_service.py),
rather than seeded via a one-time data migration -- avoids
migration/dev-db seed drift. `role_id`/`organization_id` on `Role` stay
`NULL` for both, per that model's own "nullable for system-wide roles"
design intent -- these apply platform-wide, not per-tenant.

`permissions`/`role_permissions` stay schema-only and unused: no
endpoint anywhere checks a fine-grained permission slug today, so
building a permission-management UI would be pure unused scaffolding.
Role-based admin/member is what's actually needed to gate the
org/user-management endpoints this feature adds -- nothing else in the
app (locations, competitors) is role-gated, since those are shared
platform-wide data per ADR-0002, not tenant-private.

No "can't deactivate/demote the last admin" guard, deliberately: the
route layer already rejects any attempt to modify your own account
(`organizations.py`), and every organization starts with exactly one
admin at registration. Combined, those two facts make 0 active admins
structurally unreachable through this API regardless of an extra
counting check -- whoever calls this endpoint on someone else is
necessarily a *different*, currently-active admin, so at least one
admin always survives. An earlier version of this file had such a
guard; it was provably dead for its stated purpose and produced a
false-positive (blocking a harmless demotion of an already-inactive
admin) instead, so it was removed rather than patched.

`require_review_for_submissions` (ADR-0014, Phase 2) toggles the
validation workflow for this org -- see `validation_service.py` for
what actually happens when it's on. Defaults `False` so no existing
organization's behavior changes unless an admin opts in.
"""

from sqlalchemy.orm import Session

from app.core.models.associations import user_roles
from app.core.models.organization import Organization
from app.core.models.role import Role
from app.core.models.user import User
from app.core.security import hash_password

ADMIN_ROLE = "admin"
MEMBER_ROLE = "member"


class EmailAlreadyRegisteredError(Exception):
    pass


def get_or_create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.organization_id.is_(None), Role.name == name).first()
    if role is None:
        role = Role(organization_id=None, name=name)
        db.add(role)
        db.flush()
    return role


def _assign_role(db: Session, user: User, role: Role) -> None:
    db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))


def _remove_role(db: Session, user: User, role: Role) -> None:
    db.execute(
        user_roles.delete().where(user_roles.c.user_id == user.id, user_roles.c.role_id == role.id)
    )


def get_user_role_name(db: Session, user: User) -> str:
    row = (
        db.query(Role.name)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .filter(user_roles.c.user_id == user.id)
        .first()
    )
    # Defensive default -- every user created through this service gets
    # a role, but this keeps a pre-existing seed-script user (which has
    # none) from 403ing/erroring instead of just being treated as a
    # regular member.
    return row[0] if row else MEMBER_ROLE


def user_is_admin(db: Session, user: User) -> bool:
    return get_user_role_name(db, user) == ADMIN_ROLE


def register_organization(db: Session, organization_name: str, email: str, password: str) -> User:
    if db.query(User).filter(User.email == email).first() is not None:
        raise EmailAlreadyRegisteredError(f"{email} is already registered")

    organization = Organization(name=organization_name)
    db.add(organization)
    db.flush()

    user = User(organization_id=organization.id, email=email, hashed_password=hash_password(password))
    db.add(user)
    db.flush()

    _assign_role(db, user, get_or_create_role(db, ADMIN_ROLE))

    db.commit()
    db.refresh(user)
    return user


def list_organization_users(db: Session, organization_id: int) -> list[User]:
    return (
        db.query(User)
        .filter(User.organization_id == organization_id)
        .order_by(User.created_at)
        .all()
    )


def create_organization_user(
    db: Session, organization_id: int, email: str, password: str, role_name: str
) -> User:
    if db.query(User).filter(User.email == email).first() is not None:
        raise EmailAlreadyRegisteredError(f"{email} is already registered")

    user = User(organization_id=organization_id, email=email, hashed_password=hash_password(password))
    db.add(user)
    db.flush()

    _assign_role(db, user, get_or_create_role(db, role_name))

    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def set_user_role(db: Session, user: User, role_name: str) -> User:
    current_role_name = get_user_role_name(db, user)
    if current_role_name == role_name:
        return user

    _remove_role(db, user, get_or_create_role(db, current_role_name))
    _assign_role(db, user, get_or_create_role(db, role_name))
    db.commit()
    db.refresh(user)
    return user


def get_organization(db: Session, organization_id: int) -> Organization | None:
    return db.get(Organization, organization_id)


def set_require_review(db: Session, organization: Organization, value: bool) -> Organization:
    organization.require_review_for_submissions = value
    db.commit()
    db.refresh(organization)
    return organization
