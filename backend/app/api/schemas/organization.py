from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.validators import validate_email_format

RoleName = Literal["admin", "member"]


class CreateOrgUserRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: RoleName = "member"

    _validate_email = field_validator("email")(validate_email_format)


class UpdateOrgUserRequest(BaseModel):
    """Partial update -- only `is_active` and/or `role` are settable, and
    only for a *different* user than the caller (self-modification is
    rejected at the route layer to prevent an admin locking themselves
    out).
    """

    is_active: bool | None = None
    role: RoleName | None = None


class OrgUserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    role: RoleName
    created_at: datetime

    model_config = {"from_attributes": True}
