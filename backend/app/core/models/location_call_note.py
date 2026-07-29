import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class LocationCallNote(Base):
    """A log of prospecting calls/interactions for a location. follow_up_at
    is set when the call ends with a scheduled next step -- that's what
    the "add to calendar" button (see app/services/calendar_link_service.py)
    turns into a Google/Outlook event. Append-only: notes are never
    edited or deleted, matching the history-preservation approach used
    for every other change record in this schema.
    """

    __tablename__ = "location_call_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id"), index=True, nullable=False
    )
    note_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    call_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
