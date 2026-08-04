import uuid
from datetime import date, datetime

from pydantic import BaseModel

_STAGES = ("identified", "contacted", "negotiating", "won", "lost")


class OpportunityCreateRequest(BaseModel):
    location_id: uuid.UUID
    stage: str = "identified"
    assigned_user_id: int | None = None
    priority: str | None = None
    target_action_date: date | None = None
    outcome_notes: str | None = None


class OpportunityUpdateRequest(BaseModel):
    stage: str | None = None
    assigned_user_id: int | None = None
    priority: str | None = None
    target_action_date: date | None = None
    outcome_notes: str | None = None


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    location_address: str
    organization_id: int
    stage: str
    assigned_user_id: int | None
    assigned_user_email: str | None
    priority: str | None
    target_action_date: date | None
    outcome_notes: str | None
    created_at: datetime
    updated_at: datetime
