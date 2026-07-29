from datetime import datetime

from pydantic import BaseModel


class ValidationQueueResponse(BaseModel):
    """Returned both from GET /validation-queue and, in place of the
    usual LocationResponse, from POST/PUT /locations when the caller's
    write was queued instead of applied directly (ADR-0014).
    """

    id: int
    entity_type: str
    entity_id: str | None
    proposed_changes: dict
    reason: str | None
    submitted_by: int | None
    submitted_by_email: str | None
    status: str
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime


class RejectRequest(BaseModel):
    reason: str | None = None
