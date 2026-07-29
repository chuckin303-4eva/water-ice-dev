import uuid
from datetime import datetime

from pydantic import BaseModel


class BrandCreateRequest(BaseModel):
    name: str
    description: str | None = None
    logo_url: str | None = None


class BrandUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None


class BrandResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    logo_url: str | None
    created_at: datetime
    updated_at: datetime
