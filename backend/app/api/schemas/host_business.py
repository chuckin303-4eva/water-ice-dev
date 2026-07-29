import uuid
from datetime import datetime

from pydantic import BaseModel


class HostBusinessCreateRequest(BaseModel):
    name: str
    category: str | None = None
    phone: str | None = None
    website: str | None = None


class HostBusinessUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    phone: str | None = None
    website: str | None = None


class HostBusinessResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None
    phone: str | None
    website: str | None
    created_at: datetime
    updated_at: datetime
