import uuid
from datetime import datetime

from pydantic import BaseModel


class PhotoResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    file_url: str
    caption: str | None
    uploaded_by: int
    uploaded_at: datetime
    is_primary: bool

    model_config = {"from_attributes": True}
