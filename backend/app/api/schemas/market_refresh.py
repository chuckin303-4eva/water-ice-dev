from datetime import datetime

from pydantic import BaseModel


class RefreshRunResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None
    status: str
    locations_reviewed: int
    changes_queued: int
    providers_used: list[str]
    error_message: str | None

    model_config = {"from_attributes": True}
